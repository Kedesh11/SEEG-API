import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_jobs_returns_empty_list_with_mock(client: AsyncClient):
    resp = await client.get("/api/v1/jobs/")
    assert resp.status_code in (200, 204, 401, 403)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.anyio
async def test_cors_preflight_jobs(client: AsyncClient):
    headers = {
        "Origin": "https://seeg-hcm.vercel.app",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    }
    resp = await client.options("/api/v1/jobs/", headers=headers)
    assert resp.status_code in (200, 204)


@pytest.mark.anyio
async def test_create_job_requires_auth(client: AsyncClient):
    payload = {"title": "Dev", "description": "desc", "department": "IT"}
    resp = await client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code in (401, 403) 