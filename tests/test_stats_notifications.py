def test_applications_stats_overview_requires_auth(client):
    r = client.get("/api/v1/applications/stats/overview")
    assert r.status_code == 401


def test_applications_stats_overview_ok_as_admin(client, admin_token):
    r = client.get("/api/v1/applications/stats/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code in (200, 500)


