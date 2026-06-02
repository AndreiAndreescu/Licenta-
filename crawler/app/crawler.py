import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from urllib import robotparser

from .config import settings
from webintel_common.schemas import PageCrawledEvent, JobCrawlFinishedEvent
from webintel_common import messaging

logger = logging.getLogger(__name__)

SKIP_EXT_RE = re.compile(r"\.(pdf|jpg|jpeg|png|gif|css|js)$", re.IGNORECASE)


async def crawl(job_id: int, seed_urls: list[str], max_depth: int, max_pages: int, redis_client, storage_url: str) -> int:
    visited = set()
    q: asyncio.Queue = asyncio.Queue()
    for u in seed_urls:
        await q.put((u, 0))

    sem = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
    last_fetch: dict[str, float] = {}
    robots_cache: dict[str, robotparser.RobotFileParser] = {}
    total_crawled = 0

    async def fetch(url: str) -> tuple[str, int, str]:
        try:
            async with sem:
                parsed = urlparse(url)
                host = parsed.netloc
                # robots
                rp = robots_cache.get(host)
                if rp is None:
                    rp = robotparser.RobotFileParser()
                    try:
                        robots_url = f"{parsed.scheme}://{host}/robots.txt"
                        r = await httpx.AsyncClient().get(robots_url, timeout=5.0)
                        if r.status_code == 200:
                            rp.parse(r.text.splitlines())
                    except Exception:
                        pass
                    robots_cache[host] = rp
                if hasattr(rp, "can_fetch") and not rp.can_fetch(settings.USER_AGENT, url):
                    return "", 403, ""

                # polite delay
                last = last_fetch.get(host)
                if last:
                    since = asyncio.get_event_loop().time() - last
                    if since < settings.CRAWL_DELAY_SECONDS:
                        await asyncio.sleep(settings.CRAWL_DELAY_SECONDS - since)
                last_fetch[host] = asyncio.get_event_loop().time()

                headers = {"User-Agent": settings.USER_AGENT}
                async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                    resp = await client.get(url)
                return resp.text, resp.status_code, resp.headers.get("content-type", "")
        except Exception as exc:
            logger.exception("fetch error %s", exc)
            return "", -1, ""

    async def worker():
        nonlocal total_crawled
        while not q.empty() and total_crawled < max_pages:
            url, depth = await q.get()
            if url in visited:
                q.task_done()
                continue
            visited.add(url)
            if depth > max_depth:
                q.task_done()
                continue
            if SKIP_EXT_RE.search(url):
                q.task_done()
                continue

            html, status, content_type = await fetch(url)
            # send to storage and capture the assigned page_id
            fetched_at = datetime.now(timezone.utc).isoformat()
            actual_page_id = None
            try:
                page_payload = {"url": url, "http_status": status, "fetched_at": fetched_at}
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{storage_url}/api/jobs/{job_id}/pages",
                        json=page_payload, timeout=10.0
                    )
                    if resp.status_code == 201:
                        actual_page_id = resp.json().get("id")
            except Exception:
                logger.exception("failed to post page to storage")

            if actual_page_id is None:
                q.task_done()
                continue

            html_key = f"html:{job_id}:{actual_page_id}:{total_crawled}"
            try:
                if html and status > 0:
                    await redis_client.set(html_key, html, ex=settings.HTML_TTL_SECONDS)
            except Exception:
                logger.exception("redis set failed")

            # publish page.crawled event
            try:
                event = PageCrawledEvent(job_id=job_id, page_id=actual_page_id, url=url, html_redis_key=html_key)
                await messaging.publish(redis_client, "page.crawled", event)
            except Exception:
                logger.exception("publish failed")

            total_crawled += 1

            # parse links
            if html and status == 200 and "text/html" in content_type:
                try:
                    soup = BeautifulSoup(html, "lxml")
                    for a in soup.find_all("a", href=True):
                        href = urljoin(url, a["href"])
                        parsed_href = urlparse(href)
                        if parsed_href.scheme not in ("http", "https"):
                            continue
                        # same domain only
                        if parsed_href.netloc != urlparse(url).netloc:
                            continue
                        if href in visited:
                            continue
                        await q.put((href, depth + 1))
                except Exception:
                    logger.exception("parse links failed")

            q.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(settings.MAX_CONCURRENT_REQUESTS)]
    await asyncio.gather(*workers, return_exceptions=True)
    # drain any remaining queued URLs that workers left unprocessed (max_pages reached)
    while not q.empty():
        try:
            q.get_nowait()
            q.task_done()
        except asyncio.QueueEmpty:
            break

    # publish crawl finished
    try:
        event = JobCrawlFinishedEvent(job_id=job_id, total_pages_crawled=total_crawled)
        await messaging.publish(redis_client, "job.crawl_finished", event)
    except Exception:
        logger.exception("publish crawl finished failed")

    return total_crawled
