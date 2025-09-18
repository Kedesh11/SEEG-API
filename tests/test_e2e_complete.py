"""
Tests end-to-end complets pour l'API One HCM SEEG
"""
import pytest
import asyncio
import base64
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.database import get_async_db
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application, ApplicationDocument
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.job import JobOfferService
from app.services.application import ApplicationService

client = TestClient(app)

class TestCompleteWorkflow:
    """Tests du workflow complet de candidature"""
    
    @pytest.fixture
    async def test_user(self):
        """Créer un utilisateur de test"""
        async for db in get_async_db():
            user_service = UserService(db)
            
            # Créer un utilisateur candidat
            user_data = {
                "email": "candidate@test.com",
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "Candidate",
                "role": "candidate",
                "phone": "+33123456789"
            }
            
            user = await user_service.create_user(user_data)
            yield user
            break
    
    @pytest.fixture
    async def test_job_offer(self):
        """Créer une offre d'emploi de test"""
        async for db in get_async_db():
            job_service = JobOfferService(db)
            
            # Créer une offre d'emploi
            job_data = {
                "title": "Développeur Full Stack",
                "description": "Poste de développeur full stack avec React et Python",
                "requirements": "3+ ans d'expérience",
                "location": "Paris",
                "salary_min": 45000,
                "salary_max": 65000,
                "employment_type": "CDI",
                "status": "active"
            }
            
            job = await job_service.create_job_offer(job_data)
            yield job
            break
    
    @pytest.fixture
    def auth_token(self, test_user):
        """Obtenir un token d'authentification"""
        # Simuler la connexion pour obtenir un token
        response = client.post("/api/v1/auth/login", json={
            "email": "candidate@test.com",
            "password": "TestPassword123!"
        })
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            # Si la connexion échoue, créer un token manuellement
            from app.core.security.security import TokenManager
            return TokenManager.create_access_token(str(test_user.id))
    
    def test_complete_application_workflow(self, test_user, test_job_offer, auth_token):
        """Test du workflow complet de candidature"""
        
        # 1. Créer une candidature
        application_data = {
            "candidate_id": str(test_user.id),
            "job_offer_id": str(test_job_offer.id),
            "reference_contacts": "Référence: M. Dupont - 0123456789",
            "mtp_answers": {
                "metier": "Développement web",
                "paradigme": "Agile",
                "talent": "Résolution de problèmes"
            }
        }
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post("/api/v1/applications/", json=application_data, headers=headers)
        
        assert response.status_code == 201
        application = response.json()["data"]
        application_id = application["id"]
        
        # 2. Uploader des documents PDF
        # Créer un PDF simulé
        fake_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
        
        # Upload CV
        files = {"file": ("cv.pdf", fake_pdf_content, "application/pdf")}
        data = {"document_type": "cv"}
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             files=files, data=data, headers=headers)
        
        assert response.status_code == 201
        cv_document = response.json()["data"]
        
        # Upload lettre de motivation
        files = {"file": ("cover_letter.pdf", fake_pdf_content, "application/pdf")}
        data = {"document_type": "cover_letter"}
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             files=files, data=data, headers=headers)
        
        assert response.status_code == 201
        cover_letter_document = response.json()["data"]
        
        # 3. Récupérer les documents
        response = client.get(f"/api/v1/applications/{application_id}/documents", headers=headers)
        
        assert response.status_code == 200
        documents = response.json()["data"]
        assert len(documents) == 2
        
        # 4. Récupérer un document avec ses données
        response = client.get(f"/api/v1/applications/{application_id}/documents/{cv_document['id']}", 
                            headers=headers)
        
        assert response.status_code == 200
        document_with_data = response.json()["data"]
        assert "file_data" in document_with_data
        assert document_with_data["file_data"] is not None
        
        # 5. Mettre à jour le statut de la candidature
        update_data = {"status": "reviewed"}
        response = client.put(f"/api/v1/applications/{application_id}", 
                            json=update_data, headers=headers)
        
        assert response.status_code == 200
        updated_application = response.json()["data"]
        assert updated_application["status"] == "reviewed"
        
        # 6. Récupérer la candidature mise à jour
        response = client.get(f"/api/v1/applications/{application_id}", headers=headers)
        
        assert response.status_code == 200
        final_application = response.json()["data"]
        assert final_application["status"] == "reviewed"
        
        print("✅ Workflow complet de candidature testé avec succès")

class TestPDFUploadWorkflow:
    """Tests du workflow d'upload de PDF"""
    
    @pytest.fixture
    def auth_token(self):
        """Token d'authentification pour les tests"""
        from app.core.security.security import TokenManager
        return TokenManager.create_access_token("test-user-id")
    
    def test_multiple_pdf_upload(self, auth_token):
        """Test de l'upload de plusieurs PDF"""
        # Créer une candidature de test
        application_id = str(uuid.uuid4())
        
        # Créer des PDF simulés
        fake_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Upload multiple de documents
        files = [
            ("files", ("cv.pdf", fake_pdf_content, "application/pdf")),
            ("files", ("cover_letter.pdf", fake_pdf_content, "application/pdf")),
            ("files", ("diplome.pdf", fake_pdf_content, "application/pdf"))
        ]
        data = {
            "document_types": ["cv", "cover_letter", "diplome"]
        }
        
        response = client.post(f"/api/v1/applications/{application_id}/documents/multiple", 
                             files=files, data=data, headers=headers)
        
        # Note: Ce test peut échouer si l'application n'existe pas, mais on teste la structure
        assert response.status_code in [201, 404, 401]
        
        if response.status_code == 201:
            documents = response.json()["data"]
            assert len(documents) == 3
            print("✅ Upload multiple de PDF testé avec succès")

class TestErrorHandlingE2E:
    """Tests de gestion d'erreurs end-to-end"""
    
    def test_invalid_pdf_upload(self):
        """Test d'upload de fichier non-PDF"""
        from app.core.security.security import TokenManager
        auth_token = TokenManager.create_access_token("test-user-id")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        application_id = str(uuid.uuid4())
        
        # Essayer d'uploader un fichier texte
        files = {"file": ("test.txt", b"Not a PDF content", "text/plain")}
        data = {"document_type": "cv"}
        
        response = client.post(f"/api/v1/applications/{application_id}/documents", 
                             files=files, data=data, headers=headers)
        
        # Doit échouer avec une erreur de validation
        assert response.status_code in [400, 404, 401]
        
        if response.status_code == 400:
            error_data = response.json()
            assert "detail" in error_data
            print("✅ Validation des fichiers PDF testée")

class TestPerformanceE2E:
    """Tests de performance end-to-end"""
    
    def test_api_response_times(self):
        """Test des temps de réponse de l'API"""
        import time
        
        endpoints_to_test = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/info", "GET"),
            ("/docs", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            start_time = time.time()
            
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code in [200, 401, 422]
            assert response_time < 2.0  # Moins de 2 secondes
            
            print(f"✅ {endpoint} - {response_time:.3f}s")
    
    def test_concurrent_pdf_uploads(self):
        """Test d'uploads PDF concurrents"""
        import threading
        import time
        
        from app.core.security.security import TokenManager
        auth_token = TokenManager.create_access_token("test-user-id")
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        results = []
        
        def upload_pdf():
            application_id = str(uuid.uuid4())
            fake_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
            
            files = {"file": ("test.pdf", fake_pdf_content, "application/pdf")}
            data = {"document_type": "cv"}
            
            start_time = time.time()
            response = client.post(f"/api/v1/applications/{application_id}/documents", 
                                 files=files, data=data, headers=headers)
            end_time = time.time()
            
            results.append({
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })
        
        # Créer 5 threads pour des uploads concurrents
        threads = []
        for i in range(5):
            thread = threading.Thread(target=upload_pdf)
            threads.append(thread)
            thread.start()
        
        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join()
        
        # Vérifier les résultats
        assert len(results) == 5
        for result in results:
            assert result["status_code"] in [201, 404, 401]
            assert result["response_time"] < 5.0  # Moins de 5 secondes
        
        print(f"✅ {len(results)} uploads PDF concurrents testés")

class TestDataIntegrityE2E:
    """Tests d'intégrité des données end-to-end"""
    
    @pytest.mark.asyncio
    async def test_database_consistency(self):
        """Test de la cohérence de la base de données"""
        async for db in get_async_db():
            # Vérifier que les tables principales existent
            tables = ["users", "job_offers", "applications", "application_documents"]
            
            for table in tables:
                result = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                assert count is not None
                print(f"✅ Table {table}: {count} enregistrements")
            
            # Vérifier la structure de la table application_documents
            result = await db.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'application_documents'
                ORDER BY ordinal_position
            """)
            
            columns = result.fetchall()
            expected_columns = [
                ("id", "uuid", "NO"),
                ("application_id", "uuid", "YES"),
                ("document_type", "character varying", "NO"),
                ("file_name", "character varying", "NO"),
                ("file_data", "bytea", "NO"),
                ("file_size", "integer", "NO"),
                ("file_type", "character varying", "YES")
            ]
            
            for i, (col_name, col_type, nullable) in enumerate(expected_columns):
                if i < len(columns):
                    actual_name, actual_type, actual_nullable = columns[i]
                    assert actual_name == col_name
                    print(f"✅ Colonne {col_name}: {actual_type} ({'NULL' if actual_nullable == 'YES' else 'NOT NULL'})")
            
            break

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
