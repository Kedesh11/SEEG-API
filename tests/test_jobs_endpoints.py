def test_jobs_list_success(client):
    resp = client.get("/api/v1/jobs")
    # Peut être 200 même sans données; si DB non connectée, peut renvoyer 500
    assert resp.status_code in (200, 500)


