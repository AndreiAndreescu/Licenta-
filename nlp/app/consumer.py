import asyncio
import logging
import json
import httpx

from webintel_common import messaging
from webintel_common.schemas import PageExtractedEvent, PageAnalyzedEvent, JobCompletedEvent
from .config import settings
from .pipeline import run_pipeline, compute_verdict

logger = logging.getLogger(__name__)


async def maybe_compute_verdict(job_id: int, http_client: httpx.AsyncClient):
    """Fetch all page analyses for job_id from storage, compute verdict, PATCH back."""
    try:
        r = await http_client.get(
            f"{settings.STORAGE_URL}/api/jobs/{job_id}/results", timeout=20.0
        )
        if r.status_code != 200:
            logger.warning("results fetch returned %s for job %s", r.status_code, job_id)
            return
        data = r.json()

        # Storage returns {job: {..., query: ...}, pages: [...]}
        job_obj = data.get("job") or data  # handle both shapes
        claim = job_obj.get("query", "")
        pages = data.get("pages", [])

        pages_data = []
        for page in pages:
            analysis = page.get("analysis")
            if not analysis:
                continue
            kw_raw = analysis.get("keywords")
            keywords = kw_raw if isinstance(kw_raw, list) else []
            if isinstance(kw_raw, str):
                try:
                    keywords = json.loads(kw_raw)
                except Exception:
                    keywords = []
            pages_data.append({
                "summary": analysis.get("summary"),
                "keywords": keywords,
                "sentiment_label": analysis.get("sentiment_label"),
                "sentiment_score": analysis.get("sentiment_score"),
            })

        result = compute_verdict(claim, pages_data)
        logger.info("verdict for job %s: %s (%s%%)", job_id, result["verdict"], result["confidence"])

        patch_r = await http_client.patch(
            f"{settings.STORAGE_URL}/api/jobs/{job_id}/verdict",
            json={
                "verdict": result["verdict"],
                "verdict_confidence": result["confidence"],
                "verdict_evidence": result["evidence"],
            },
            timeout=10.0,
        )
        if patch_r.status_code not in (200, 204):
            logger.warning("verdict PATCH returned %s", patch_r.status_code)
    except Exception:
        logger.exception("maybe_compute_verdict failed for job %s", job_id)


async def start_consumer(app):
    redis = app.state.redis

    # Ensure consumer groups exist for all streams this service reads
    for stream in ("page.extracted", "job.completed"):
        try:
            await messaging.ensure_consumer_group(redis, stream, settings.CONSUMER_GROUP)
        except Exception:
            logger.warning("ensure_consumer_group failed for %s", stream)

    # Warmup NLP models so first request isn't slow
    try:
        run_pipeline("warmup", settings.NLP_SUMMARY_SENTENCES, settings.NLP_MAX_KEYWORDS)
    except Exception:
        pass

    async def loop_extracted():
        """Consume page.extracted events, run NLP, post analysis to storage."""
        while True:
            try:
                entries = await messaging.consume(
                    redis, "page.extracted", settings.CONSUMER_GROUP,
                    settings.CONSUMER_NAME, count=5, block_ms=2000
                )
                for msg_id, payload in entries:
                    try:
                        event = PageExtractedEvent.model_validate_json(payload.get("data", "{}"))
                        logger.info("processing page %s for job %s", event.page_id, event.job_id)

                        # Fetch extracted text from storage
                        async with httpx.AsyncClient() as client:
                            ext_r = await client.get(
                                f"{settings.STORAGE_URL}/api/pages/{event.page_id}/extraction",
                                timeout=10.0,
                            )

                        if ext_r.status_code != 200:
                            logger.warning("no extraction for page %s (status %s)", event.page_id, ext_r.status_code)
                            await messaging.ack(redis, "page.extracted", settings.CONSUMER_GROUP, msg_id)
                            continue

                        clean_text = ext_r.json().get("clean_text", "")
                        if not clean_text or not clean_text.strip():
                            logger.warning("empty text for page %s", event.page_id)
                            await messaging.ack(redis, "page.extracted", settings.CONSUMER_GROUP, msg_id)
                            continue

                        # Run NLP pipeline
                        result = run_pipeline(
                            clean_text,
                            settings.NLP_SUMMARY_SENTENCES,
                            settings.NLP_MAX_KEYWORDS,
                        )

                        # Post analysis to storage
                        async with httpx.AsyncClient() as client:
                            post_r = await client.post(
                                f"{settings.STORAGE_URL}/api/pages/{event.page_id}/analysis",
                                json=result,
                                timeout=10.0,
                            )
                            if post_r.status_code not in (200, 201):
                                logger.warning("analysis POST returned %s", post_r.status_code)

                        # Publish page.analyzed
                        await messaging.publish(
                            redis, "page.analyzed",
                            PageAnalyzedEvent(job_id=event.job_id, page_id=event.page_id)
                        )
                        logger.info("analyzed page %s", event.page_id)
                    except Exception:
                        logger.exception("error processing page.extracted msg %s", msg_id)
                    finally:
                        await messaging.ack(redis, "page.extracted", settings.CONSUMER_GROUP, msg_id)

            except Exception:
                logger.exception("loop_extracted error")
                await asyncio.sleep(2)

    async def loop_completed():
        """Consume job.completed events, compute and store verdict."""
        consumer_name = settings.CONSUMER_NAME + "-verdict"
        while True:
            try:
                entries = await messaging.consume(
                    redis, "job.completed", settings.CONSUMER_GROUP,
                    consumer_name, count=5, block_ms=2000
                )
                for msg_id, payload in entries:
                    try:
                        event = JobCompletedEvent.model_validate_json(payload.get("data", "{}"))
                        logger.info("computing verdict for job %s", event.job_id)
                        async with httpx.AsyncClient() as client:
                            await maybe_compute_verdict(event.job_id, client)
                    except Exception:
                        logger.exception("error processing job.completed msg %s", msg_id)
                    finally:
                        await messaging.ack(redis, "job.completed", settings.CONSUMER_GROUP, msg_id)
            except Exception:
                logger.exception("loop_completed error")
                await asyncio.sleep(2)

    task1 = asyncio.create_task(loop_extracted())
    task2 = asyncio.create_task(loop_completed())
    app.state._nlp_task1 = task1
    app.state._nlp_task2 = task2
    return task1
