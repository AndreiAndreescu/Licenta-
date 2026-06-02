from locust import HttpUser, task, between
import random

QUERIES = [
    "artificial intelligence", "machine learning", "python programming",
    "web scraping", "distributed systems", "docker containers",
    "neural networks", "data science", "cloud computing", "microservices"
]

class MonolithUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    job_ids = []

    @task(3)
    def submit_job(self):
        query = random.choice(QUERIES)
        response = self.client.post("/api/jobs", json={
            "query": query,
            "seed_urls": [],
            "max_depth": 1,
            "max_pages": 5
        })
        if response.status_code == 202:
            data = response.json()
            MonolithUser.job_ids.append(data["id"])

    @task(5)
    def list_jobs(self):
        self.client.get("/api/jobs")

    @task(2)
    def get_job_results(self):
        if MonolithUser.job_ids:
            job_id = random.choice(MonolithUser.job_ids)
            self.client.get(f"/api/jobs/{job_id}/results")

    @task(4)
    def get_job_progress(self):
        if MonolithUser.job_ids:
            job_id = random.choice(MonolithUser.job_ids)
            self.client.get(f"/api/jobs/{job_id}")
