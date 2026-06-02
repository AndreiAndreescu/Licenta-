import uuid
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse, RedirectResponse

from .config import settings
from .routes import router

logger = logging.getLogger(__name__)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:
    Instrumentator = None

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    try:
        yield
    finally:
        try:
            await app.state.http_client.aclose()
        except Exception:
            pass


app = FastAPI(title=settings.SERVICE_NAME, lifespan=lifespan)
if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.DASHBOARD_ORIGIN, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"request_id={request_id} method={request.method} path={request.url.path} status={response.status_code}")
    return response


# Rate limiter error handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "rate limit exceeded"})


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url=settings.DASHBOARD_ORIGIN)


app.state.limiter = limiter
app.include_router(router, prefix="/api")
