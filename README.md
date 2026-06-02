# WebIntel: Distributed Microservice Platform vs Monolithic Architecture

WebIntel is a web data extraction platform comparing a traditional monolithic architecture with a distributed microservices design. The system performs web crawling, text extraction, NLP analysis, and serves results via a dashboard.

## Architecture Overview

- **Monolithic Version:** A single FastAPI application handles web crawling, extraction, NLP processing, persistence, and dashboard rendering in one container.
- **Microservices Version:** The system is split into dedicated services with an API Gateway, separate crawler, extractor, NLP, storage, scheduler, and a React dashboard, communicating asynchronously through Redis Streams.

## How to Run

### Monolith

```bash
docker compose up --build
```

### Microservices

```bash
docker compose up --build
```

## Tech Stack

- FastAPI
- SQLite
- PostgreSQL
- Redis
- Docker
- spaCy
- BeautifulSoup
- React
- Prometheus
- Grafana
