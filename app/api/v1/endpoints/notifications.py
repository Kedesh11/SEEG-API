"""
Endpoints pour la gestion des notifications
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.notification import NotificationService
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse, NotificationStatsResponse
)
from app.core.security import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    unread_only: bool = Query(False, description="Afficher seulement les notifications non lues"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer la liste des notifications de l'utilisateur
    
    - **skip**: Nombre d'éléments à ignorer (pagination)
    - **limit**: Nombre maximum d'éléments à retourner
    - **unread_only**: Afficher seulement les notifications non lues
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.get_user_notifications(
            user_id=str(current_user.id),
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une notification par son ID
    
    - **notification_id**: ID unique de la notification
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.get_notification(notification_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Marquer une notification comme lue
    
    - **notification_id**: ID de la notification à marquer comme lue
    """
    try:
        notification_service = NotificationService(db)
        return await notification_service.mark_as_read(notification_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Marquer toutes les notifications comme lues
    """
    try:
        notification_service = NotificationService(db)
        await notification_service.mark_all_as_read(str(current_user.id))
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/unread-count", response_model=dict)
async def get_unread_notifications_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer le nombre de notifications non lues
    """
    try:
        notification_service = NotificationService(db)
        count = await notification_service.get_unread_count(str(current_user.id))
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/overview", response_model=NotificationStatsResponse)
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
