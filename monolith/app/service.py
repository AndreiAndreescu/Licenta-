import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import crawler, extractor, nlp
from .database import AsyncSessionLocal
from .models import Analysis, Job, Page
from .config import settings


async def run_job(job_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        return

    job.status = "running"
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    seeds = []
    if job.seed_urls:
        try:
            seeds = [url.strip() for url in json.loads(job.seed_urls) if isinstance(url, str)]
        except Exception:
            seeds = []

    try:
        pages = await crawler.crawl_job(
            job_id=job.id,
            seeds=seeds,
            query=job.query,
            max_depth=job.max_depth,
            max_pages=job.max_pages,
            db_session=db,
        )
        job.pages_crawled = len(pages)
        await db.commit()

        for page_data in pages:
            page_id = page_data.get("page_id")
            html = page_data.get("html", "")
            if page_id is None:
                continue

            page_result = await db.execute(select(Page).where(Page.id == page_id))
            page = page_result.scalars().first()
            if not page:
                continue

            extracted = extractor.extract(html, page.url)
            page.clean_text = extracted.get("clean_text")
            page.title = extracted.get("title") or page.title
            page.language = extracted.get("language") or page.language
            await db.flush()

            if page.clean_text:
                analysis_data = nlp.run_pipeline(
                    page.clean_text,
                    sentence_count=settings.NLP_SUMMARY_SENTENCES,
                    max_keywords=settings.NLP_MAX_KEYWORDS,
                )
                analysis = Analysis(
                    page_id=page.id,
                    summary=analysis_data.get("summary"),
                    keywords=json.dumps(analysis_data.get("keywords", [])),
                    sentiment_label=analysis_data.get("sentiment_label"),
                    sentiment_score=analysis_data.get("sentiment_score"),
                    entities=json.dumps(analysis_data.get("entities", {})),
                )
                db.add(analysis)
                job.pages_analyzed += 1

            await db.commit()

        pages_data = []
        for page_data in pages:
            page_id = page_data.get("page_id")
            if page_id is None:
                continue
            page_result = await db.execute(
                select(Page).where(Page.id == page_id).options(selectinload(Page.analysis))
            )
            p = page_result.scalars().first()
            if p and p.analysis:
                pages_data.append({
                    "summary": p.analysis.summary,
                    "keywords": json.loads(p.analysis.keywords or "[]"),
                    "sentiment_label": p.analysis.sentiment_label,
                    "sentiment_score": p.analysis.sentiment_score,
                })

        verdict_result = nlp.compute_verdict(job.query, pages_data)
        job.verdict = verdict_result["verdict"]
        job.verdict_confidence = verdict_result["confidence"]
        job.verdict_evidence = verdict_result["evidence"]
        await db.commit()

        job.pages_analyzed = len([p for p in pages_data if p])
        job.status = "done"
        job.updated_at = datetime.utcnow()
        await db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.updated_at = datetime.utcnow()
        await db.commit()


async def run_job_task(job_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_job(job_id, db)
