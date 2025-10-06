def test_interviews_list_requires_auth(client):
    r = client.get("/api/v1/interviews")
    assert r.status_code in (401, 404)


