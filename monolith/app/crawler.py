import asyncio
import time
from datetime import datetime
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from .config import settings
from .models import Page


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None
    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    return urljoin(base_url, href)


def _get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()



def _is_url(text: str) -> bool:
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _looks_like_domain(text: str) -> bool:
    if not text or " " in text:
        return False
    parsed = urlparse(text if text.startswith("http") else f"https://{text}")
    return bool(parsed.netloc and "." in parsed.netloc)


async def _search_seed_urls(query: str, max_results: int = 10) -> list[str]:
    from urllib.parse import quote_plus, unquote
    import re
    encoded = quote_plus(query)
    urls = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def clean_urls(raw: list[str]) -> list[str]:
        bad = {
            "r.bing.com", "th.bing.com", "bing.com/rs", "bing.com/th",
            "bing.com/images", "bing.com/videos", "bing.com/aclick",
            "bing.net", "bingapis.com", "microsoft.com", "msn.com",
            "facebook.com", "twitter.com", "instagram.com", "tiktok.com",
            "youtube.com", "linkedin.com", "pinterest.com",
            "amazon.com", "ebay.com", "doubleclick", "analytics",
            "go.microsoft", "microsofttranslator", "live.com",
        }
        bad_ext = ('.css', '.js', '.png', '.jpg', '.gif', '.ico',
                   '.svg', '.woff', '.ttf', '.map', '.json')
        result = []
        for u in raw:
            u = u.strip().split('#')[0]
            if not u or len(u) < 20:
                continue
            if not u.startswith('http'):
                continue
            if u.endswith(bad_ext):
                continue
            if any(b in u for b in bad):
                continue
            result.append(u)
        return result

    # Source 1: Wikipedia Search API — always works, no blocking
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(
                f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded}&limit=5&format=json&namespace=0",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code == 200:
                data = r.json()
                if len(data) > 3:
                    urls += clean_urls(data[3])
    except Exception:
        pass

    # Source 2: Wikipedia full text search for related articles
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(
                f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&srlimit=5&format=json",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code == 200:
                data = r.json()
                pages = data.get("query", {}).get("search", [])
                for p in pages:
                    title = p.get("title", "").replace(" ", "_")
                    if title:
                        urls.append(f"https://en.wikipedia.org/wiki/{title}")
    except Exception:
        pass

    # Source 3: DuckDuckGo — extract uddg= encoded URLs (real results)
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(
                f"https://html.duckduckgo.com/html/?q={encoded}",
                headers=headers
            )
            if r.status_code == 200:
                found = re.findall(r'uddg=(https?%3A%2F%2F[^&">\s]+)', r.text)
                decoded = [unquote(u) for u in found]
                urls += clean_urls(decoded)
    except Exception:
        pass

    # Source 4: Bing RSS feed — clean XML, real URLs in <link> tags
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(
                f"https://www.bing.com/search?q={encoded}&format=rss",
                headers=headers
            )
            if r.status_code == 200:
                found = re.findall(r'<link>(https?://[^<\s]+)</link>', r.text)
                urls += clean_urls([u for u in found if "bing.com" not in u])
    except Exception:
        pass

    # Source 5: Google — extract /url?q= decoded URLs
    if len(urls) < 5:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                r = await client.get(
                    f"https://www.google.com/search?q={encoded}&num=10&hl=en&gl=en",
                    headers=headers
                )
                if r.status_code == 200:
                    found = re.findall(r'/url\?q=(https?://(?!google|youtube|gstatic)[^&\s]+)&amp;', r.text)
                    decoded = [unquote(u) for u in found]
                    urls += clean_urls(decoded)
        except Exception:
            pass

    # Source 6: Brave Search
    if len(urls) < 5:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                r = await client.get(
                    f"https://search.brave.com/search?q={encoded}&source=web",
                    headers=headers
                )
                if r.status_code == 200:
                    found = re.findall(r'href="(https?://(?!brave|search\.brave)[^"]+)"[^>]*data-pos', r.text)
                    urls += clean_urls(found)
        except Exception:
            pass

    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)

    return result[:max_results]

async def _load_robots(client: httpx.AsyncClient, domain: str) -> RobotFileParser:
    parser = RobotFileParser()
    robots_url = f"https://{domain}/robots.txt"
    try:
        response = await client.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=10.0)
        if response.status_code == 200 and response.text:
            parser.parse(response.text.splitlines())
        else:
            parser.allow_all = True
    except httpx.HTTPError:
        parser.allow_all = True
    return parser


async def crawl_job(job_id: int, seeds: list[str], query: str, max_depth: int, max_pages: int, db_session) -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=15.0) as client:
        if not seeds:
            if _is_url(query):
                seeds = [query]
            elif _looks_like_domain(query):
                seeds = [f"https://{query}" if not query.startswith("http") else query]
            else:
                seeds = await _search_seed_urls(query, max_results=3)

        if not seeds:
            seeds = [query] if query.startswith("http") else []

        visited: set[str] = set()
    queue: list[tuple[str, int]] = []
    last_fetch: dict[str, float] = {}
    robots_cache: dict[str, RobotFileParser] = {}
    allowed_domains: set[str] = set()

    if seeds:
        for seed in seeds:
            normalized = seed.strip()
            if normalized:
                queue.append((normalized, 0))
                allowed_domains.add(_get_domain(normalized))
    else:
        queue.append((query, 0))

    results: list[dict] = []

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=15.0) as client:
        while queue and len(results) < max_pages:
            url, depth = queue.pop(0)
            normalized = url.strip()
            if not normalized:
                continue
            if normalized in visited:
                continue
            if depth > max_depth:
                continue

            visited.add(normalized)
            domain = _get_domain(normalized)
            if allowed_domains and domain not in allowed_domains:
                continue

            parser = robots_cache.get(domain)
            if parser is None:
                parser = await _load_robots(client, domain)
                robots_cache[domain] = parser
            if not parser.can_fetch(USER_AGENT, normalized):
                continue

            last = last_fetch.get(domain)
            if last is not None:
                elapsed = time.time() - last
                if elapsed < settings.CRAWL_DELAY_SECONDS:
                    await asyncio.sleep(settings.CRAWL_DELAY_SECONDS - elapsed)

            try:
                response = await client.get(normalized)
                status = response.status_code
                html = response.text if response.status_code == 200 else ""
            except httpx.HTTPError:
                status = -1
                html = ""

            page = Page(
                job_id=job_id,
                url=normalized,
                http_status=status,
                fetched_at=datetime.utcnow(),
            )
            db_session.add(page)
            await db_session.flush()

            if status == 200 and html:
                soup = BeautifulSoup(html, "lxml")
                for anchor in soup.find_all("a", href=True):
                    linked = _normalize_url(normalized, anchor["href"])
                    if linked and linked not in visited and len(results) + len(queue) < max_pages:
                        if not allowed_domains or _get_domain(linked) in allowed_domains:
                            queue.append((linked, depth + 1))
            last_fetch[domain] = time.time()
            results.append(
                {
                    "page_id": page.id,
                    "url": normalized,
                    "html": html,
                    "http_status": status,
                }
            )

            if len(results) >= max_pages:
                break

    return results
