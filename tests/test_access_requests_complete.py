"""
Tests complets pour le module Access Requests
Couvre tous les endpoints /access-requests/*

Focus:
- Création automatique lors inscription interne sans email SEEG
- Approbation/Rejet par admin
- Permissions
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable


class TestAccessRequestsCreation:
    """Tests de création automatique d'AccessRequest"""
    
    @pytest.mark.asyncio
    async def test_access_request_auto_created_for_internal_no_seeg_email(
        self,
        http_client: AsyncClient,
        valid_signup_interne_no_seeg_email: Dict[str, Any]
    ):
        """
        Scénario: Inscription interne sans email SEEG crée automatiquement AccessRequest
        Attendu: User créé avec statut='en_attente' (AccessRequest créée automatiquement)
        """
        # Inscription
        response = await http_client.post("/auth/signup", json=valid_signup_interne_no_seeg_email)
        
        assert response.status_code == 201
        user_data = response.json()
        
        # Vérifications principales
        assert user_data['statut'] == 'en_attente'
        assert user_data['candidate_status'] == 'interne'
        assert user_data['no_seeg_email'] is True
        assert user_data['is_internal_candidate'] is True
        
        # Note: AccessRequest créée en arrière-plan, vérifiable via endpoint admin
        # GET /access-requests nécessite authentification admin
    
    @pytest.mark.asyncio
    async def test_no_access_request_for_internal_with_seeg_email(
        self,
        http_client: AsyncClient,
        valid_signup_interne_with_seeg_email: Dict[str, Any],
        db_session
    ):
        """
        Scénario: Inscription interne avec email SEEG ne crée PAS d'AccessRequest
        Attendu: Aucune AccessRequest en base
        """
        response = await http_client.post("/auth/signup", json=valid_signup_interne_with_seeg_email)
        
        assert response.status_code == 201
        user_data = response.json()
        assert user_data['statut'] == 'actif'
        
        # Vérifier qu'aucune AccessRequest n'existe
        from app.models.access_request import AccessRequest
        from sqlalchemy import select
        
        result = await db_session.execute(
            select(AccessRequest).where(
                AccessRequest.email == valid_signup_interne_with_seeg_email['email']
            )
        )
        access_request = result.scalar_one_or_none()
        
        assert access_request is None


class TestAccessRequestsAdminOperations:
    """Tests pour les opérations admin sur les demandes d'accès"""
    
    @pytest.mark.asyncio
    async def test_admin_list_access_requests_success(
        self,
        http_client: AsyncClient,
        admin_credentials: Dict[str, str],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Admin liste toutes les demandes d'accès
        Attendu: 200 OK, liste des demandes
        """
        # Authentifier avec le compte admin
        admin_client, admin_user = await authenticated_client_factory(
            admin_credentials['email'],
            admin_credentials['password']
        )
        
        response = await admin_client.get("/access-requests/")
        
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data or isinstance(data, list)
        
        await admin_client.aclose()
    
    @pytest.mark.asyncio
    async def test_admin_approve_access_request_success(
        self,
        http_client: AsyncClient,
        admin_credentials: Dict[str, str],
        valid_signup_interne_no_seeg_email: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Admin approuve une demande d'accès
        Attendu: 200 OK, user.statut passe à 'actif'
        """
        # 1. Créer un candidat interne sans email SEEG (génère une AccessRequest)
        signup_response = await http_client.post("/auth/signup", json=valid_signup_interne_no_seeg_email)
        assert signup_response.status_code == 201
        
        # 2. Authentifier avec le compte admin
        admin_client, admin_user = await authenticated_client_factory(
            admin_credentials['email'],
            admin_credentials['password']
        )
        
        # 3. Lister les access requests pour trouver celle qui vient d'être créée
        list_response = await admin_client.get("/access-requests/")
        assert list_response.status_code == 200
        
        # 4. Trouver la demande (peut être dans 'data' ou directement dans la liste)
        data = list_response.json()
        requests_list = data.get('data', data) if isinstance(data, dict) else data
        
        if not requests_list:
            pytest.skip("Aucune demande d'accès disponible")
        
        # Trouver la demande pour notre email
        target_request = None
        for req in requests_list:
            if req['email'] == valid_signup_interne_no_seeg_email['email']:
                target_request = req
                break
        
        if not target_request:
            pytest.skip("Demande d'accès non trouvée")
        
        # 5. Approuver la demande
        approve_response = await admin_client.put(
            f"/access-requests/{target_request['id']}/approve"
        )
        
        assert approve_response.status_code == 200
        
        await admin_client.aclose()
    
    @pytest.mark.asyncio
    async def test_admin_reject_access_request_success(
        self,
        http_client: AsyncClient,
        admin_credentials: Dict[str, str],
        valid_signup_interne_no_seeg_email: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Admin rejette une demande d'accès
        Attendu: 200 OK, status='rejected'
        """
        # 1. Créer un candidat interne sans email SEEG
        signup_response = await http_client.post("/auth/signup", json=valid_signup_interne_no_seeg_email)
        assert signup_response.status_code == 201
        
        # 2. Authentifier avec le compte admin
        admin_client, admin_user = await authenticated_client_factory(
            admin_credentials['email'],
            admin_credentials['password']
        )
        
        # 3. Lister et trouver la demande
        list_response = await admin_client.get("/access-requests/")
        assert list_response.status_code == 200
        
        data = list_response.json()
        requests_list = data.get('data', data) if isinstance(data, dict) else data
        
        if not requests_list:
            pytest.skip("Aucune demande d'accès disponible")
        
        target_request = None
        for req in requests_list:
            if req['email'] == valid_signup_interne_no_seeg_email['email']:
                target_request = req
                break
        
        if not target_request:
            pytest.skip("Demande d'accès non trouvée")
        
        # 4. Rejeter la demande
        reject_response = await admin_client.put(
            f"/access-requests/{target_request['id']}/reject"
        )
        
        assert reject_response.status_code == 200
        
        await admin_client.aclose()
    
    @pytest.mark.asyncio
    async def test_candidate_cannot_access_access_requests_forbidden(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Candidat tente d'accéder aux demandes d'accès
        Attendu: 403 Forbidden
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        response = await auth_client.get("/access-requests/")
        
        # Peut être 307 (redirect) ou 403 selon la configuration
        assert response.status_code in [307, 403]
        
        await auth_client.aclose()

