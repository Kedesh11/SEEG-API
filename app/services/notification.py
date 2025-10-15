"""
Service pour la gestion des notifications
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from datetime import datetime, timedelta, timezone
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
        CrÃ©er une nouvelle notification
        
        Args:
            notification_data: DonnÃ©es de la notification
            
        Returns:
            NotificationResponse: Notification crÃ©Ã©e
        """
        try:
            notification = Notification()
            notification.user_id = notification_data.user_id  # type: ignore
            notification.related_application_id = notification_data.related_application_id  # type: ignore
            notification.title = notification_data.title  # type: ignore
            notification.message = notification_data.message  # type: ignore
            notification.type = notification_data.type  # type: ignore
            notification.link = notification_data.link  # type: ignore
            notification.read = notification_data.read  # type: ignore
            
            self.db.add(notification)
            #  PAS de commit ici - MAIS flush nécessaire avant refresh
            await self.db.flush()
            await self.db.refresh(notification)
            
            logger.info(
                "Notification created",
                notification_id=str(notification.id),
                user_id=str(notification_data.user_id),
                type=notification_data.type
            )
            
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
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
        RÃ©cupÃ©rer une notification par son ID
        
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
            raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvÃ©e")
        
        return NotificationResponse.model_validate(notification)
    
    async def get_user_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False,
        q: Optional[str] = None,
        type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> NotificationListResponse:
        """
        RÃ©cupÃ©rer les notifications d'un utilisateur (avec filtres et tri)
        Retourne un schÃ©ma conforme Ã  NotificationListResponse
        { notifications, total, page, per_page, total_pages }
        """
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.read == False)
            count_query = count_query.where(Notification.read == False)
        
        if q:
            like = f"%{q}%"
            query = query.where(or_(Notification.title.ilike(like), Notification.message.ilike(like)))
            count_query = count_query.where(or_(Notification.title.ilike(like), Notification.message.ilike(like)))
        
        if type:
            query = query.where(Notification.type == type)
            count_query = count_query.where(Notification.type == type)
        
        # Dates
        def parse_date(s: Optional[str]):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None
        df = parse_date(date_from)
        dt = parse_date(date_to)
        if df:
            query = query.where(Notification.created_at >= df)
            count_query = count_query.where(Notification.created_at >= df)
        if dt:
            query = query.where(Notification.created_at <= dt)
            count_query = count_query.where(Notification.created_at <= dt)
        
        # Tri
        if sort in {"created_at", "title"}:
            direction = desc if (order or "desc").lower() == "desc" else None
            if direction:
                query = query.order_by(direction(getattr(Notification, sort)))
            else:
                query = query.order_by(getattr(Notification, sort))
        else:
            query = query.order_by(desc(Notification.created_at))
        
        # Pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        per_page = limit
        page = (skip // limit) + 1 if limit else 1
        total_pages = (total_count + limit - 1) // limit if limit else 1

        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(notif) for notif in notifications],
            total=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
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
            NotificationResponse: Notification mise Ã  jour
        """
        try:
            # VÃ©rification de l'existence de la notification
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
                raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvÃ©e")
            
            # Mise Ã  jour du statut
            notification.read = True  # type: ignore
            notification.updated_at = datetime.now(timezone.utc)
            
            #  PAS de commit ici
            await self.db.refresh(notification)
            
            logger.info(
                "Notification marked as read",
                notification_id=notification_id,
                user_id=user_id
            )
            
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
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
            int: Nombre de notifications mises Ã  jour
        """
        try:
            result = await self.db.execute(
                update(Notification)
                .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.read == False
                )
            )
            .values(
                read=True,
                updated_at=datetime.now(timezone.utc)
            )
            )
            
            #  PAS de commit ici
            
            updated_count = result.rowcount
            logger.info(
                "All notifications marked as read",
                user_id=user_id,
                updated_count=updated_count
            )
            
            return updated_count
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to mark all notifications as read",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def get_unread_count(self, user_id: str) -> int:
        """
        RÃ©cupÃ©rer le nombre de notifications non lues
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            int: Nombre de notifications non lues
        """
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.read == False
                )
            )
        )
        return result.scalar() or 0
    
    async def get_user_notification_statistics(self, user_id: str) -> NotificationStatsResponse:
        """
        RÃ©cupÃ©rer les statistiques des notifications d'un utilisateur
        
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
            select(Notification.type, func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .group_by(Notification.type)
        )
        type_stats = {row[0]: row[1] for row in type_result.fetchall()}

        read_count = (total_notifications or 0) - (unread_count or 0)

        return NotificationStatsResponse(
            total_notifications=total_notifications or 0,
            unread_count=unread_count or 0,
            read_count=read_count if read_count >= 0 else 0,
            notifications_by_type=type_stats
        )
    
    async def cleanup_old_notifications(self, days_old: int = 90) -> int:
        """
        Nettoyer les anciennes notifications
        
        Args:
            days_old: Nombre de jours pour considÃ©rer une notification comme ancienne
            
        Returns:
            int: Nombre de notifications supprimÃ©es
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            result = await self.db.execute(
                delete(Notification).where(
                    and_(
                        Notification.created_at < cutoff_date,
                        Notification.read == True
                    )
                )
            )
            
            #  PAS de commit ici
            
            deleted_count = result.rowcount
            logger.info(
                "Old notifications cleaned up",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date
            )
            
            return deleted_count
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to cleanup old notifications",
                error=str(e)
            )
            raise
