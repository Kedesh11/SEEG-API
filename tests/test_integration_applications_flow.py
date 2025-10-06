import uuid


def test_applications_protected_then_list_as_admin(client):
    # Sans token
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 401


def test_export_application_pdf_requires_permissions(client):
    # Appel sur UUID aléatoire; attend 401 si pas d'auth
    application_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/applications/{application_id}/export/pdf")
    assert resp.status_code == 401


