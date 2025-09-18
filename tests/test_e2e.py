"""
Tests end-to-end pour l'API One HCM SEEG
"""
import pytest
import asyncio
import base64
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.database import get_async_db
from app.models.user import User
from app.models.application import Application, ApplicationDocument
from app.models.job_offer import JobOffer
from app.core.config.config import settings

client = TestClient(app)

class TestCompleteUserJourney:
    """Tests du parcours complet utilisateur"""
    
    def test_candidate_registration_and_application(self):
        """Test complet : inscription candidat + candidature"""
        # 1. Inscription d'un candidat
        candidate_data = {
            "email": "candidate.e2e@example.com",
            "password": "TestPassword123!",
            "first_name": "Jean",
            "last_name": "Dupont",
            "role": "candidate",
            "phone": "+237123456789"
        }
        
        response = client.post("/api/v1/auth/signup", json=candidate_data)
        assert response.status_code == 201
        candidate = response.json()
        candidate_id = candidate["id"]
        
        # 2. Connexion du candidat
        login_data = {
            "email": candidate_data["email"],
            "password": candidate_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        login_response = response.json()
        access_token = login_response["access_token"]
        
        # 3. Création d'une offre d'emploi (par un recruteur)
        # D'abord, créer un recruteur
        recruiter_data = {
            "email": "recruiter.e2e@example.com",
            "password": "TestPassword123!",
            "first_name": "Marie",
            "last_name": "Martin",
            "role": "recruiter"
        }
        
        response = client.post("/api/v1/auth/signup", json=recruiter_data)
        assert response.status_code == 201
        recruiter = response.json()
        
        # Connexion du recruteur
        recruiter_login = {
            "email": recruiter_data["email"],
            "password": recruiter_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=recruiter_login)
        assert response.status_code == 200
        recruiter_token = response.json()["access_token"]
        
        # Création de l'offre d'emploi
        job_data = {
            "title": "Développeur Full Stack",
            "description": "Développement d'applications web modernes",
            "requirements": "Python, React, PostgreSQL",
            "location": "Douala, Cameroun",
            "salary_min": 500000,
            "salary_max": 800000,
            "employment_type": "CDI",
            "experience_level": "intermediate",
            "status": "active"
        }
        
        headers = {"Authorization": f"Bearer {recruiter_token}"}
        response = client.post("/api/v1/jobs/", json=job_data, headers=headers)
        assert response.status_code == 201
        job = response.json()
        job_id = job["id"]
        
        # 4. Candidature du candidat
        application_data = {
            "job_offer_id": job_id,
            "status": "pending",
            "reference_contacts": "Référence 1: +237123456789",
            "availability_start": "2024-02-01T00:00:00Z"
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/v1/applications/", json=application_data, headers=headers)
        assert response.status_code == 201
        application = response.json()
        application_id = application["id"]
        
        # 5. Upload de documents PDF
        # Créer un fichier PDF simulé
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Upload du CV
        cv_data = {
            "document_type": "cv",
            "file_name": "cv_jean_dupont.pdf",
            "file_data": pdf_base64,
            "file_size": len(pdf_content),
            "file_type": "application/pdf"
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             json=cv_data, headers=headers)
        assert response.status_code == 201
        cv_document = response.json()
        
        # Upload de la lettre de motivation
        cover_letter_data = {
            "document_type": "cover_letter",
            "file_name": "lettre_motivation_jean.pdf",
            "file_data": pdf_base64,
            "file_size": len(pdf_content),
            "file_type": "application/pdf"
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             json=cover_letter_data, headers=headers)
        assert response.status_code == 201
        cover_letter_document = response.json()
        
        # 6. Vérification des documents uploadés
        response = client.get(f"/api/v1/applications/{application_id}/documents", headers=headers)
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) == 2
        
        # 7. Récupération d'un document spécifique
        response = client.get(f"/api/v1/applications/{application_id}/documents/{cv_document['id']}", 
                            headers=headers)
        assert response.status_code == 200
        retrieved_cv = response.json()
        assert retrieved_cv["document_type"] == "cv"
        assert retrieved_cv["file_name"] == "cv_jean_dupont.pdf"
        
        # 8. Évaluation par le recruteur
        evaluation_data = {
            "application_id": application_id,
            "evaluator_id": recruiter["id"],
            "protocol": "protocol1",
            "scores": {
                "experience": 8,
                "skills": 7,
                "motivation": 9,
                "communication": 8
            },
            "comments": "Excellent candidat, très motivé",
            "recommendation": "accepted"
        }
        
        response = client.post("/api/v1/evaluations/", json=evaluation_data, headers=headers)
        assert response.status_code == 201
        evaluation = response.json()
        
        # 9. Mise à jour du statut de candidature
        update_data = {"status": "accepted"}
        response = client.patch(f"/api/v1/applications/{application_id}", 
                              json=update_data, headers=headers)
        assert response.status_code == 200
        updated_application = response.json()
        assert updated_application["status"] == "accepted"
        
        print("✅ Parcours complet candidat réussi")
        print(f"   - Candidat: {candidate['email']}")
        print(f"   - Offre: {job['title']}")
        print(f"   - Candidature: {application_id}")
        print(f"   - Documents: {len(documents)} uploadés")
        print(f"   - Évaluation: {evaluation['recommendation']}")

class TestPDFDocumentWorkflow:
    """Tests du workflow complet des documents PDF"""
    
    def test_multiple_pdf_upload(self):
        """Test d'upload multiple de documents PDF"""
        # Créer un candidat et une candidature
        candidate_data = {
            "email": "pdf.test@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "PDF",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/signup", json=candidate_data)
        assert response.status_code == 201
        candidate = response.json()
        
        # Connexion
        login_data = {
            "email": candidate_data["email"],
            "password": candidate_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Créer une offre d'emploi
        job_data = {
            "title": "Test PDF Job",
            "description": "Test pour documents PDF",
            "requirements": "Test",
            "location": "Test",
            "salary_min": 100000,
            "salary_max": 200000,
            "employment_type": "CDI",
            "experience_level": "junior",
            "status": "active"
        }
        
        response = client.post("/api/v1/jobs/", json=job_data, headers=headers)
        assert response.status_code == 201
        job = response.json()
        
        # Créer une candidature
        application_data = {
            "job_offer_id": job["id"],
            "status": "pending"
        }
        
        response = client.post("/api/v1/applications/", json=application_data, headers=headers)
        assert response.status_code == 201
        application = response.json()
        application_id = application["id"]
        
        # Créer des fichiers PDF simulés
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Upload multiple de documents
        multiple_docs_data = {
            "files": [
                {
                    "document_type": "cv",
                    "file_name": "cv_test.pdf",
                    "file_data": pdf_base64,
                    "file_size": len(pdf_content),
                    "file_type": "application/pdf"
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre_test.pdf",
                    "file_data": pdf_base64,
                    "file_size": len(pdf_content),
                    "file_type": "application/pdf"
                },
                {
                    "document_type": "diplome",
                    "file_name": "diplome_test.pdf",
                    "file_data": pdf_base64,
                    "file_size": len(pdf_content),
                    "file_type": "application/pdf"
                },
                {
                    "document_type": "certificats",
                    "file_name": "certificats_test.pdf",
                    "file_data": pdf_base64,
                    "file_size": len(pdf_content),
                    "file_type": "application/pdf"
                }
            ]
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents/multiple", 
                             json=multiple_docs_data, headers=headers)
        assert response.status_code == 201
        uploaded_docs = response.json()
        assert len(uploaded_docs) == 4
        
        # Vérifier que tous les documents sont bien uploadés
        response = client.get(f"/api/v1/applications/{application_id}/documents", headers=headers)
        assert response.status_code == 200
        all_docs = response.json()
        assert len(all_docs) == 4
        
        # Vérifier les types de documents
        doc_types = [doc["document_type"] for doc in all_docs]
        assert "cv" in doc_types
        assert "cover_letter" in doc_types
        assert "diplome" in doc_types
        assert "certificats" in doc_types
        
        print("✅ Upload multiple de documents PDF réussi")
        print(f"   - {len(all_docs)} documents uploadés")
        print(f"   - Types: {', '.join(doc_types)}")

class TestErrorHandlingE2E:
    """Tests de gestion d'erreurs end-to-end"""
    
    def test_invalid_pdf_upload(self):
        """Test d'upload de fichier non-PDF"""
        # Créer un candidat
        candidate_data = {
            "email": "error.test@example.com",
            "password": "TestPassword123!",
            "first_name": "Error",
            "last_name": "Test",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/signup", json=candidate_data)
        assert response.status_code == 201
        candidate = response.json()
        
        # Connexion
        login_data = {
            "email": candidate_data["email"],
            "password": candidate_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Créer une candidature
        job_data = {
            "title": "Error Test Job",
            "description": "Test d'erreurs",
            "requirements": "Test",
            "location": "Test",
            "salary_min": 100000,
            "salary_max": 200000,
            "employment_type": "CDI",
            "experience_level": "junior",
            "status": "active"
        }
        
        response = client.post("/api/v1/jobs/", json=job_data, headers=headers)
        assert response.status_code == 201
        job = response.json()
        
        application_data = {
            "job_offer_id": job["id"],
            "status": "pending"
        }
        
        response = client.post("/api/v1/applications/", json=application_data, headers=headers)
        assert response.status_code == 201
        application = response.json()
        application_id = application["id"]
        
        # Tentative d'upload d'un fichier non-PDF
        invalid_content = b"This is not a PDF file"
        invalid_base64 = base64.b64encode(invalid_content).decode('utf-8')
        
        invalid_doc_data = {
            "document_type": "cv",
            "file_name": "not_a_pdf.txt",
            "file_data": invalid_base64,
            "file_size": len(invalid_content),
            "file_type": "text/plain"
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             json=invalid_doc_data, headers=headers)
        assert response.status_code == 422  # Validation error
        
        # Tentative d'upload avec un magic number invalide
        fake_pdf_data = {
            "document_type": "cv",
            "file_name": "fake.pdf",
            "file_data": invalid_base64,
            "file_size": len(invalid_content),
            "file_type": "application/pdf"
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             json=fake_pdf_data, headers=headers)
        assert response.status_code == 422  # Validation error
        
        print("✅ Gestion d'erreurs PDF fonctionnelle")

class TestPerformanceE2E:
    """Tests de performance end-to-end"""
    
    def test_large_pdf_upload(self):
        """Test d'upload d'un PDF volumineux"""
        # Créer un candidat
        candidate_data = {
            "email": "performance.test@example.com",
            "password": "TestPassword123!",
            "first_name": "Performance",
            "last_name": "Test",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/signup", json=candidate_data)
        assert response.status_code == 201
        candidate = response.json()
        
        # Connexion
        login_data = {
            "email": candidate_data["email"],
            "password": candidate_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Créer une candidature
        job_data = {
            "title": "Performance Test Job",
            "description": "Test de performance",
            "requirements": "Test",
            "location": "Test",
            "salary_min": 100000,
            "salary_max": 200000,
            "employment_type": "CDI",
            "experience_level": "junior",
            "status": "active"
        }
        
        response = client.post("/api/v1/jobs/", json=job_data, headers=headers)
        assert response.status_code == 201
        job = response.json()
        
        application_data = {
            "job_offer_id": job["id"],
            "status": "pending"
        }
        
        response = client.post("/api/v1/applications/", json=application_data, headers=headers)
        assert response.status_code == 201
        application = response.json()
        application_id = application["id"]
        
        # Créer un PDF volumineux (1MB)
        large_pdf_content = b"%PDF-1.4\n" + b"x" * (1024 * 1024)  # 1MB
        large_pdf_base64 = base64.b64encode(large_pdf_content).decode('utf-8')
        
        import time
        start_time = time.time()
        
        large_doc_data = {
            "document_type": "cv",
            "file_name": "large_cv.pdf",
            "file_data": large_pdf_base64,
            "file_size": len(large_pdf_content),
            "file_type": "application/pdf"
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             json=large_doc_data, headers=headers)
        
        end_time = time.time()
        upload_time = end_time - start_time
        
        assert response.status_code == 201
        assert upload_time < 10.0  # Moins de 10 secondes
        
        print(f"✅ Upload de PDF volumineux réussi en {upload_time:.2f}s")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
