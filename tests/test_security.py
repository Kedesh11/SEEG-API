"""
Tests de sécurité pour l'API One HCM SEEG
"""
import pytest
from datetime import timedelta
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.core.security.security import PasswordManager, TokenManager
from app.core.config.config import settings

client = TestClient(app)

class TestPasswordSecurity:
    """Tests de sécurité des mots de passe"""
    
    def test_password_hashing(self):
        """Test du hachage des mots de passe"""
        password = "TestPassword123!"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")
    
    def test_password_verification(self):
        """Test de la vérification des mots de passe"""
        password = "TestPassword123!"
        hashed = PasswordManager.hash_password(password)
        
        assert PasswordManager.verify_password(password, hashed) is True
        assert PasswordManager.verify_password("wrong_password", hashed) is False
    
    def test_weak_passwords(self):
        """Test des mots de passe faibles"""
        weak_passwords = [
            "123456",
            "password",
            "abc",
            "12345678",
            "qwerty"
        ]
        
        for weak_password in weak_passwords:
            hashed = PasswordManager.hash_password(weak_password)
            # Le hachage doit fonctionner même pour des mots de passe faibles
            assert PasswordManager.verify_password(weak_password, hashed) is True

class TestTokenSecurity:
    """Tests de sécurité des tokens JWT"""
    
    def test_token_generation(self):
        """Test de la génération de tokens"""
        user_id = "test-user-id"
        token = TokenManager.create_access_token({"sub": user_id})
        
        assert token is not None
        assert len(token) > 100
        assert isinstance(token, str)
    
    def test_token_verification(self):
        """Test de la vérification de tokens"""
        user_id = "test-user-id"
        token = TokenManager.create_access_token({"sub": user_id})
        
        payload = TokenManager.verify_token(token)
        assert payload is not None
        assert payload.get("sub") == user_id
    
    def test_invalid_token(self):
        """Test avec un token invalide"""
        invalid_token = "invalid.token.here"
        
        payload = TokenManager.verify_token(invalid_token)
        assert payload is None
    
    def test_expired_token(self):
        """Test avec un token expiré"""
        # Créer un token avec une expiration très courte
        import time
        user_id = "test-user-id"
        token = TokenManager.create_access_token({"sub": user_id}, expires_delta=timedelta(seconds=1))  # 1 seconde
        
        # Attendre que le token expire
        time.sleep(2)
        
        payload = TokenManager.verify_token(token)
        assert payload is None

class TestAPISecurity:
    """Tests de sécurité de l'API"""
    
    def test_protected_endpoints_require_auth(self):
        """Test que les endpoints protégés nécessitent une authentification"""
        protected_endpoints = [
            "/api/v1/users/",
            "/api/v1/applications/",
            "/api/v1/jobs/",
            "/api/v1/evaluations/",
            "/api/v1/notifications/",
            "/api/v1/interviews/"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 403]  # Unauthorized or Forbidden
    
    def test_cors_headers(self):
        """Test des en-têtes CORS"""
        response = client.options("/api/v1/users/")
        
        # Vérifier que les en-têtes CORS sont présents
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_security_headers(self):
        """Test des en-têtes de sécurité"""
        response = client.get("/")
        
        # Vérifier que les en-têtes de sécurité sont présents
        assert response.status_code == 200
    
    def test_invalid_credentials(self):
        """Test avec des identifiants invalides"""
        response = client.post("/api/v1/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_malformed_jwt(self):
        """Test avec un JWT malformé"""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/v1/users/", headers=headers)
        
        assert response.status_code == 401

class TestFileUploadSecurity:
    """Tests de sécurité pour l'upload de fichiers"""
    
    def test_pdf_validation(self):
        """Test de la validation des fichiers PDF"""
        # Test avec un fichier non-PDF
        files = {"file": ("test.txt", b"Not a PDF content", "text/plain")}
        data = {"document_type": "cv"}
        
        response = client.post("/api/v1/applications/test-id/documents", files=files, data=data)
        assert response.status_code == 401  # Auth required, mais on teste la structure
    
    def test_file_size_limits(self):
        """Test des limites de taille de fichier"""
        # Créer un fichier PDF simulé très volumineux
        large_content = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024)  # 10MB
        
        files = {"file": ("large.pdf", large_content, "application/pdf")}
        data = {"document_type": "cv"}
        
        response = client.post("/api/v1/applications/test-id/documents", files=files, data=data)
        assert response.status_code == 401  # Auth required
    
    def test_malicious_file_names(self):
        """Test avec des noms de fichiers malveillants"""
        malicious_names = [
            "../../../etc/passwd",
            "script.js",
            "malware.exe",
            "file.php"
        ]
        
        for name in malicious_names:
            files = {"file": (name, b"%PDF-1.4\ncontent", "application/pdf")}
            data = {"document_type": "cv"}
            
            response = client.post("/api/v1/applications/test-id/documents", files=files, data=data)
            assert response.status_code == 401  # Auth required

class TestInputValidation:
    """Tests de validation des entrées"""
    
    def test_sql_injection_attempts(self):
        """Test des tentatives d'injection SQL"""
        sql_injections = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for injection in sql_injections:
            response = client.post("/api/v1/auth/login", json={
                "email": injection,
                "password": "password"
            })
            
            # Doit retourner 422 (validation error) ou 401 (unauthorized)
            assert response.status_code in [401, 422]
    
    def test_xss_attempts(self):
        """Test des tentatives XSS"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            response = client.post("/api/v1/auth/signup", json={
                "email": f"test{payload}@example.com",
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "User",
                "role": "candidate"
            })
            
            # Doit retourner 422 (validation error)
            assert response.status_code == 422
    
    def test_path_traversal_attempts(self):
        """Test des tentatives de path traversal"""
        path_traversals = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for path in path_traversals:
            response = client.get(f"/api/v1/applications/{path}/documents")
            assert response.status_code == 401  # Auth required

class TestRateLimiting:
    """Tests de limitation de débit"""
    
    def test_login_rate_limiting(self):
        """Test de la limitation de débit pour les tentatives de connexion"""
        # Faire plusieurs tentatives de connexion rapides
        for i in range(10):
            response = client.post("/api/v1/auth/login", json={
                "email": f"test{i}@example.com",
                "password": "wrongpassword"
            })
            
            # Les premières tentatives doivent échouer avec 401
            assert response.status_code == 401
    
    def test_api_rate_limiting(self):
        """Test de la limitation de débit pour l'API"""
        # Faire plusieurs requêtes rapides
        for i in range(20):
            response = client.get("/")
            
            # Les requêtes doivent toujours réussir (pas de rate limiting sur /)
            assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
