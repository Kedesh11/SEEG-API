import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from app.main import app
from app.core.security.security import get_current_user
from app.services.interview import InterviewService


@pytest.fixture(autouse=True)
async def _auth_override():
    fake_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", email="tester@example.com", role="recruiter")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_list_slots_empty(monkeypatch, client: AsyncClient):
    async def _fake_list(self, **kwargs):
        return {"slots": [], "total": 0, "page": 1, "per_page": 100, "total_pages": 0}
    monkeypatch.setattr(InterviewService, "get_interview_slots", _fake_list, raising=False)

    resp = await client.get("/api/v1/interviews/slots")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("slots") == []
    assert data.get("total") == 0 