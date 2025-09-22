"""
Endpoints pour la gestion des notifications
"""
from typing import List, Dict, Set, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.notification import NotificationService
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse, NotificationStatsResponse
)
from app.core.security.security import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError
from app.core.security.security import TokenManager

router = APIRouter()

# Gestionnaire de connexions WebSocket pour les notifications
class NotificationConnectionManager:
    def __init__(self) -> None:
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        try:
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        except Exception:
            pass

    async def send_to_user(self, user_id: str, message: dict) -> None:
        if user_id not in self.user_connections:
            return
        dead: Set[WebSocket] = set()
        for ws in list(self.user_connections[user_id]):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.user_connections[user_id].discard(ws)
        if user_id in self.user_connections and not self.user_connections[user_id]:
            del self.user_connections[user_id]

manager = NotificationConnectionManager()


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket temps réel pour les notifications.
    
    - Authentification: fournir un token JWT via le paramètre de requête `?token=...`.
    - Alternatives: certaines bibliothèques envoient le token dans l'en-tête `Sec-WebSocket-Protocol`.
    - Messages émis: `notifications:new`, `notifications:updated`, `notifications:updated_all`, `notifications:unread_count`.
    """
    token = websocket.query_params.get("token")
    if not token:
        # Essai via header Sec-WebSocket-Protocol (certaines libs passent le token là)
        token = websocket.headers.get("sec-websocket-protocol")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = TokenManager.get_user_id_from_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # On garde la connexion ouverte; on ignore les messages entrants (ping client)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass


async def _broadcast_unread_count(db: AsyncSession, user_id: str) -> None:
    service = NotificationService(db)
    count = await service.get_unread_count(user_id)
    await manager.send_to_user(user_id, {"type": "notifications:unread_count", "count": count})


@router.get("/", response_model=NotificationListResponse, summary="Lister mes notifications (filtres avancés)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"items": [], "total": 0, "skip": 0, "limit": 100, "has_more": False}}}}}
})
async def get_notifications(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    unread_only: bool = Query(False, description="Afficher seulement les notifications non lues"),
    q: Optional[str] = Query(None, description="Recherche texte (titre, message)"),
    type: Optional[str] = Query(None, description="Filtrer par type de notification"),
    date_from: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD ou ISO8601)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD ou ISO8601)"),
    sort: Optional[str] = Query(None, description="Champ de tri (created_at)"),
    order: Optional[str] = Query("desc", description="Ordre de tri: asc|desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer la liste des notifications de l'utilisateur.
    
    Utiliser les paramètres de filtre pour restreindre les résultats et le tri pour l'ordre d'affichage.
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.get_user_notifications(
            user_id=str(current_user.id),
            skip=skip,
            limit=limit,
            unread_only=unread_only,
            q=q,
            type=type,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            order=order
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/{notification_id}", response_model=NotificationResponse, summary="Récupérer une notification par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": 1, "title": "Nouvelle candidature", "message": "Un candidat a postulé", "is_read": False}}}}, "404": {"description": "Non trouvée"}}
})
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une notification par son ID unique.
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.get_notification(notification_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/{notification_id}/read", response_model=NotificationResponse, summary="Marquer une notification comme lue", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": 1, "is_read": True}}}}, "404": {"description": "Non trouvée"}}
})
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Marquer une notification comme lue et diffuser l'état vers les clients.
    """
    try:
        notification_service = NotificationService(db)
        resp = await notification_service.mark_as_read(notification_id, str(current_user.id))
        # Emettre la mise à jour du compteur non lus
        await _broadcast_unread_count(db, str(current_user.id))
        # Emettre l'événement de notification mise à jour
        await manager.send_to_user(str(current_user.id), {"type": "notifications:updated", "id": notification_id})
        return resp
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Marquer toutes mes notifications comme lues", openapi_extra={
    "responses": {"204": {"description": "Toutes les notifications marquées comme lues"}}
})
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Marquer toutes les notifications de l'utilisateur comme lues et diffuser l'état.
    """
    try:
        notification_service = NotificationService(db)
        await notification_service.mark_all_as_read(str(current_user.id))
        # Emettre la mise à jour du compteur non lus
        await _broadcast_unread_count(db, str(current_user.id))
        await manager.send_to_user(str(current_user.id), {"type": "notifications:updated_all"})
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/unread-count", response_model=dict, summary="Compter mes notifications non lues", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"count": 0}}}}}
})
async def get_unread_notifications_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retourne le nombre de notifications non lues sous la forme `{ "count": <nombre> }`.
    """
    try:
        notification_service = NotificationService(db)
        count = await notification_service.get_unread_count(str(current_user.id))
        # Harmonisation de la réponse
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/overview", response_model=NotificationStatsResponse, openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "total_notifications": 0, "unread_count": 0, "type_distribution": {}, "monthly_trend": {}
    }}}}}
})
async def get_notification_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les statistiques des notifications
    
    Retourne:
    - Nombre total de notifications
    - Nombre de notifications non lues
    - Répartition par type
    - Tendance mensuelle
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.get_user_notification_statistics(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
