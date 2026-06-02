import asyncio
import logging
import json

from webintel_common import messaging
from webintel_common.schemas import PageCrawledEvent, PageExtractedEvent, PageAnalyzedEvent
from .config import settings
from .extractor import extract
import httpx

logger = logging.getLogger(__name__)


async def start_consumer(app):
    redis = app.state.redis
    await messaging.ensure_consumer_group(redis, "page.crawled", settings.CONSUMER_GROUP)

    async def loop():
        while True:
            try:
                entries = await messaging.consume(redis, "page.crawled", settings.CONSUMER_GROUP, settings.CONSUMER_NAME)
                for msg_id, payload in entries:
                    try:
                        event = PageCrawledEvent.model_validate_json(payload.get("data", "{}"))
                        # fetch html
                        html = await redis.get(event.html_redis_key)
                        if not html:
                            logger.warning("no html for %s", event.html_redis_key)
                            await messaging.publish(redis, "page.analyzed", PageAnalyzedEvent(job_id=event.job_id, page_id=event.page_id))
                            await messaging.ack(redis, "page.crawled", settings.CONSUMER_GROUP, msg_id)
                            continue
                        res = extract(html, event.url)
                        if not res.get("clean_text") or len(res.get("clean_text")) < 50:
                            await messaging.publish(redis, "page.analyzed", PageAnalyzedEvent(job_id=event.job_id, page_id=event.page_id))
                            await messaging.ack(redis, "page.crawled", settings.CONSUMER_GROUP, msg_id)
                            continue
                        # post to storage
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.post(f"{settings.STORAGE_URL}/api/pages/{event.page_id}/extraction", json=res, timeout=10.0)
                            # set text:{page_id}
                            await redis.set(f"text:{event.page_id}", res.get("clean_text"), ex=7200)
                            # publish page.extracted
                            await messaging.publish(redis, "page.extracted", PageExtractedEvent(job_id=event.job_id, page_id=event.page_id))
                        except Exception:
                            logger.exception("failed to post extraction")
                        await messaging.ack(redis, "page.crawled", settings.CONSUMER_GROUP, msg_id)
                    except Exception:
                        logger.exception("processing page.crawled failed")
                await asyncio.sleep(0.1)
            except Exception:
                logger.exception("consumer loop error")
                await asyncio.sleep(1)

    task = asyncio.create_task(loop())
    app.state._consumer_task = task
    return task
