"""
Tests complets pour le module Applications
Couvre tous les endpoints /applications/*

Focus sur le nouveau flow:
- Création atomique avec documents obligatoires
- Validation des 3 documents requis
- Upload transactionnel
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable


class TestApplicationsCreate:
    """Tests pour POST /applications/"""
    
    @pytest.mark.asyncio
    async def test_create_application_with_all_documents_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_application_data_with_documents: Callable
    ):
        """
        Scénario: Création candidature avec les 3 documents obligatoires
        Attendu: 201 Created, 3 documents uploadés
        """
        # Créer un candidat et se connecter
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Récupérer une offre (supposons qu'elle existe)
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre d'emploi disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        
        # Créer la candidature
        app_data = valid_application_data_with_documents(user['id'], job_id)
        response = await auth_client.post("/applications/", json=app_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['success'] is True
        assert "3 document(s) uploadé(s)" in data['message']
        assert data['data']['id'] is not None
        assert data['data']['candidate_id'] == user['id']
        assert data['data']['job_offer_id'] == job_id
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_create_application_missing_documents_error(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        invalid_application_missing_documents: Callable
    ):
        """
        Scénario: Création candidature sans documents
        Attendu: 422 Unprocessable Entity
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = invalid_application_missing_documents(user['id'], job_id)
        
        response = await auth_client.post("/applications/", json=app_data)
        
        assert response.status_code == 422
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_create_application_missing_one_document_error(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        invalid_application_missing_one_document: Callable
    ):
        """
        Scénario: Création avec seulement 2 documents (manque diplôme)
        Attendu: 422, message "Documents manquants: Diplôme"
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = invalid_application_missing_one_document(user['id'], job_id)
        
        response = await auth_client.post("/applications/", json=app_data)
        
        assert response.status_code == 422
        assert "Diplôme" in response.text
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_create_duplicate_application_error(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_application_data_with_documents: Callable
    ):
        """
        Scénario: Tentative de création d'une candidature en double
        Attendu: 400 Bad Request
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = valid_application_data_with_documents(user['id'], job_id)
        
        # Première création
        response1 = await auth_client.post("/applications/", json=app_data)
        assert response1.status_code == 201
        
        # Tentative de duplication
        response2 = await auth_client.post("/applications/", json=app_data)
        assert response2.status_code == 400
        assert "existe déjà" in response2.text.lower()
        
        await auth_client.aclose()


class TestApplicationsRead:
    """Tests pour GET /applications/*"""
    
    @pytest.mark.asyncio
    async def test_list_applications_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Lister toutes les candidatures
        Attendu: 200 OK, liste paginée
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        response = await auth_client.get("/applications/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert 'data' in data
        assert 'total' in data
        assert 'page' in data
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_get_application_by_id_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_application_data_with_documents: Callable
    ):
        """
        Scénario: Récupérer une candidature spécifique
        Attendu: 200 OK, données complètes
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Créer une candidature
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = valid_application_data_with_documents(user['id'], job_id)
        
        create_response = await auth_client.post("/applications/", json=app_data)
        app_id = create_response.json()['data']['id']
        
        # Récupérer la candidature
        response = await auth_client.get(f"/applications/{app_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert data['data']['id'] == app_id
        
        await auth_client.aclose()


class TestApplicationsDocuments:
    """Tests pour GET /applications/{id}/documents/*"""
    
    @pytest.mark.asyncio
    async def test_list_documents_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_application_data_with_documents: Callable
    ):
        """
        Scénario: Lister les documents d'une candidature
        Attendu: 200 OK, liste des 3 documents (sans file_data)
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Créer candidature avec documents
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = valid_application_data_with_documents(user['id'], job_id)
        
        create_response = await auth_client.post("/applications/", json=app_data)
        app_id = create_response.json()['data']['id']
        
        # Lister les documents
        response = await auth_client.get(f"/applications/{app_id}/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['success'] is True
        assert len(data['data']) >= 3  # Au moins les 3 obligatoires
        
        # Vérifier que file_data n'est pas inclus (performance)
        for doc in data['data']:
            assert 'file_data' not in doc
            assert doc['document_type'] in ['cv', 'cover_letter', 'diplome', 'certificats']
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_download_document_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_application_data_with_documents: Callable
    ):
        """
        Scénario: Télécharger un document spécifique
        Attendu: 200 OK, PDF retourné
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Créer candidature
        jobs_response = await auth_client.get("/jobs")
        if jobs_response.status_code != 200 or not jobs_response.json().get('data'):
            pytest.skip("Aucune offre disponible")
        
        job_id = jobs_response.json()['data'][0]['id']
        app_data = valid_application_data_with_documents(user['id'], job_id)
        
        create_response = await auth_client.post("/applications/", json=app_data)
        app_id = create_response.json()['data']['id']
        
        # Récupérer les documents
        docs_response = await auth_client.get(f"/applications/{app_id}/documents")
        doc_id = docs_response.json()['data'][0]['id']
        
        # Télécharger le document
        response = await auth_client.get(f"/applications/{app_id}/documents/{doc_id}/download")
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/pdf'
        assert len(response.content) > 0
        assert response.content.startswith(b'%PDF')
        
        await auth_client.aclose()

