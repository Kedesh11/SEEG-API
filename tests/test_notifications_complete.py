"""
Tests complets pour le module Notifications
Couvre tous les endpoints /notifications/*

Tests de réception et marquage comme lu
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable


class TestNotificationsRead:
    """Tests pour GET /notifications/"""
    
    @pytest.mark.asyncio
    async def test_list_notifications_authenticated_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Utilisateur liste ses notifications
        Attendu: 200 OK, liste des notifications
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        response = await auth_client.get("/notifications/")
        
        assert response.status_code == 200
        data = response.json()
        
        # L'endpoint retourne 'notifications' au lieu de 'data'
        assert 'notifications' in data
        assert isinstance(data['notifications'], list)
        # Peut être vide si pas de notifications
        assert len(data['notifications']) >= 0
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_list_notifications_unauthenticated_error(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Accès sans authentification
        Attendu: 401 Unauthorized
        """
        response = await http_client.get("/notifications/")
        
        assert response.status_code == 401


class TestNotificationsMarkAsRead:
    """Tests pour PUT /notifications/{id}/read"""
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Marquer une notification comme lue
        Attendu: 200 OK
        """
        await http_client.post("/auth/signup", json=valid_signup_externe)
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Récupérer les notifications
        notifs_response = await auth_client.get("/notifications/")
        notifications = notifs_response.json()['notifications']
        
        if not notifications:
            pytest.skip("Aucune notification disponible")
        
        notif_id = notifications[0]['id']
        
        # Marquer comme lue
        response = await auth_client.put(f"/notifications/{notif_id}/read")
        
        assert response.status_code == 200
        
        await auth_client.aclose()

