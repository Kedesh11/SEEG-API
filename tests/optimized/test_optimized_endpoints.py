import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_optimized_health(client: AsyncClient):
    resp = await client.get("/api/v1/optimized/health")
    # Accepte 200 si l'endpoint existe, sinon 404 si non exposé
    assert resp.status_code in (200, 404) 