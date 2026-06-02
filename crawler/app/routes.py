from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import httpx

from .crawler import crawl
from .config import settings

router = APIRouter()


@router.post("/crawl")
async def crawl_single(payload: dict):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10.0)
            html = r.text
            title = None
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "lxml")
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)
            except Exception:
                title = None
            return {"url": url, "http_status": r.status_code, "title": title, "html_length": len(html)}
        except Exception:
            return {"url": url, "http_status": -1, "title": None, "html_length": 0}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "crawler"}
