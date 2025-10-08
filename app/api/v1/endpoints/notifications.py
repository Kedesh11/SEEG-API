"""
Endpoints pour la gestion des notifications
"""
from typing import List, Dict, Set, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.notification import NotificationService
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse, NotificationStatsResponse
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError
from app.core.security.security import TokenManager
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")

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
    WebSocket temps rÃ©el pour les notifications.
    
    - Authentification: fournir un token JWT via le paramÃ¨tre de requÃªte `?token=...`.
    - Alternatives: certaines bibliothÃ¨ques envoient le token dans l'en-tÃªte `Sec-WebSocket-Protocol`.
    - Messages Ã©mis: `notifications:new`, `notifications:updated`, `notifications:updated_all`, `notifications:unread_count`.
    """
    token = websocket.query_params.get("token")
    if not token:
        # Essai via header Sec-WebSocket-Protocol (certaines libs passent le token lÃ )
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


@router.get("/", response_model=NotificationListResponse, summary="Lister mes notifications (filtres avancÃ©s)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"items": [], "total": 0, "skip": 0, "limit": 100, "has_more": False}}}}}
})
async def get_notifications(
    skip: int = Query(0, ge=0, description="Nombre d'Ã©lÃ©ments Ã  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'Ã©lÃ©ments Ã  retourner"),
    unread_only: bool = Query(False, description="Afficher seulement les notifications non lues"),
    q: Optional[str] = Query(None, description="Recherche texte (titre, message)"),
    type: Optional[str] = Query(None, description="Filtrer par type de notification"),
    date_from: Optional[str] = Query(None, description="Date de dÃ©but (YYYY-MM-DD ou ISO8601)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD ou ISO8601)"),
    sort: Optional[str] = Query(None, description="Champ de tri (created_at)"),
    order: Optional[str] = Query("desc", description="Ordre de tri: asc|desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer la liste des notifications de l'utilisateur.
    
    Utiliser les paramÃ¨tres de filtre pour restreindre les rÃ©sultats et le tri pour l'ordre d'affichage.
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
        safe_log("info", "Notifications rÃ©cupÃ©rÃ©es", user_id=str(current_user.id), count=len(return_value.items) if hasattr(return_value, 'items') else 0)
        return return_value
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration notifications", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/{notification_id}", response_model=NotificationResponse, summary="RÃ©cupÃ©rer une notification par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": 1, "title": "Nouvelle candidature", "message": "Un candidat a postulÃ©", "is_read": False}}}}, "404": {"description": "Non trouvÃ©e"}}
})
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer une notification par son ID unique.
    """
    try:
        notification_service = NotificationService(db)
        result = await notification_service.get_notification(notification_id, str(current_user.id))
        safe_log("info", "Notification rÃ©cupÃ©rÃ©e", notification_id=notification_id, user_id=str(current_user.id))
        return result
    except NotFoundError as e:
        safe_log("warning", "Notification non trouvÃ©e", notification_id=notification_id, user_id=str(current_user.id))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration notification", notification_id=notification_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/{notification_id}/read", response_model=NotificationResponse, summary="Marquer une notification comme lue", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": 1, "is_read": True}}}}, "404": {"description": "Non trouvÃ©e"}}
})
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marquer une notification comme lue et diffuser l'Ã©tat vers les clients.
    """
    try:
        notification_service = NotificationService(db)
        resp = await notification_service.mark_as_read(notification_id, str(current_user.id))
        # Emettre la mise Ã  jour du compteur non lus
        await _broadcast_unread_count(db, str(current_user.id))
        # Emettre l'Ã©vÃ©nement de notification mise Ã  jour
        await manager.send_to_user(str(current_user.id), {"type": "notifications:updated", "id": notification_id})
        safe_log("info", "Notification marquÃ©e comme lue", notification_id=notification_id, user_id=str(current_user.id))
        return resp
    except NotFoundError as e:
        safe_log("warning", "Notification non trouvÃ©e pour marquer lue", notification_id=notification_id, user_id=str(current_user.id))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur marquage notification lue", notification_id=notification_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Marquer toutes mes notifications comme lues", openapi_extra={
    "responses": {"204": {"description": "Toutes les notifications marquÃ©es comme lues"}}
})
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marquer toutes les notifications de l'utilisateur comme lues et diffuser l'Ã©tat.
    """
    try:
        notification_service = NotificationService(db)
        await notification_service.mark_all_as_read(str(current_user.id))
        # Emettre la mise Ã  jour du compteur non lus
        await _broadcast_unread_count(db, str(current_user.id))
        await manager.send_to_user(str(current_user.id), {"type": "notifications:updated_all"})
        safe_log("info", "Toutes notifications marquÃ©es comme lues", user_id=str(current_user.id))
        return None
    except Exception as e:
        safe_log("error", "Erreur marquage toutes notifications lues", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/unread-count", response_model=dict, summary="Compter mes notifications non lues", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"count": 0}}}}}
})
async def get_unread_notifications_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retourne le nombre de notifications non lues sous la forme `{ "count": <nombre> }`.
    """
    try:
        notification_service = NotificationService(db)
        count = await notification_service.get_unread_count(str(current_user.id))
        # Harmonisation de la rÃ©ponse
        safe_log("info", "Compteur notifications non lues rÃ©cupÃ©rÃ©", user_id=str(current_user.id), count=count)
        return {"count": count}
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration compteur notifications", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/overview", response_model=NotificationStatsResponse, openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "total_notifications": 0, "unread_count": 0, "type_distribution": {}, "monthly_trend": {}
    }}}}}
})
async def get_notification_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les statistiques des notifications
    
    Retourne:
    - Nombre total de notifications
    - Nombre de notifications non lues
    - RÃ©partition par type
    - Tendance mensuelle
    """
    try:
        notification_service = NotificationService(db)
        stats = await notification_service.get_user_notification_statistics(str(current_user.id))
        safe_log("info", "Statistiques notifications rÃ©cupÃ©rÃ©es", user_id=str(current_user.id))
        return stats
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration statistiques notifications", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
