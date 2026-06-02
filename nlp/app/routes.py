from fastapi import APIRouter
from .pipeline import run_pipeline
from .config import settings

router = APIRouter()


@router.post("/analyze")
async def analyze(payload: dict):
    text = payload.get("text", "")
    res = run_pipeline(text, settings.NLP_SUMMARY_SENTENCES, settings.NLP_MAX_KEYWORDS)
    return res


@router.get("/health")
async def health():
    return {"status": "ok", "service": "nlp"}
