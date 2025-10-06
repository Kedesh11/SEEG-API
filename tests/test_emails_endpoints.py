
def test_emails_endpoints_maybe_present(client):
    resp = client.get("/api/v1/emails")
    assert resp.status_code in (200, 404)
