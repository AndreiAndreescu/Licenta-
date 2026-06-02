import pytest


def test_create_job_returns_202(client):
    payload = {
        "query": "https://example.com",
        "seed_urls": ["https://example.com"],
        "max_depth": 2,
        "max_pages": 5,
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"


def test_create_job_invalid_payload_returns_422(client):
    payload = {
        "query": "ok",
        "seed_urls": [],
        "max_depth": 2,
        "max_pages": 5,
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422


def test_list_jobs_returns_list(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_job_not_found_returns_404(client):
    response = client.get("/api/jobs/9999")
    assert response.status_code == 404


def test_get_job_progress_returns_shape(client):
    create_resp = client.post(
        "/api/jobs",
        json={
            "query": "https://example.com",
            "seed_urls": ["https://example.com"],
            "max_depth": 1,
            "max_pages": 3,
        },
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]
    progress_resp = client.get(f"/api/jobs/{job_id}/progress")
    assert progress_resp.status_code == 200
    data = progress_resp.json()
    assert data["job_id"] == job_id
    assert "status" in data
    assert "pages_crawled" in data
    assert "pages_analyzed" in data
    assert "progress_pct" in data
