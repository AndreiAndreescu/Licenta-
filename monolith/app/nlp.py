import re
from collections import defaultdict

import spacy
import nltk
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yake


try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


try:
    nlp_model = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download

    download("en_core_web_sm")
    nlp_model = spacy.load("en_core_web_sm")

sentiment_analyzer = SentimentIntensityAnalyzer()


def summarize(text: str, sentence_count: int) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        sentences = summarizer(parser.document, sentence_count)
        summary = " ".join(str(sentence) for sentence in sentences).strip()
        if summary:
            return summary
    except Exception:
        pass

    sentences = [sentence.strip() for sentence in text.split('.') if sentence.strip()]
    return ' '.join(sentences[:sentence_count])


def extract_keywords(text: str, max_kw: int) -> list[str]:
    extractor = yake.KeywordExtractor(top=max_kw, features=None)
    keywords = extractor.extract_keywords(text)
    return [keyword for keyword, _ in keywords][:max_kw]


def analyze_sentiment(text: str) -> dict:
    scores = sentiment_analyzer.polarity_scores(text)
    compound = float(scores.get("compound", 0.0))
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return {"sentiment_label": label, "sentiment_score": compound}


def extract_entities(text: str) -> dict:
    document = nlp_model(text)
    entities: dict[str, set[str]] = defaultdict(set)
    for ent in document.ents:
        entities[ent.label_].add(ent.text)
    return {label: sorted(values) for label, values in entities.items()}


def run_pipeline(text: str, sentence_count: int = 3, max_keywords: int = 10) -> dict:
    if not text or not text.strip():
        return {
            "summary": "",
            "keywords": [],
            "sentiment_label": "neutral",
            "sentiment_score": 0.0,
            "entities": {},
        }

    return {
        "summary": summarize(text, sentence_count),
        "keywords": extract_keywords(text, max_keywords),
        **analyze_sentiment(text),
        "entities": extract_entities(text),
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
