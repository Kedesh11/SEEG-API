"""
Fixtures pour les clients HTTP
Fournit des clients authentifiés avec différents rôles
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable, AsyncGenerator


@pytest.fixture
def api_base_url() -> str:
    """URL de base de l'API (locale ou production selon config)"""
    import os
    env = os.getenv("TEST_ENV", "local")
    
    if env == "production":
        return "https://seeg-backend-api.azurewebsites.net/api/v1"
    else:
        return "http://localhost:8000/api/v1"


@pytest.fixture
async def http_client(api_base_url: str) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP de base sans authentification"""
    async with AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
async def authenticated_client_factory(http_client: AsyncClient) -> Callable:
    """
    Factory pour créer des clients authentifiés
    
    Usage:
        client = await authenticated_client_factory(email, password)
    """
    async def _create(email: str, password: str) -> tuple[AsyncClient, Dict[str, Any]]:
        """
        Crée un client authentifié et retourne (client, user_data)
        """
        # Connexion
        login_response = await http_client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        
        if login_response.status_code != 200:
            raise Exception(f"Échec connexion: {login_response.text}")
        
        token_data = login_response.json()
        token = token_data['access_token']
        user = token_data.get('user', {})
        
        # Créer un nouveau client avec le token
        authenticated_client = AsyncClient(
            base_url=http_client.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        
        return authenticated_client, user
    
    return _create

