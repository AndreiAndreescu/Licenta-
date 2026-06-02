import pytest


@pytest.mark.anyio
async def test_get_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gateway"


@pytest.mark.anyio
async def test_request_id_header(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    # Check for X-Request-ID header in either case
    assert "x-request-id" in {k.lower() for k in response.headers.keys()}
