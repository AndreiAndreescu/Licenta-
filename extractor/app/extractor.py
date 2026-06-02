import json
import logging
from bs4 import BeautifulSoup

import trafilatura

logger = logging.getLogger(__name__)


def extract(html: str, url: str) -> dict:
    try:
        result = trafilatura.extract(html, include_metadata=True, output_format="json")
        if result:
            data = json.loads(result)
            return {
                "clean_text": data.get("text", "") or "",
                "title": data.get("title"),
                "author": data.get("author"),
                "publish_date": data.get("date"),
                "language": data.get("language"),
            }
    except Exception:
        logger.exception("trafilatura failed")

    try:
        soup = BeautifulSoup(html or "", "lxml")
        texts = soup.stripped_strings
        clean = " ".join(texts)
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None
        return {"clean_text": clean, "title": title, "author": None, "publish_date": None, "language": None}
    except Exception:
        logger.exception("fallback extract failed")
        return {"clean_text": "", "title": None, "author": None, "publish_date": None, "language": None}
