import pytest
from app.extractor import extract


def test_extract_with_html():
    html = "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
    res = extract(html, "https://example.com")
    assert isinstance(res, dict)
    assert "clean_text" in res


def test_extract_empty():
    res = extract("", "https://example.com")
    assert res["clean_text"] == ""


def test_extract_fallback():
    html = "<html><body><h1>Hi</h1></body></html>"
    res = extract(html, "https://example.com")
    assert res["title"] is None or isinstance(res["title"], str)
