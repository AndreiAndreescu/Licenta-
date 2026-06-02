from contextlib import asynccontextmanager
import httpx
try:
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:
    Instrumentator = None
from fastapi import FastAPI
from webintel_common.messaging import get_redis
from .consumer import start_consumer
from .routes import router
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await get_redis(settings.REDIS_URL)
    app.state.http_client = httpx.AsyncClient()
    await start_consumer(app)
    try:
        yield
    finally:
        try:
            await app.state.http_client.aclose()
        except Exception:
            pass
        try:
            await app.state.redis.close()
        except Exception:
            pass


app = FastAPI(title=settings.SERVICE_NAME, lifespan=lifespan)
if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)
app.include_router(router, prefix="/api")
