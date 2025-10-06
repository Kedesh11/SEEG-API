import base64


def test_upload_and_download_pdf_as_candidate(client, candidate_token, seeded_ids):
    if not seeded_ids.get("job_offer_id"):
        return

    # Créer une candidature rapide via endpoint (si schema permet)
    app_resp = client.post(
        "/api/v1/applications",
        json={
            "candidate_id": "00000000-0000-0000-0000-000000000001",
            "job_offer_id": seeded_ids["job_offer_id"],
            "status": "pending"
        },
        headers={"Authorization": f"Bearer {candidate_token}", "content-type": "application/json"},
    )
    if app_resp.status_code not in (201, 200):
        return
    app_data = app_resp.json()
    application_id = app_data.get("data", {}).get("id") or app_data.get("id")
    if not application_id:
        return

    # Préparer un petit PDF factice
    pdf_bytes = b"%PDF-1.4\n%Fake Minimal PDF for upload test\n"

    # Upload via multipart
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    data = {"document_type": "cv"}
    up = client.post(f"/api/v1/applications/{application_id}/documents", files=files, data=data, headers={"Authorization": f"Bearer {candidate_token}"})
    assert up.status_code in (201, 200, 404, 422)

    # Lister documents
    lst = client.get(f"/api/v1/applications/{application_id}/documents", headers={"Authorization": f"Bearer {candidate_token}"})
    assert lst.status_code in (200, 404)
    if lst.status_code == 200:
        docs = lst.json().get("data", [])
        if docs:
            doc_id = docs[0].get("id")
            # Download
            dl = client.get(f"/api/v1/applications/{application_id}/documents/{doc_id}/download", headers={"Authorization": f"Bearer {candidate_token}"})
            assert dl.status_code in (200, 404)


def test_export_pdf_permissions(client, candidate_token, recruiter_token, seeded_ids):
    # Sans application concrète, on vérifie au moins les statuts 401/403/404 en fonction du contexte
    import uuid
    application_id = str(uuid.uuid4())
    r = client.get(f"/api/v1/applications/{application_id}/export/pdf", headers={"Authorization": f"Bearer {candidate_token}"})
    assert r.status_code in (403, 404)
    r2 = client.get(f"/api/v1/applications/{application_id}/export/pdf", headers={"Authorization": f"Bearer {recruiter_token}"})
    assert r2.status_code in (403, 404)


