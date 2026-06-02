import json
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import service
from ..crawler import _is_url, _looks_like_domain, _search_seed_urls
from ..database import get_db
from ..models import Job, Page
from ..schemas import AnalysisResponse, JobCreate, JobResponse, JobResultsResponse, PageResponse, PageWithAnalysis

router = APIRouter(prefix="/api", tags=["jobs"])


def _parse_seed_urls(seed_urls: list[str] | None) -> list[str]:
    return [url.strip() for url in (seed_urls or []) if url.strip()]


async def _resolve_seed_urls_for_query(query: str) -> list[str]:
    if _is_url(query):
        return [query]
    if _looks_like_domain(query):
        return [f"https://{query}" if not query.startswith("http") else query]
    try:
        return await _search_seed_urls(query, max_results=5)
    except Exception:
        return []


def _job_to_response(job: Job) -> JobResponse:
    seed_urls = []
    if job.seed_urls:
        try:
            seed_urls = json.loads(job.seed_urls)
        except Exception:
            seed_urls = []
    return JobResponse(
        id=job.id,
        query=job.query,
        seed_urls=seed_urls,
        status=job.status,
        max_depth=job.max_depth,
        max_pages=job.max_pages,
        created_at=job.created_at,
        updated_at=job.updated_at,
        pages_crawled=job.pages_crawled,
        pages_analyzed=job.pages_analyzed,
        error_message=job.error_message,
        verdict=job.verdict,
        verdict_confidence=job.verdict_confidence,
        verdict_evidence=job.verdict_evidence,
    )


def _page_with_analysis(page: Page) -> PageWithAnalysis:
    analysis = None
    if page.analysis:
        keywords = []
        entities = {}
        try:
            keywords = json.loads(page.analysis.keywords or "[]")
        except Exception:
            keywords = []
        try:
            entities = json.loads(page.analysis.entities or "{}")
        except Exception:
            entities = {}
        analysis = AnalysisResponse(
            id=page.analysis.id,
            page_id=page.analysis.page_id,
            summary=page.analysis.summary,
            keywords=keywords,
            sentiment_label=page.analysis.sentiment_label,
            sentiment_score=page.analysis.sentiment_score,
            entities=entities,
        )
    return PageWithAnalysis(
        id=page.id,
        job_id=page.job_id,
        url=page.url,
        title=page.title,
        http_status=page.http_status,
        fetched_at=page.fetched_at,
        clean_text=page.clean_text,
        language=page.language,
        analysis=analysis,
    )


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> JobResponse:
    seed_urls = _parse_seed_urls(payload.seed_urls)
    if not seed_urls:
        seed_urls = await _resolve_seed_urls_for_query(payload.query)

    job = Job(
        query=payload.query,
        seed_urls=json.dumps(seed_urls),
        status="pending",
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background_tasks.add_task(service.run_job_task, job.id)
    return _job_to_response(job)


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    result = await db.execute(select(Job).order_by(desc(Job.created_at)).offset(skip).limit(limit))
    jobs = result.scalars().all()
    return [_job_to_response(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)) -> JobResponse:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(job_id: int, db: AsyncSession = Depends(get_db)) -> JobResultsResponse:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = await db.execute(
        select(Page).where(Page.job_id == job_id).options(selectinload(Page.analysis)).order_by(Page.fetched_at)
    )
    pages = result.scalars().all()
    response = _job_to_response(job)
    return JobResultsResponse(**response.model_dump(), pages=[_page_with_analysis(page) for page in pages])


@router.post("/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_claim(payload: JobCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Same as POST /jobs but semantically named for the fact-checker UI."""
    return await create_job(payload, background_tasks, db)


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    progress = 0
    if job.max_pages > 0:
        progress = min(100, int((job.pages_analyzed / job.max_pages) * 100))
    return {
        "job_id": job.id,
        "status": job.status,
        "pages_crawled": job.pages_crawled,
        "pages_analyzed": job.pages_analyzed,
        "progress_pct": progress,
    }
