import uuid


def test_export_application_pdf_downloads_pdf(client, candidate_token, seeded_ids):
    # Préconditions: un job_offer_id seedé est requis
    job_offer_id = seeded_ids.get("job_offer_id")
    if not job_offer_id:
        # Si l'environnement de test n'a pas de seed, on sort proprement
        return

    # 1) Créer une candidature minimale pour le candidat seedé
    create_resp = client.post(
        "/api/v1/applications",
        json={
            "candidate_id": "00000000-0000-0000-0000-000000000001",
            "job_offer_id": job_offer_id,
            "status": "pending",
        },
        headers={
            "Authorization": f"Bearer {candidate_token}",
            "content-type": "application/json",
        },
    )

    # Certains environnements renvoient 201/200, sinon on ne peut pas poursuivre
    assert create_resp.status_code in (200, 201), f"Creation failed: {create_resp.status_code} {create_resp.text}"
    app_json = create_resp.json()
    application_id = app_json.get("data", {}).get("id") or app_json.get("id")
    assert application_id, "Application ID non récupéré"

    # 2) Appeler l'export PDF
    resp = client.get(
        f"/api/v1/applications/{application_id}/export/pdf",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    # 3) Vérifications minimales
    assert resp.status_code == 200, f"Export PDF failed: {resp.status_code} {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/pdf"), "Content-Type non PDF"
    # Lire quelques octets pour vérifier l'en-tête PDF
    chunk = next(resp.iter_bytes(), b"") if hasattr(resp, "iter_bytes") else resp.content[:4]
    assert chunk.startswith(b"%PDF"), "Le flux retourné ne semble pas être un PDF"


