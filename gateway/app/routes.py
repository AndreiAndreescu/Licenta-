from fastapi import APIRouter, Request
from .proxy import forward
from .config import settings

router = APIRouter()


@router.post("/jobs")
async def post_jobs(request: Request):
    payload = await request.json()
    return await forward(request.app.state.http_client, "POST", f"{settings.SCHEDULER_URL}/api/jobs", json=payload, timeout=10.0)


@router.post("/verify")
async def post_verify(request: Request):
    payload = await request.json()
    return await forward(request.app.state.http_client, "POST", f"{settings.SCHEDULER_URL}/api/verify", json=payload, timeout=10.0)


@router.get("/jobs")
async def get_jobs(request: Request, skip: int = 0, limit: int = 20):
    return await forward(request.app.state.http_client, "GET", f"{settings.STORAGE_URL}/api/jobs", params={"skip": skip, "limit": limit}, timeout=10.0)


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, request: Request):
    return await forward(request.app.state.http_client, "GET", f"{settings.STORAGE_URL}/api/jobs/{job_id}", timeout=10.0)


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: int, request: Request):
    return await forward(request.app.state.http_client, "GET", f"{settings.STORAGE_URL}/api/jobs/{job_id}/results", timeout=10.0)


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: int, request: Request):
    return await forward(request.app.state.http_client, "GET", f"{settings.SCHEDULER_URL}/api/jobs/{job_id}/progress", timeout=10.0)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway", "version": "1.0.0"}
