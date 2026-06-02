import asyncio
import logging
import json

from webintel_common import messaging
from webintel_common.schemas import PageCrawledEvent, JobCrawlFinishedEvent, PageAnalyzedEvent
from .scheduler import increment_counter, mark_job_complete
from .config import settings

logger = logging.getLogger(__name__)


async def start_consumer(app):
    redis = app.state.redis
    http_client = app.state.http_client
    
    await messaging.ensure_consumer_group(redis, "page.crawled", settings.CONSUMER_GROUP)
    await messaging.ensure_consumer_group(redis, "job.crawl_finished", settings.CONSUMER_GROUP)
    await messaging.ensure_consumer_group(redis, "page.analyzed", settings.CONSUMER_GROUP)

    async def consume_crawled():
        while True:
            try:
                entries = await messaging.consume(redis, "page.crawled", settings.CONSUMER_GROUP, settings.CONSUMER_NAME + "_crawled")
                for msg_id, payload in entries:
                    try:
                        event = PageCrawledEvent.model_validate_json(payload.get("data", "{}"))
                        await increment_counter(redis, event.job_id, "crawled")
                        await messaging.ack(redis, "page.crawled", settings.CONSUMER_GROUP, msg_id)
                    except Exception:
                        logger.exception("processing page.crawled failed")
                await asyncio.sleep(0.1)
            except Exception:
                logger.exception("consume_crawled loop error")
                await asyncio.sleep(1)

    async def consume_crawl_finished():
        while True:
            try:
                entries = await messaging.consume(redis, "job.crawl_finished", settings.CONSUMER_GROUP, settings.CONSUMER_NAME + "_crawl_fin")
                for msg_id, payload in entries:
                    try:
                        event = JobCrawlFinishedEvent.model_validate_json(payload.get("data", "{}"))
                        await redis.set(f"counter:{event.job_id}:expected", event.total_pages_crawled)
                        analyzed = int(await redis.get(f"counter:{event.job_id}:analyzed") or 0)
                        if analyzed >= event.total_pages_crawled:
                            await mark_job_complete(event.job_id, settings.STORAGE_URL, redis, http_client)
                        await messaging.ack(redis, "job.crawl_finished", settings.CONSUMER_GROUP, msg_id)
                    except Exception:
                        logger.exception("processing job.crawl_finished failed")
                await asyncio.sleep(0.1)
            except Exception:
                logger.exception("consume_crawl_finished loop error")
                await asyncio.sleep(1)

    async def consume_analyzed():
        while True:
            try:
                entries = await messaging.consume(redis, "page.analyzed", settings.CONSUMER_GROUP, settings.CONSUMER_NAME + "_analyzed")
                for msg_id, payload in entries:
                    try:
                        event = PageAnalyzedEvent.model_validate_json(payload.get("data", "{}"))
                        await increment_counter(redis, event.job_id, "analyzed")
                        analyzed = int(await redis.get(f"counter:{event.job_id}:analyzed") or 0)
                        expected = int(await redis.get(f"counter:{event.job_id}:expected") or 0)
                        if expected > 0 and analyzed >= expected:
                            await mark_job_complete(event.job_id, settings.STORAGE_URL, redis, http_client)
                        await messaging.ack(redis, "page.analyzed", settings.CONSUMER_GROUP, msg_id)
                    except Exception:
                        logger.exception("processing page.analyzed failed")
                await asyncio.sleep(0.1)
            except Exception:
                logger.exception("consume_analyzed loop error")
                await asyncio.sleep(1)

    tasks = [
        asyncio.create_task(consume_crawled()),
        asyncio.create_task(consume_crawl_finished()),
        asyncio.create_task(consume_analyzed()),
    ]
    app.state._consumer_tasks = tasks
