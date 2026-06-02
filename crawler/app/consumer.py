import asyncio
import logging
import json

from webintel_common import messaging
from webintel_common.schemas import JobCreatedEvent
from .config import settings
from .crawler import crawl

logger = logging.getLogger(__name__)


async def start_consumer(app):
    redis = app.state.redis
    await messaging.ensure_consumer_group(redis, "job.created", settings.CONSUMER_GROUP)

    async def loop():
        while True:
            try:
                entries = await messaging.consume(redis, "job.created", settings.CONSUMER_GROUP, settings.CONSUMER_NAME)
                for msg_id, payload in entries:
                    try:
                        data = json.loads(payload.get("data", "{}"))
                        event = JobCreatedEvent.model_validate_json(payload.get("data", "{}"))
                        # run crawl in background but await to ensure processing for tests
                        await crawl(event.job_id, event.seed_urls, event.max_depth, event.max_pages, redis, settings.STORAGE_URL)
                        await messaging.ack(redis, "job.created", settings.CONSUMER_GROUP, msg_id)
                    except Exception:
                        logger.exception("processing message failed")
                        # do not ack
                await asyncio.sleep(0.1)
            except Exception:
                logger.exception("consumer loop error")
                await asyncio.sleep(1)

    task = asyncio.create_task(loop())
    app.state._consumer_task = task
    return task
