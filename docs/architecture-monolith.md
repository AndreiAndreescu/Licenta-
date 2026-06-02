# Monolithic Architecture

The monolithic version of WebIntel is designed as a single FastAPI application that hosts the entire data extraction pipeline inside one deployable unit. It uses FastAPI for HTTP endpoints, BackgroundTasks for asynchronous work, SQLite for local persistence, and server-side templates for the dashboard.

## Components

- **FastAPI App:** Exposes crawler, extraction, NLP, and dashboard endpoints through one service.
- **BackgroundTasks:** Executes crawling and extraction jobs asynchronously without separate worker processes.
- **SQLite:** Stores crawled HTML, extracted text, analysis results, and metadata in a single file-based database.
- **NLP Stack:** Combines spaCy for entity recognition, VADER for sentiment analysis, and sumy for summarization.
- **Dashboard:** Rendered using Jinja2 templates inside the same application.
- **Containerization:** The whole monolith runs in a single Docker container.

## Internal Flow

The internal processing flow is simple and sequential, with all tasks handled in-process.

```text
[Client] --> [FastAPI App]
                  |
                  v
          +----------------+
          |  Request Router |
          +----------------+
                  |
          v
          +----------------+
          | BackgroundTasks|
          +----------------+
            /      |      \
           v       v       v
   [Crawler] [Extractor] [NLP/Analysis]
                  |
                  v
               [SQLite]
                  |
                  v
             [Jinja2 Dashboard]
```

## Summary

This architecture is easy to develop and deploy because there is only one service. It is best suited for early prototype validation and small-scale workloads where distributed complexity is not required.
