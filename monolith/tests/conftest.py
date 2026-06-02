pytest_plugins = "pytest_asyncio"

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import database, main, service
from app.database import Base, get_db


@pytest.fixture(scope="function")
async def test_engine(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_engine, monkeypatch):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with async_session() as session:
            yield session

    async def noop_run_job_task(job_id: int) -> None:
        return

    monkeypatch.setattr(database, "AsyncSessionLocal", async_session)
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(service, "AsyncSessionLocal", async_session)
    monkeypatch.setattr(service, "run_job_task", noop_run_job_task)
    main.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main.app) as client_obj:
        yield client_obj

    main.app.dependency_overrides.pop(get_db, None)
