import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_list_users_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/users/")
    assert resp.status_code in (401, 403) 