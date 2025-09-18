"""
Service pour la gestion des notifications
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from datetime import datetime, timedelta
import structlog

from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
    NotificationListResponse, NotificationStatsResponse
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service pour la gestion des notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        notification_data: NotificationCreate
    ) -> NotificationResponse:
        """
        Créer une nouvelle notification
        
        Args:
            notification_data: Données de la notification
            
        Returns:
            NotificationResponse: Notification créée
        """
        try:
            notification = Notification(
                user_id=notification_data.user_id,
                title=notification_data.title,
                message=notification_data.message,
                notification_type=notification_data.notification_type,
                is_read=notification_data.is_read,
                metadata=notification_data.metadata
            )
            
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            
            logger.info(
                "Notification created",
                notification_id=str(notification.id),
                user_id=notification_data.user_id,
                type=notification_data.notification_type
            )
            
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create notification",
                error=str(e),
                user_id=notification_data.user_id
            )
            raise
    
    async def get_notification(
        self,
        notification_id: str,
        user_id: str
    ) -> NotificationResponse:
        """
        Récupérer une notification par son ID
        
        Args:
            notification_id: ID de la notification
            user_id: ID de l'utilisateur
            
        Returns:
            NotificationResponse: Notification
        """
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvée")
        
        return NotificationResponse.model_validate(notification)
    
    async def get_user_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False
    ) -> NotificationListResponse:
        """
        Récupérer les notifications d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            unread_only: Afficher seulement les notifications non lues
            
        Returns:
            NotificationListResponse: Liste des notifications
        """
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
            count_query = count_query.where(Notification.is_read == False)
        
        query = query.order_by(desc(Notification.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        return NotificationListResponse(
            items=[NotificationResponse.model_validate(notif) for notif in notifications],
            total=total_count,
            skip=skip,
            limit=limit,
            has_more=skip + len(notifications) < total_count
        )
    
    async def mark_as_read(
        self,
        notification_id: str,
        user_id: str
    ) -> NotificationResponse:
        """
        Marquer une notification comme lue
        
        Args:
            notification_id: ID de la notification
            user_id: ID de l'utilisateur
            
        Returns:
            NotificationResponse: Notification mise à jour
        """
        try:
            # Vérification de l'existence de la notification
            result = await self.db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id
                    )
                )
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvée")
            
            # Mise à jour du statut
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            notification.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(notification)
            
            logger.info(
                "Notification marked as read",
                notification_id=notification_id,
                user_id=user_id
            )
            
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to mark notification as read",
                notification_id=notification_id,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Marquer toutes les notifications comme lues
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            int: Nombre de notifications mises à jour
        """
        try:
            result = await self.db.execute(
                update(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    )
                )
                .values(
                    is_read=True,
                    read_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            await self.db.commit()
            
            updated_count = result.rowcount
            logger.info(
                "All notifications marked as read",
                user_id=user_id,
                updated_count=updated_count
            )
            
            return updated_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to mark all notifications as read",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def get_unread_count(self, user_id: str) -> int:
        """
        Récupérer le nombre de notifications non lues
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            int: Nombre de notifications non lues
        """
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )
        return result.scalar() or 0
    
    async def get_user_notification_statistics(self, user_id: str) -> NotificationStatsResponse:
        """
        Récupérer les statistiques des notifications d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            NotificationStatsResponse: Statistiques des notifications
        """
        # Nombre total de notifications
        total_result = await self.db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == user_id)
        )
        total_notifications = total_result.scalar()
        
        # Nombre de notifications non lues
        unread_count = await self.get_unread_count(user_id)
        
        # Statistiques par type
        type_result = await self.db.execute(
            select(Notification.notification_type, func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .group_by(Notification.notification_type)
        )
        type_stats = {row[0]: row[1] for row in type_result.fetchall()}
        
        # Statistiques par mois (derniers 12 mois)
        monthly_result = await self.db.execute(
            select(
                func.date_trunc('month', Notification.created_at).label('month'),
                func.count(Notification.id).label('count')
            )
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= datetime.utcnow() - timedelta(days=365)
                )
            )
            .group_by(func.date_trunc('month', Notification.created_at))
            .order_by('month')
        )
        monthly_stats = {row[0]: row[1] for row in monthly_result.fetchall()}
        
        return NotificationStatsResponse(
            total_notifications=total_notifications,
            unread_count=unread_count,
            type_distribution=type_stats,
            monthly_trend=monthly_stats
        )
    
    async def cleanup_old_notifications(self, days_old: int = 90) -> int:
        """
        Nettoyer les anciennes notifications
        
        Args:
            days_old: Nombre de jours pour considérer une notification comme ancienne
            
        Returns:
            int: Nombre de notifications supprimées
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self.db.execute(
                delete(Notification).where(
                    and_(
                        Notification.created_at < cutoff_date,
                        Notification.is_read == True
                    )
                )
            )
            
            await self.db.commit()
            
            deleted_count = result.rowcount
            logger.info(
                "Old notifications cleaned up",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date
            )
            
            return deleted_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to cleanup old notifications",
                error=str(e)
            )
            raise
