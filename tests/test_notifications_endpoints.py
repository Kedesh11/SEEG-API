def test_notifications_requires_auth(client):
    r = client.get("/api/v1/notifications")
    assert r.status_code in (401, 404)


