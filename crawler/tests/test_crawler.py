import pytest
import respx
from httpx import Response

from app.crawler import crawl


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.streams = {}

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def xadd(self, stream, data):
        self.streams.setdefault(stream, []).append(data)
        return "1-0"


@pytest.mark.anyio
async def test_crawl_respects_max_pages(respx_mock):
    respx_mock.get("https://example.com").respond(200, text="<html><a href=\"https://example.com/1\">link</a></html>")
    respx_mock.get("https://example.com/1").respond(200, text="<html></html>")
    fake_redis = FakeRedis()
    count = await crawl(1, 1, ["https://example.com"], max_depth=2, max_pages=1, redis_client=fake_redis, storage_url="http://storage:8001")
    assert count == 1


@pytest.mark.anyio
async def test_crawl_skips_visited(respx_mock):
    respx_mock.get("https://example.com").respond(200, text='<a href="https://example.com">self</a>')
    fake_redis = FakeRedis()
    count = await crawl(1, 1, ["https://example.com"], max_depth=2, max_pages=10, redis_client=fake_redis, storage_url="http://storage:8001")
    assert count == 1


@pytest.mark.anyio
async def test_crawl_stores_html_and_publishes(respx_mock):
    respx_mock.get("https://example.com").respond(200, text="<html></html>")
    fake_redis = FakeRedis()
    count = await crawl(1, 1, ["https://example.com"], max_depth=0, max_pages=1, redis_client=fake_redis, storage_url="http://storage:8001")
    assert count == 1
    assert any(k.startswith("html:1:1:0") for k in fake_redis.store.keys())
    assert "stream:page.crawled" in fake_redis.streams


@pytest.mark.anyio
async def test_crawl_handles_404(respx_mock):
    respx_mock.get("https://notfound.example").respond(404)
    fake_redis = FakeRedis()
    count = await crawl(1, 1, ["https://notfound.example"], max_depth=0, max_pages=1, redis_client=fake_redis, storage_url="http://storage:8001")
    assert count == 1
