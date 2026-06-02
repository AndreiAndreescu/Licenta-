# Microservices Architecture

The microservices version of WebIntel splits the platform into specialized services that communicate through Redis Streams and HTTP APIs. This architecture improves scalability, fault isolation, and service autonomy while enabling independent deployment of each component.

## Components

- **API Gateway:** Routes client requests to appropriate backend services and aggregates responses.
- **Crawler Service:** Fetches web pages and publishes raw page data to the message stream.
- **Extractor Service:** Parses HTML and extracts textual content for downstream analysis.
- **NLP Service:** Performs entity extraction, sentiment analysis, and summarization using spaCy and NLP tools.
- **Storage Service:** Persists crawled content, extracted data, and analysis results in PostgreSQL.
- **Scheduler Service:** Triggers periodic crawl jobs and coordinates workflow execution.
- **React Dashboard:** Provides a separate frontend application for visualization and monitoring.
- **Redis Streams:** Used for asynchronous messaging between services and event-driven orchestration.
- **Docker Compose:** Orchestrates all services, databases, and monitoring tools together.

## Inter-Service Flow

The system is composed of decoupled services that exchange data asynchronously.

```text
[Client] --> [API Gateway] --> [React Dashboard]
                      |
                      v
                 [Scheduler Service]
                      |
                      v
                [Crawler Service]
                      |
                      v
               [Redis Streams]
                      |
                      v
              [Extractor Service]
                      |
                      v
              [NLP Service]
                      |
                      v
             [Storage Service]
                      |
                      v
                 [PostgreSQL]
```

## Summary

A distributed design separates concerns into independent services, making it easier to scale crawler capacity, isolate failures, and add new capabilities without affecting the whole platform. The API Gateway and Redis Streams enable flexible routing and asynchronous workflows.
