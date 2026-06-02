# WebIntel — Thesis Summary

## Project Title

**Monolithic vs Microservices Architecture: A Practical Comparison Using a Web Intelligence Platform**

---

## Goal

The thesis builds and compares two functionally identical implementations of a fact-checking web application called **WebIntel**. A user submits a natural-language claim (e.g. "Earth is round", "Russia is in the EU"). The system crawls the web, extracts and analyses the text of relevant pages with NLP, and returns a verdict: **TRUE**, **FALSE**, or **UNCERTAIN**, together with a confidence score and a text evidence snippet.

The two implementations share the same end-user behaviour but differ radically in internal architecture:

| Property | Monolith | Microservices |
|---|---|---|
| Deployment unit | One Docker container | 13 Docker containers |
| Database | SQLite (file, in-container) | PostgreSQL (dedicated container) |
| Messaging | None (in-process function calls) | Redis Streams (async event bus) |
| Frontend | Jinja2 server-rendered HTML | React SPA (separate container) |
| Observability | None | Prometheus + Grafana |
| Entry point | `localhost:8006` | Gateway `localhost:8000`, Dashboard `localhost:3000` |

The core research question is: **what does moving from monolith to microservices cost and gain in a real, running system?** The answer is measured across response latency, resource usage, deployment complexity, failure isolation, and development effort.

---

## Architecture

### Monolith

```
[Browser] ──► [FastAPI app :8006]
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
      [Crawler] [Extractor] [NLP]
                    │
                    ▼
                [SQLite]
                    │
                    ▼
           [Jinja2 Dashboard]
```

All processing runs inside a single Python process. FastAPI `BackgroundTasks` triggers the crawl pipeline when a job is submitted. The entire job — seed URL discovery, crawling, HTML extraction, NLP analysis, and verdict computation — executes sequentially in one async task. Results are stored in SQLite and rendered server-side.

**Key files:**
- `monolith/app/crawler.py` — seed URL discovery (6 sources: Wikipedia API ×2, DuckDuckGo, Bing RSS, Google, Brave) + BFS web crawl with robots.txt respect and polite delay
- `monolith/app/extractor.py` — HTML → clean text using BeautifulSoup + trafilatura/readability
- `monolith/app/nlp.py` — summarisation (sumy/LSA), keyword extraction (YAKE), sentiment (VADER), NER (spaCy en_core_web_sm), verdict computation
- `monolith/app/service.py` — orchestrates the full pipeline per job
- `monolith/app/routes/api.py` — REST endpoints (`POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/results`, `GET /api/seed-urls`)
- `monolith/app/routes/ui.py` — Jinja2 page rendering

### Microservices

```
[Browser] ──► [React Dashboard :3000]
                    │
                    ▼
[Browser] ──► [API Gateway :8000]
                    │
                    ▼
            [Scheduler :8005]
            Seeds URLs, creates Job in Storage,
            publishes job.created to Redis Stream
                    │
                    ▼ (Redis Stream: job.created)
            [Crawler :8002]
            Fetches pages, stores HTML in Redis,
            publishes page.crawled events
                    │
                    ▼ (Redis Stream: page.crawled)
            [Extractor :8003]
            Reads HTML from Redis, extracts clean text,
            stores Extraction in Storage,
            publishes page.extracted events
                    │
                    ▼ (Redis Stream: page.extracted)
            [NLP :8004]
            Runs summarisation/keywords/sentiment/NER,
            stores Analysis in Storage,
            publishes page.analyzed events
                    │
                    ▼ (Redis Stream: page.analyzed / job.crawl_finished)
            [Scheduler consumer]
            Tracks counters in Redis, calls Storage PATCH
            to set pages_crawled, pages_analyzed, status=done,
            publishes job.completed
                    │
                    ▼
            [Storage :8001] ──► [PostgreSQL]
```

**Redis stream keys:**
`stream:job.created` → `stream:page.crawled` → `stream:page.extracted` → `stream:page.analyzed` → `stream:job.crawl_finished` → `stream:job.completed`

**Key files per service:**

| Service | Port | Key file | Responsibility |
|---|---|---|---|
| gateway | 8000 | `proxy.py` | Reverse-proxies all `/api/*` calls to scheduler or storage |
| scheduler | 8005 | `routes.py`, `scheduler.py`, `consumer.py` | Job creation, seed URL search, pipeline progress tracking |
| crawler | 8002 | `crawler.py`, `consumer.py` | BFS crawl, robots.txt, Redis HTML store |
| extractor | 8003 | `extractor.py`, `consumer.py` | HTML extraction from Redis |
| nlp | 8004 | `pipeline.py`, `consumer.py` | Full NLP pipeline + verdict |
| storage | 8001 | `routes.py`, `models.py` | PostgreSQL persistence (Jobs, Pages, Extractions, Analyses) |
| dashboard | 3000 | React SPA | Job submission UI, live progress polling, results display |

**Observability stack:** Prometheus scrapes all services every 15 s; Grafana dashboards show per-service request rates, latency, and error counts. Redis and PostgreSQL exporters expose DB-level metrics.

---

## NLP Pipeline

Both implementations run the same NLP logic (kept in sync):

1. **Summarisation** — sumy LSA, 3 sentences. Falls back to first 3 sentences if sumy fails.
2. **Keyword extraction** — YAKE, up to 10 keywords.
3. **Sentiment analysis** — VADER `compound` score → `positive` / `negative` / `neutral`.
4. **Named entity recognition** — spaCy `en_core_web_sm`, entities grouped by label (PERSON, ORG, GPE, …).

### Verdict Algorithm (`compute_verdict`)

For each crawled page the algorithm computes a **relevance score** (fraction of claim keywords that appear in the page summary + keywords) and a **weighted directional score**:

- Pages containing debunking signals ("myth", "debunked", "no evidence", "disproven", …) are treated as contradicting the claim.
- Pages containing support signals ("confirmed", "evidence shows", "verified", …) are treated as supporting.
- Otherwise raw VADER sentiment is used as the signal.

`support_ratio = support_weight / (support_weight + contradict_weight)`

| `support_ratio` | Verdict |
|---|---|
| ≥ 0.62 | TRUE |
| ≤ 0.38 | FALSE |
| otherwise | UNCERTAIN |

Confidence is clamped to [35, 90] and scaled by a relevance factor. Pages shorter than 50 characters or containing CAPTCHA/junk signals are discarded before scoring.

### Seed URL Discovery (`_search_seed_urls`)

Both implementations search 6 sources in order, stopping early if enough URLs accumulate:

1. Wikipedia opensearch API (exact title match)
2. Wikipedia full-text search API (related articles)
3. DuckDuckGo HTML (`uddg=` encoded URLs)
4. Bing RSS feed (`<link>` tags)
5. Google (`/url?q=` redirects, decoded)
6. Brave Search (`data-pos` anchors)

A `clean_urls()` helper strips fragments, filters social media / ad / CDN domains, and rejects static asset extensions.

---

## Data Model

### Monolith (SQLite)

```
Job
  id, query, status, max_depth, max_pages
  pages_crawled, pages_analyzed
  verdict, verdict_confidence, verdict_evidence
  seed_urls (JSON string)
  created_at, updated_at, error_message

Page
  id, job_id, url, title, http_status
  clean_text, language, fetched_at

Analysis
  id, page_id, summary, keywords (JSON)
  sentiment_label, sentiment_score, entities (JSON)
```

### Microservices (PostgreSQL)

```
Job              (same fields as monolith)
Page             (id, job_id, url, title, http_status, fetched_at, language)
Extraction       (id, page_id, clean_text, author, publish_date)
Analysis         (id, page_id, summary, keywords, sentiment_label,
                  sentiment_score, entities)
```

Microservices split the monolith `Page.clean_text` into a separate `Extraction` table, separating concerns between crawling (Page) and content extraction (Extraction).

---

## Current State / Progress

### Working

- Both sites start cleanly with `docker compose up` and are visually pixel-identical.
- Job submission, crawling, extraction, NLP analysis, and verdict display all function end-to-end in both implementations.
- Seed URL discovery reliably returns real, crawlable URLs (after fixing bot user-agent blocking and URL extraction from search engine HTML).
- The crawler uses a browser User-Agent (`Chrome/120`) so robots.txt allows it on Wikipedia, news sites, and encyclopaedic sources.
- Microservices page counter bug fixed: `pages_crawled` and `pages_analyzed` are written to PostgreSQL by `mark_job_complete` (reads Redis counters before deleting them). The `/results` endpoint also recomputes both counts from actual DB rows as a belt-and-suspenders fallback.
- Verdict algorithm iteratively improved: relevance matching, debunking/support signal detection, CAPTCHA page filtering, junk domain filtering.
- Locust benchmark suite is ready (`benchmarks/`) to compare the two architectures under load.
- Prometheus + Grafana monitoring live on the microservices stack.

### Known Limitations

- **Verdict accuracy** is fundamentally limited by the NLP approach. The system maps sentiment on relevant pages to TRUE/FALSE but cannot perform logical reasoning. A claim like "Russia is in the EU" may return UNCERTAIN or even TRUE if the search returns many positive articles about Russia and EU relations separately.
- **Single-page crawl depth** per job (max_depth=1 in practice) limits evidence diversity for niche claims.
- **Search engine scraping** is fragile — Google and Bing frequently change their HTML structure and may block scrapers. Wikipedia API sources are always reliable.
- The monolith uses **SQLite**, which serialises writes and will bottleneck under concurrent jobs. This is intentional for the thesis comparison.
- The postgres-exporter container logs a config warning (`postgres_exporter.yml: no such file or directory`) — harmless, the exporter still runs.

---

## Open Questions

1. **Benchmark results** — The Locust suite exists but formal benchmark runs comparing throughput, p95 latency, and error rates under 10/50/100 concurrent users have not yet been executed. This is the primary remaining empirical work.

2. **Resource utilisation** — Does the microservices stack actually use more RAM/CPU in steady state? Docker stats should be captured and compared.

3. **Verdict quality** — Should a secondary NLP step (e.g. a zero-shot classifier or a sentence-similarity model) be added to improve claim-vs-page relevance, beyond keyword overlap?

4. **Failure isolation** — The thesis claims microservices offer better fault isolation. This should be demonstrated by killing individual services (e.g. the NLP container) and showing that the rest of the pipeline degrades gracefully, while the monolith fails entirely.

5. **Deployment complexity cost** — Quantify: lines of Docker/config, time to first deployment, onboarding time. This is qualitative but important for the thesis argument.

6. **Scalability demonstration** — Run multiple crawler replicas in the microservices stack and show horizontal scaling. The Redis Stream consumer group already supports this (each replica gets a partition of messages).

---

## Tech Stack Reference

| Layer | Monolith | Microservices |
|---|---|---|
| Web framework | FastAPI | FastAPI (×6 services) |
| Frontend | Jinja2 + HTML/CSS | React + TypeScript |
| Database | SQLite (aiosqlite) | PostgreSQL (asyncpg / SQLAlchemy async) |
| Messaging | — | Redis Streams |
| NLP | spaCy, VADER, sumy, YAKE | same |
| Crawling | httpx + BeautifulSoup | httpx + BeautifulSoup |
| Containerisation | Docker Compose (1 service) | Docker Compose (13 services) |
| Monitoring | — | Prometheus + Grafana |
| Load testing | Locust | Locust |
| Migrations | — | Alembic |
