"""
Fixtures pour les candidatures
Fournit des données de test pour applications et documents
"""
import pytest
import base64
from pathlib import Path
from typing import Dict, Any, List, Callable


@pytest.fixture
def test_pdf_base64() -> str:
    """Charge le PDF de test et retourne le contenu encodé en base64"""
    pdf_path = Path("app/data/cv/Sevan.pdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF de test introuvable: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    return base64.b64encode(pdf_content).decode('utf-8')


@pytest.fixture
def valid_application_data_with_documents(test_pdf_base64: str) -> Callable:
    """
    Factory fixture pour créer des données de candidature valides avec documents
    
    Usage:
        data = valid_application_data_with_documents(candidate_id, job_offer_id)
    """
    def _create(candidate_id: str, job_offer_id: str) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "status": "pending",
            "reference_contacts": "M. Reference (+241 01 02 03 04)",
            "ref_entreprise": "Entreprise Test",
            "ref_fullname": "Jean Dupont",
            "ref_mail": "jean.dupont@test.com",
            "ref_contact": "+241 01 02 03 04",
            "documents": [
                {
                    "document_type": "cv",
                    "file_name": "mon_cv.pdf",
                    "file_data": test_pdf_base64
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre_motivation.pdf",
                    "file_data": test_pdf_base64
                },
                {
                    "document_type": "diplome",
                    "file_name": "diplome.pdf",
                    "file_data": test_pdf_base64
                }
            ]
        }
    
    return _create


@pytest.fixture
def invalid_application_missing_documents() -> Callable:
    """Factory pour candidature sans documents (invalide)"""
    def _create(candidate_id: str, job_offer_id: str) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "documents": []  # Manquants !
        }
    
    return _create


@pytest.fixture
def invalid_application_missing_one_document(test_pdf_base64: str) -> Callable:
    """Factory pour candidature avec seulement 2 documents (manque diplôme)"""
    def _create(candidate_id: str, job_offer_id: str) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "documents": [
                {
                    "document_type": "cv",
                    "file_name": "cv.pdf",
                    "file_data": test_pdf_base64
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre.pdf",
                    "file_data": test_pdf_base64
                }
                # Manque diplôme
            ]
        }
    
    return _create


@pytest.fixture
def valid_application_with_extra_documents(test_pdf_base64: str) -> Callable:
    """Factory pour candidature avec plus de 3 documents"""
    def _create(candidate_id: str, job_offer_id: str) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "documents": [
                {"document_type": "cv", "file_name": "cv.pdf", "file_data": test_pdf_base64},
                {"document_type": "cover_letter", "file_name": "lettre.pdf", "file_data": test_pdf_base64},
                {"document_type": "diplome", "file_name": "diplome.pdf", "file_data": test_pdf_base64},
                {"document_type": "certificats", "file_name": "certificat.pdf", "file_data": test_pdf_base64}
            ]
        }
    
    return _create

