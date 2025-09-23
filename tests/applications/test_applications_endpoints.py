import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from app.main import app
from app.core.dependencies import get_current_user
from app.services.application import ApplicationService


@pytest.fixture(autouse=True)
async def _auth_override():
    fake_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", email="tester@example.com", role="candidate")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_list_applications_empty(monkeypatch, client: AsyncClient):
    async def _fake_get(self, **kwargs):
        return [], 0
    monkeypatch.setattr(ApplicationService, "get_applications", _fake_get, raising=False)

    resp = await client.get("/api/v1/applications/")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("data") == []
    assert data.get("total") == 0


@pytest.mark.anyio
async def test_get_application_draft(monkeypatch, client: AsyncClient):
    async def _fake_get_draft(self, application_id: str, user_id: str):
        return {"form_data": {"step": 1}, "ui_state": {}}
    monkeypatch.setattr(ApplicationService, "get_application_draft", _fake_get_draft, raising=False)

    resp = await client.get("/api/v1/applications/00000000-0000-0000-0000-0000000000AA/draft")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True 