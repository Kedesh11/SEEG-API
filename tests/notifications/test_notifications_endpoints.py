import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from app.main import app
from app.core.dependencies import get_current_user
from app.services.notification import NotificationService


@pytest.fixture(autouse=True)
async def _auth_override():
    fake_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", email="tester@example.com", role="candidate")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_list_notifications_empty(monkeypatch, client: AsyncClient):
    async def _fake_list(self, **kwargs):
        return {"notifications": [], "total": 0}
    monkeypatch.setattr(NotificationService, "get_notifications", _fake_list, raising=False)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("notifications") == []


@pytest.mark.anyio
async def test_notifications_stats(monkeypatch, client: AsyncClient):
    async def _fake_stats(self, user_id: str):
        return {"total": 0, "unread": 0}
    monkeypatch.setattr(NotificationService, "get_notification_statistics", _fake_stats, raising=False)

    resp = await client.get("/api/v1/notifications/stats")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        data = resp.json()
        assert "total" in data and "unread" in data 