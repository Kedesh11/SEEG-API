import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from app.main import app
from app.core.dependencies import get_current_user
from app.services.evaluation import EvaluationService


@pytest.fixture(autouse=True)
async def _auth_override():
    fake_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", email="tester@example.com", role="recruiter")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_protocol1_list_by_application(monkeypatch, client: AsyncClient):
    async def _fake_list(self, application_id: str):
        return []
    monkeypatch.setattr(EvaluationService, "get_protocol1_evaluations_by_application", _fake_list, raising=False)

    resp = await client.get("/api/v1/evaluations/protocol1/application/00000000-0000-0000-0000-0000000000AA")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_protocol2_stats(monkeypatch, client: AsyncClient):
    async def _fake_stats(self):
        return {"protocol1": {"total_evaluations": 0, "average_score": 0}, "protocol2": {"total_evaluations": 0, "average_score": 0}}
    monkeypatch.setattr(EvaluationService, "get_evaluation_statistics", _fake_stats, raising=False)

    resp = await client.get("/api/v1/evaluations/stats/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "protocol1" in data and "protocol2" in data 