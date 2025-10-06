def test_users_me_requires_bearer(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


