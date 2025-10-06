def test_applications_list_requires_bearer(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 401


def test_applications_docs_list_requires_bearer(client):
    resp = client.get("/api/v1/applications/00000000-0000-0000-0000-0000000000AA/documents")
    assert resp.status_code == 401


