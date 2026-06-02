# WebIntel Monolith

This repository contains the monolithic implementation of WebIntel, a web data extraction and NLP analysis platform. It includes crawling, extraction, sentiment analysis, keyword extraction, and a Jinja2 dashboard in a single FastAPI application.

## Run Locally

1. Copy `.env.example` to `.env`
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
uvicorn app.main:app --reload
```

4. Open `http://localhost:8000`
