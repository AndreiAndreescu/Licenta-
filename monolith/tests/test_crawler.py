import pytest
import respx
import httpx

from app.crawler import crawl_job
from app.models import Job


@respx.mock
@pytest.mark.asyncio
async def test_crawler_respects_max_pages(db_session):
    job = Job(query="https://example.com", status="pending", max_depth=2, max_pages=2)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200, text='<html><body><a href="/page1">Page 1</a><a href="/page2">Page 2</a></body></html>')
    )
    respx.get("https://example.com/page1").mock(return_value=httpx.Response(200, text="<html><body></body></html>"))
    respx.get("https://example.com/page2").mock(return_value=httpx.Response(200, text="<html><body></body></html>"))

    pages = await crawl_job(job.id, ["https://example.com"], "https://example.com", 2, 2, db_session)
    assert len(pages) == 2


@respx.mock
@pytest.mark.asyncio
async def test_crawler_respects_max_depth(db_session):
    job = Job(query="https://example.com", status="pending", max_depth=1, max_pages=10)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200, text='<html><body><a href="/page1">Page 1</a></body></html>')
    )
    respx.get("https://example.com/page1").mock(
        return_value=httpx.Response(200, text='<html><body><a href="/page2">Page 2</a></body></html>')
    )
    respx.get("https://example.com/page2").mock(return_value=httpx.Response(200, text="<html><body></body></html>"))

    pages = await crawl_job(job.id, ["https://example.com"], "https://example.com", 1, 10, db_session)
    assert any(page["url"].endswith("/page1") for page in pages)
    assert not any(page["url"].endswith("/page2") for page in pages)


@respx.mock
@pytest.mark.asyncio
async def test_crawler_skips_already_visited_urls(db_session):
    job = Job(query="https://example.com", status="pending", max_depth=2, max_pages=10)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200, text='<html><body><a href="/page1">Page 1</a><a href="/page1">Page 1 again</a></body></html>')
    )
    respx.get("https://example.com/page1").mock(return_value=httpx.Response(200, text="<html><body></body></html>"))

    pages = await crawl_job(job.id, ["https://example.com"], "https://example.com", 2, 10, db_session)
    assert len(pages) == 2
    assert len({page["url"] for page in pages}) == 2


@respx.mock
@pytest.mark.asyncio
async def test_crawler_handles_http_errors_gracefully(db_session):
    job = Job(query="https://error.example", status="pending", max_depth=1, max_pages=10)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    respx.get("https://error.example/robots.txt").mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    respx.get("https://error.example").mock(side_effect=httpx.ConnectError("connection failed"))

    pages = await crawl_job(job.id, ["https://error.example"], "https://error.example", 1, 10, db_session)
    assert len(pages) == 1
    assert pages[0]["http_status"] == -1 or pages[0]["http_status"] == -1
