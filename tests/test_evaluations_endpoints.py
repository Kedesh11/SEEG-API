def test_evaluations_endpoints_require_auth(client):
    r = client.get("/api/v1/evaluations")
    assert r.status_code in (401, 404)


