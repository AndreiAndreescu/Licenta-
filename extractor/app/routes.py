from fastapi import APIRouter
from .extractor import extract

router = APIRouter()


@router.post("/extract")
async def extract_route(payload: dict):
    html = payload.get("html", "")
    url = payload.get("url", "")
    return extract(html, url)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "extractor"}
