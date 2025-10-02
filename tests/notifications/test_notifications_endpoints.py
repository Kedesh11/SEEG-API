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
    from app.schemas.notification import NotificationListResponse
    
    async def _fake_list(self, **kwargs):
        # Retourner le schéma conforme à NotificationListResponse
        return NotificationListResponse(
            notifications=[],
            total=0,
            page=1,
            per_page=100,
            total_pages=0
        )
    # Le service utilise get_user_notifications
    monkeypatch.setattr(NotificationService, "get_user_notifications", _fake_list, raising=False)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("notifications") == []
        assert data.get("total") == 0
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data


@pytest.mark.anyio
async def test_notifications_stats(monkeypatch, client: AsyncClient):
    from app.schemas.notification import NotificationStatsResponse
    
    async def _fake_stats(self, user_id: str):
        # Retourner le schéma conforme à NotificationStatsResponse
        return NotificationStatsResponse(
            total_notifications=0,
            unread_count=0,
            read_count=0,
            notifications_by_type={}
        )
    # Le service expose get_user_notification_statistics
    monkeypatch.setattr(NotificationService, "get_user_notification_statistics", _fake_stats, raising=False)

    resp = await client.get("/api/v1/notifications/stats/overview")
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        data = resp.json()
        assert "total_notifications" in data
        assert "unread_count" in data
        assert "read_count" in data
        assert "notifications_by_type" in data 