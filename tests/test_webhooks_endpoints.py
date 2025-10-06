def test_webhooks_maybe_present(client):
    r = client.get("/api/v1/webhooks")
    assert r.status_code in (200, 404)


