import pytest

from app import nlp


def test_summarize_returns_text():
    text = "This is a short article about testing. The system should summarize the main points." * 3
    summary = nlp.summarize(text, sentence_count=2)
    assert isinstance(summary, str)
    assert summary


def test_extract_keywords_returns_list():
    text = "Python testing is useful for writing reliable software and verifying behavior."
    keywords = nlp.extract_keywords(text, max_kw=5)
    assert isinstance(keywords, list)
    assert all(isinstance(item, str) for item in keywords)


def test_analyze_sentiment_returns_correct_label():
    positive_text = "I love this product and it works perfectly."
    negative_text = "This experience was terrible and frustrating."
    result_positive = nlp.analyze_sentiment(positive_text)
    result_negative = nlp.analyze_sentiment(negative_text)
    assert result_positive["sentiment_label"] == "positive"
    assert result_negative["sentiment_label"] == "negative"


def test_extract_entities_returns_dict():
    text = "Barack Obama visited Paris and met with officials from Microsoft."
    entities = nlp.extract_entities(text)
    assert isinstance(entities, dict)
    assert any(key in entities for key in ["PERSON", "GPE", "ORG"])


def test_run_pipeline_returns_all_keys():
    text = "FastAPI is a modern framework for building APIs."
    result = nlp.run_pipeline(text, sentence_count=2, max_keywords=3)
    assert set(result.keys()) == {"summary", "keywords", "sentiment_label", "sentiment_score", "entities"}
    assert isinstance(result["summary"], str)
    assert isinstance(result["keywords"], list)
    assert isinstance(result["entities"], dict)
