# API Contracts

This document describes the API contracts and interface expectations for both the monolithic and microservices systems.

## Monolithic API

The monolithic application exposes endpoints for web crawling, data extraction, NLP analysis, and dashboard access. The API is served from a single FastAPI app with shared models.

## Microservices API

The microservices architecture uses an API Gateway to expose a unified external API. Internal services are separated and communicate via HTTP or Redis Streams. The key contracts include:

- Gateway to Scheduler
- Gateway to Crawler
- Gateway to Extractor
- Gateway to NLP
- Gateway to Storage

## Future Work

As services evolve, this document will include request/response schema definitions, authentication requirements, and event payload formats for Redis Streams.
