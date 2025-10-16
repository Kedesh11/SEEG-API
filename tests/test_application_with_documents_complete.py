"""
Tests pour la route de création de candidature avec documents obligatoires
POST /api/v1/applications/ avec 3 documents (CV, lettre, diplôme)
"""
import pytest
import base64
from pathlib import Path
from httpx import AsyncClient
from datetime import datetime, date


# Charger le PDF de test
def get_test_pdf_base64() -> str:
    """Charge le PDF de test et le convertit en base64"""
    pdf_path = Path("app/data/cv/Sevan.pdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF de test introuvable : {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    return base64.b64encode(pdf_content).decode('utf-8')


@pytest.mark.asyncio
async def test_create_application_with_all_documents_success(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 1: Création de candidature avec les 3 documents obligatoires
    
    Scénario:
    - Candidat authentifié
    - 3 documents fournis (CV, lettre motivation, diplôme)
    - Tous les documents valides (PDF, < 10MB)
    
    Résultat attendu:
    - 201 Created
    - Candidature créée avec ID
    - Message indique "3 document(s) uploadé(s)"
    """
    # Préparer les données
    pdf_base64 = get_test_pdf_base64()
    
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "status": "pending",
        "reference_contacts": "M. Test (+241 01 02 03 04)",
        "has_been_manager": False,
        "ref_entreprise": "Entreprise Test",
        "ref_fullname": "Jean Dupont",
        "ref_mail": "jean.dupont@test.com",
        "ref_contact": "+241 01 02 03 04",
        "documents": [
            {
                "document_type": "cv",
                "file_name": "mon_cv.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "cover_letter",
                "file_name": "lettre_motivation.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "diplome",
                "file_name": "diplome.pdf",
                "file_data": pdf_base64
            }
        ]
    }
    
    # Appeler l'API
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    # Assertions
    assert response.status_code == 201, f"Erreur: {response.text}"
    
    data = response.json()
    assert data["success"] is True
    assert "3 document(s) uploadé(s)" in data["message"]
    assert data["data"]["id"] is not None
    assert data["data"]["candidate_id"] == str(test_user_candidate.id)
    assert data["data"]["job_offer_id"] == str(test_job_offer.id)
    assert data["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_application_missing_documents_error(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 2: Création de candidature SANS documents
    
    Scénario:
    - Candidat authentifié
    - Aucun document fourni
    
    Résultat attendu:
    - 422 Unprocessable Entity (validation Pydantic)
    - Message d'erreur indiquant que les documents sont obligatoires
    """
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "status": "pending",
        "documents": []  # Liste vide
    }
    
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    # Doit échouer car documents obligatoires
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_application_missing_one_document_type_error(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 3: Création de candidature avec seulement 2 documents (manque diplôme)
    
    Scénario:
    - Candidat authentifié
    - 2 documents fournis (CV + lettre) mais manque diplôme
    
    Résultat attendu:
    - 422 Unprocessable Entity
    - Message d'erreur : "Documents manquants : Diplôme"
    """
    pdf_base64 = get_test_pdf_base64()
    
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "status": "pending",
        "documents": [
            {
                "document_type": "cv",
                "file_name": "mon_cv.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "cover_letter",
                "file_name": "lettre_motivation.pdf",
                "file_data": pdf_base64
            }
            # Manque diplôme
        ]
    }
    
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    assert response.status_code == 422
    assert "Diplôme" in response.text


@pytest.mark.asyncio
async def test_create_application_with_extra_documents_success(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 4: Création de candidature avec plus de 3 documents (3 requis + certificats)
    
    Scénario:
    - Candidat authentifié
    - 4 documents fournis (CV + lettre + diplôme + certificats)
    
    Résultat attendu:
    - 201 Created
    - Tous les documents uploadés
    - Message indique "4 document(s) uploadé(s)"
    """
    pdf_base64 = get_test_pdf_base64()
    
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "status": "pending",
        "documents": [
            {
                "document_type": "cv",
                "file_name": "mon_cv.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "cover_letter",
                "file_name": "lettre_motivation.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "diplome",
                "file_name": "diplome.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "certificats",
                "file_name": "certificat_formation.pdf",
                "file_data": pdf_base64
            }
        ]
    }
    
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "4 document(s) uploadé(s)" in data["message"]


@pytest.mark.asyncio
async def test_create_application_invalid_pdf_error(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 5: Création de candidature avec un fichier non-PDF
    
    Scénario:
    - Candidat authentifié
    - 3 documents fournis mais l'un n'est pas un PDF valide
    
    Résultat attendu:
    - 201 Created (documents invalides ignorés)
    - Seulement 2 documents uploadés
    - Message indique "2 document(s) uploadé(s)"
    """
    pdf_base64 = get_test_pdf_base64()
    fake_pdf = base64.b64encode(b"This is not a PDF").decode('utf-8')
    
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "status": "pending",
        "documents": [
            {
                "document_type": "cv",
                "file_name": "mon_cv.pdf",
                "file_data": pdf_base64
            },
            {
                "document_type": "cover_letter",
                "file_name": "lettre_motivation.pdf",
                "file_data": fake_pdf  # Fichier invalide
            },
            {
                "document_type": "diplome",
                "file_name": "diplome.pdf",
                "file_data": pdf_base64
            }
        ]
    }
    
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    # La candidature est créée mais avec seulement les documents valides
    assert response.status_code == 201
    data = response.json()
    assert "2 document(s) uploadé(s)" in data["message"]


@pytest.mark.asyncio
async def test_get_application_documents(async_client: AsyncClient, test_user_candidate, test_application_with_docs):
    """
    Test 6: Récupération des documents d'une candidature
    
    Scénario:
    - Candidature existante avec documents
    - Candidat authentifié
    
    Résultat attendu:
    - 200 OK
    - Liste des documents avec métadonnées (sans file_data pour performance)
    """
    response = await async_client.get(
        f"/api/v1/applications/{test_application_with_docs.id}/documents",
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 3  # Au moins les 3 documents obligatoires
    
    # Vérifier que file_data n'est pas inclus (performance)
    for doc in data["data"]:
        assert "file_data" not in doc
        assert doc["document_type"] in ["cv", "cover_letter", "diplome", "certificats"]
        assert doc["file_name"].endswith(".pdf")


@pytest.mark.asyncio
async def test_download_application_document(async_client: AsyncClient, test_user_candidate, test_application_with_docs):
    """
    Test 7: Téléchargement d'un document spécifique
    
    Scénario:
    - Candidature existante avec documents
    - Candidat authentifié
    - ID de document valide
    
    Résultat attendu:
    - 200 OK
    - Contenu PDF retourné
    - Headers appropriés (Content-Type: application/pdf)
    """
    # Récupérer la liste des documents
    docs_response = await async_client.get(
        f"/api/v1/applications/{test_application_with_docs.id}/documents",
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    documents = docs_response.json()["data"]
    first_doc_id = documents[0]["id"]
    
    # Télécharger le document
    response = await async_client.get(
        f"/api/v1/applications/{test_application_with_docs.id}/documents/{first_doc_id}/download",
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0
    # Vérifier que c'est bien un PDF
    assert response.content.startswith(b'%PDF')


@pytest.mark.asyncio
async def test_create_application_unauthorized_error(async_client: AsyncClient, test_job_offer):
    """
    Test 8: Tentative de création sans authentification
    
    Scénario:
    - Aucun token fourni
    
    Résultat attendu:
    - 401 Unauthorized
    """
    pdf_base64 = get_test_pdf_base64()
    
    application_data = {
        "candidate_id": "00000000-0000-0000-0000-000000000001",
        "job_offer_id": str(test_job_offer.id),
        "documents": [
            {"document_type": "cv", "file_name": "cv.pdf", "file_data": pdf_base64},
            {"document_type": "cover_letter", "file_name": "lettre.pdf", "file_data": pdf_base64},
            {"document_type": "diplome", "file_name": "diplome.pdf", "file_data": pdf_base64}
        ]
    }
    
    response = await async_client.post(
        "/api/v1/applications/",
        json=application_data
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_duplicate_application_error(async_client: AsyncClient, test_user_candidate, test_job_offer):
    """
    Test 9: Tentative de création d'une candidature en double
    
    Scénario:
    - Candidat authentifié
    - Candidature déjà existante pour cette offre
    
    Résultat attendu:
    - 400 Bad Request
    - Message : "Une candidature existe déjà pour cette offre d'emploi"
    """
    pdf_base64 = get_test_pdf_base64()
    
    application_data = {
        "candidate_id": str(test_user_candidate.id),
        "job_offer_id": str(test_job_offer.id),
        "documents": [
            {"document_type": "cv", "file_name": "cv.pdf", "file_data": pdf_base64},
            {"document_type": "cover_letter", "file_name": "lettre.pdf", "file_data": pdf_base64},
            {"document_type": "diplome", "file_name": "diplome.pdf", "file_data": pdf_base64}
        ]
    }
    
    # Première création
    response1 = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    assert response1.status_code == 201
    
    # Tentative de duplication
    response2 = await async_client.post(
        "/api/v1/applications/",
        json=application_data,
        headers={"Authorization": f"Bearer {test_user_candidate.access_token}"}
    )
    
    assert response2.status_code == 400
    assert "existe déjà" in response2.text.lower()

