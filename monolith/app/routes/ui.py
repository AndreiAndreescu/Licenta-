from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Job, Page

router = APIRouter()
root_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(root_dir / "templates"))


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/result/{job_id}")
async def result(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pages_result = await db.execute(
        select(Page)
        .where(Page.job_id == job_id)
        .options(selectinload(Page.analysis))
        .order_by(Page.fetched_at)
    )
    pages = pages_result.scalars().all()

    sources = []
    for page in pages:
        keywords = []
        if page.analysis and page.analysis.keywords:
            try:
                keywords = json.loads(page.analysis.keywords)
            except Exception:
                keywords = []
        sources.append({
            "url": page.url,
            "title": page.title or page.url,
            "sentiment": page.analysis.sentiment_label if page.analysis else "pending",
            "summary": page.analysis.summary if page.analysis else "",
            "keywords": keywords[:6],
        })

    return templates.TemplateResponse("result.html", {
        "request": request,
        "job": job,
        "sources": sources,
    })
