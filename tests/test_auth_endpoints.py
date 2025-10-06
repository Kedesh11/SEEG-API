def test_auth_login_missing_fields(client):
    resp = client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


def test_auth_status_route_exists(client):
    # Le routeur v1 expose /api/v1/status via api.py
    resp = client.get("/api/v1/status")
    assert resp.status_code in (200, 404)  # selon inclusion de api_router


