import json
import logging

try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None
from pydantic import BaseModel

STREAMS = {
    "job.created": "stream:job.created",
    "page.crawled": "stream:page.crawled",
    "page.extracted": "stream:page.extracted",
    "page.analyzed": "stream:page.analyzed",
    "job.crawl_finished": "stream:job.crawl_finished",
    "job.completed": "stream:job.completed",
}


def _decode_dict(data: dict[bytes, bytes]) -> dict[str, str]:
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}


async def get_redis(url: str):
    if aioredis is None:
        raise RuntimeError("redis.asyncio is not available in this environment")
    client = aioredis.Redis.from_url(url, decode_responses=True)
    await client.ping()
    return client


async def publish(redis, stream_name: str, payload: BaseModel) -> str:
    data = {"data": payload.model_dump_json()}
    message_id = await redis.xadd(STREAMS[stream_name], data)
    return message_id


async def ensure_consumer_group(redis, stream_name: str, group_name: str) -> None:
    if aioredis is None:
        # assume fakeredis or a test double; attempt to create group if supported
        try:
            await redis.xgroup_create(STREAMS[stream_name], group_name, id="$", mkstream=True)
        except Exception:
            return
        return
    stream = STREAMS[stream_name]
    try:
        await redis.xgroup_create(stream, group_name, id="$", mkstream=True)
    except Exception as exc:
        if aioredis is not None and hasattr(aioredis, "exceptions") and "BUSYGROUP" in str(exc):
            return
        return


async def consume(redis, stream_name: str, group_name: str, consumer_name: str, count: int = 10, block_ms: int = 2000) -> list[tuple[str, dict[str, str]]]:
    stream = STREAMS[stream_name]
    result = await redis.xreadgroup(group_name, consumer_name, {stream: ">"}, count=count, block=block_ms)
    entries: list[tuple[str, dict[str, str]]] = []
    if not result:
        return entries
    for _, messages in result:
        for msg_id, payload in messages:
            entries.append((msg_id, _decode_dict(payload)))
    return entries


async def ack(redis, stream_name: str, group_name: str, msg_id: str) -> int:
    stream = STREAMS[stream_name]
    return await redis.xack(stream, group_name, msg_id)
