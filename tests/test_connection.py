"""
Tests de connexion pour l'API One HCM SEEG
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.main import app
from app.db.database import get_async_db
from app.models.user import User
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.core.config.config import settings

client = TestClient(app)

class TestDatabaseConnection:
    """Tests de connexion à la base de données"""
    
    @pytest.mark.asyncio
    @pytest.fixture(autouse=True)
    def setup_test_db(self, override_get_db):
        pass
    async def test_database_connection(self):
        """Test de la connexion à la base de données"""
        async for db in get_async_db():
            # Test simple de connexion
            result = await db.execute(text("SELECT 1"))
            assert result.scalar() == 1
            break
    
    @pytest.mark.asyncio
    @pytest.fixture(autouse=True)
    def setup_test_db(self, override_get_db):
        pass
    async def test_database_tables_exist(self):
        """Test que les tables principales existent"""
        async for db in get_async_db():
            # Vérifier que les tables principales existent
            tables_to_check = [
                "users", "job_offers", "applications", 
                "application_documents", "notifications", "evaluations"
            ]
            
            for table in tables_to_check:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                assert count is not None
                print(f"✅ Table {table} accessible - {count} enregistrements")
            break
    
    @pytest.mark.asyncio
    @pytest.fixture(autouse=True)
    def setup_test_db(self, override_get_db):
        pass
    async def test_database_migrations_applied(self):
        """Test que les migrations ont été appliquées"""
        async for db in get_async_db():
            # Vérifier que la table application_documents a les bons champs
            result = await db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'application_documents' 
                AND column_name = 'file_data'
            """))
            
            row = result.fetchone()
            assert row is not None
            assert row[1] == 'bytea'  # Type BYTEA pour les fichiers PDF
            print("✅ Migration PDF appliquée - champ file_data présent")
            break

class TestAPIConnection:
    """Tests de connexion à l'API"""
    
    def test_api_root_endpoint(self):
        """Test du endpoint racine de l'API"""
        response = client.get("/")
        
        assert response.status_code in [200, 401, 403]
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "API One HCM SEEG"
    
    def test_api_health_check(self):
        """Test du endpoint de santé de l'API"""
        response = client.get("/health")
        
        assert response.status_code in [200, 401, 403]
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert "pdf_storage" in data
    
    def test_api_info_endpoint(self):
        """Test du endpoint d'informations de l'API"""
        response = client.get("/info")
        
        assert response.status_code in [200, 401, 403]
        data = response.json()
        assert "app_name" in data
        assert "app_version" in data
        assert "features" in data
        assert "pdf_support" in data
        
        # Vérifier les fonctionnalités PDF
        pdf_support = data["pdf_support"]
        assert "allowed_types" in pdf_support
        assert "file_format" in pdf_support
        assert "storage" in pdf_support
    
    def test_api_documentation_endpoints(self):
        """Test des endpoints de documentation"""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code in [200, 401, 403]
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code in [200, 401, 403]
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code in [200, 401, 403]
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema

class TestEndpointConnectivity:
    """Tests de connectivité des endpoints"""
    
    def test_auth_endpoints(self):
        """Test des endpoints d'authentification"""
        endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/refresh"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Doit retourner 422 (validation error) ou 401, pas 404
            assert response.status_code in [401, 422, 400]
            print(f"✅ Endpoint {endpoint} accessible")
    
    def test_protected_endpoints(self):
        """Test des endpoints protégés"""
        endpoints = [
            "/api/v1/users/",
            "/api/v1/jobs/",
            "/api/v1/applications/",
            "/api/v1/evaluations/",
            "/api/v1/notifications/",
            "/api/v1/interviews/"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Doit retourner 401 (unauthorized), pas 404
            assert response.status_code in [401, 403]
            print(f"✅ Endpoint protégé {endpoint} accessible")
    
    def test_pdf_endpoints(self):
        """Test des endpoints PDF"""
        endpoints = [
            "/api/v1/applications/test-id/documents",
            "/api/v1/applications/test-id/documents/multiple"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Doit retourner 401 (unauthorized), pas 404
            assert response.status_code in [401, 403]
            print(f"✅ Endpoint PDF {endpoint} accessible")

class TestCORSConnection:
    """Tests de connexion CORS"""
    
    def test_cors_preflight(self):
        """Test des requêtes CORS preflight"""
        response = client.get("/api/v1/users/", headers={"Origin": "http://localhost:3000"})
        
        assert response.status_code in [200, 401, 403]
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_cors_headers(self):
        """Test des en-têtes CORS"""
        response = client.get("/")
        
        # Vérifier que les en-têtes CORS sont présents
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-credentials",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]
        
        for header in cors_headers:
            assert header in response.headers

class TestErrorHandling:
    """Tests de gestion des erreurs de connexion"""
    
    def test_404_handling(self):
        """Test de la gestion des erreurs 404"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"] == "Not Found"
    
    def test_405_method_not_allowed(self):
        """Test de la gestion des erreurs 405"""
        response = client.delete("/")
        
        assert response.status_code == 405
    
    def test_422_validation_error(self):
        """Test de la gestion des erreurs de validation"""
        response = client.post("/api/v1/auth/login", json={
            "email": "invalid-email",
            "password": "short"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

class TestPerformance:
    """Tests de performance de connexion"""
    
    def test_response_time(self):
        """Test du temps de réponse"""
        import time
        
        start_time = time.time()
        response = client.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code in [200, 401, 403]
        assert response_time < 1.0  # Moins d'1 seconde
        print(f"✅ Temps de réponse: {response_time:.3f}s")
    
    def test_concurrent_requests(self):
        """Test de requêtes concurrentes"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.get("/")
            end_time = time.time()
            results.append({
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })
        
        # Créer 10 threads pour faire des requêtes simultanées
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join()
        
        # Vérifier que toutes les requêtes ont réussi
        assert len(results) == 10
        for result in results:
            assert result["status_code"] == 200
            assert result["response_time"] < 2.0  # Moins de 2 secondes
        
        print(f"✅ {len(results)} requêtes concurrentes réussies")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
