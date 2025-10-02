import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200