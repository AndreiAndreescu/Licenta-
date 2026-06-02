import logging
import re as _re
from typing import List

logger = logging.getLogger(__name__)

try:
    import spacy
    import nltk
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    import yake
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    # download nltk packages silently
    for pkg in ["punkt", "stopwords"]:
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass
    try:
        nlp_model = spacy.load("en_core_web_sm")
    except Exception:
        nlp_model = None
    vader = SentimentIntensityAnalyzer()
except Exception:
    spacy = None
    nlp_model = None
    vader = None


def summarize(text: str, sentence_count: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentence_count)
        return " ".join(str(s) for s in summary)
    except Exception:
        try:
            parts = text.split(". ")
            return ". ".join(parts[:sentence_count])
        except Exception:
            return ""


def extract_keywords(text: str, max_kw: int = 10) -> List[str]:
    try:
        kw_extractor = yake.KeywordExtractor(top=max_kw)
        keywords = kw_extractor.extract_keywords(text)
        return [k for k, _ in keywords]
    except Exception:
        return []


def analyze_sentiment(text: str) -> dict:
    try:
        if vader is None:
            return {"score": 0.0, "label": "neutral"}
        s = vader.polarity_scores(text)
        score = s.get("compound", 0.0)
        label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
        return {"score": score, "label": label}
    except Exception:
        return {"score": 0.0, "label": "neutral"}


def extract_entities(text: str) -> dict:
    try:
        if nlp_model is None:
            return {}
        doc = nlp_model(text)
        entities = {}
        for ent in doc.ents:
            entities.setdefault(ent.label_, []).append(ent.text)
        # deduplicate
        return {k: list(dict.fromkeys(v)) for k, v in entities.items()}
    except Exception:
        return {}


def run_pipeline(text: str, summary_sentences: int = 3, max_keywords: int = 10) -> dict:
    try:
        summary = summarize(text, summary_sentences)
    except Exception:
        summary = ""
    try:
        keywords = extract_keywords(text, max_keywords)
    except Exception:
        keywords = []
    try:
        sentiment = analyze_sentiment(text)
    except Exception:
        sentiment = {"score": 0.0, "label": "neutral"}
    try:
        entities = extract_entities(text)
    except Exception:
        entities = {}
    return {
        "summary": summary,
        "keywords": keywords,
        "sentiment_label": sentiment.get("label"),
        "sentiment_score": sentiment.get("score"),
        "entities": entities,
    }


def compute_verdict(claim: str, pages_data: list[dict]) -> dict:
    import re

    claim_lower = claim.lower()
    claim_words_list = re.findall(r"\b\w+\b", claim_lower)

    stop_words = {
        "is", "are", "was", "were", "be", "been", "being",
        "the", "a", "an", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "with", "your", "our", "their",
        "it", "this", "that", "very", "so", "do", "does", "did",
        "has", "have", "had", "will", "would", "can", "could",
        "should", "may", "might", "shall", "also", "its", "by"
    }

    match_words = set(w for w in claim_words_list if len(w) >= 3 and w not in stop_words)

    debunk_signals = [
        "false", "myth", "debunked", "incorrect", "disproven", "misleading",
        "conspiracy", "hoax", "pseudoscience", "misinformation", "wrong",
        "actually", "contrary", "however", "but the truth", "in fact",
        "scientifically disproven", "archaic", "not true", "no evidence"
    ]
    support_signals = [
        "confirmed", "proven", "evidence shows", "research shows", "studies show",
        "scientists confirm", "officially", "verified", "fact", "indeed",
        "true that", "correct", "accurate"
    ]

    support_w = 0.0
    contradict_w = 0.0
    total_rel = 0.0
    good_snippets: list[str] = []
    valid_pages = 0

    for page in pages_data:
        summary = page.get("summary") or ""
        keywords = page.get("keywords") or []
        sentiment = page.get("sentiment_label") or "neutral"
        score = float(page.get("sentiment_score") or 0.0)

        if len(summary.strip()) < 50:
            continue

        junk_signals = ["captcha", "enable javascript", "ray id", "cloudflare",
                        "please verify", "cookie", "subscribe to continue",
                        "access denied", "403 forbidden", "404 not found",
                        "aw snap", "this page", "your browser"]
        if any(s in summary.lower() for s in junk_signals):
            continue

        blob = (summary + " " + " ".join(keywords)).lower()
        blob_words = set(re.findall(r"\b\w+\b", blob))

        if not match_words:
            rel = 0.0
        else:
            matched = match_words & blob_words
            rel = len(matched) / len(match_words)

        if rel < 0.05:
            continue

        valid_pages += 1
        total_rel += rel

        debunk_count = sum(1 for s in debunk_signals if s in blob)
        support_count = sum(1 for s in support_signals if s in blob)

        if debunk_count > support_count:
            adjusted_score = -(abs(score) + 0.3 + debunk_count * 0.1)
        elif support_count > debunk_count:
            adjusted_score = abs(score) + 0.3 + support_count * 0.1
        else:
            if sentiment == "positive":
                adjusted_score = abs(score) + 0.3
            elif sentiment == "negative":
                adjusted_score = -(abs(score) + 0.3)
            else:
                adjusted_score = 0.0

        weight = rel * abs(adjusted_score)
        if weight > 0:
            if adjusted_score > 0:
                support_w += weight
            else:
                contradict_w += weight

        if len(summary.strip()) > 50:
            good_snippets.append(summary.strip()[:200])

    total = support_w + contradict_w

    if total < 0.01 or valid_pages == 0:
        return {
            "verdict": "UNCERTAIN",
            "confidence": 0,
            "evidence": "Not enough relevant web content found to verify this claim.",
        }

    support_ratio = support_w / total
    rel_factor = min(1.0, total_rel / max(valid_pages, 1))
    raw_conf = max(support_ratio, 1 - support_ratio) * 100 * (0.4 + rel_factor * 0.6)
    confidence = int(min(90, max(35, raw_conf)))

    if support_ratio >= 0.62:
        verdict = "TRUE"
    elif support_ratio <= 0.38:
        verdict = "FALSE"
    else:
        verdict = "UNCERTAIN"

    evidence = " ".join(good_snippets[:2]) or "Analysis derived from crawled web content."
    return {"verdict": verdict, "confidence": confidence, "evidence": evidence}
