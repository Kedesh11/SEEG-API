"""
Service pour la gestion des notifications
"""
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta, timezone
import structlog
from app.schemas.notification import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
    NotificationListResponse, NotificationStatsResponse
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service pour la gestion des notifications"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
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
            notification = {
                "user_id": str(notification_data.user_id),
                "related_application_id": str(notification_data.related_application_id) if notification_data.related_application_id else None,
                "title": notification_data.title,
                "message": notification_data.message,
                "type": notification_data.type,
                "link": notification_data.link,
                "read": notification_data.read,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.db.notifications.insert_one(notification)
            notification["_id"] = result.inserted_id
            
            logger.info(
                "Notification created",
                notification_id=str(result.inserted_id),
                user_id=str(notification_data.user_id),
                type=notification_data.type
            )
            
            # Map _id to id for Pydantic if needed
            notification["id"] = str(notification["_id"])
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
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
        query = {"_id": ObjectId(notification_id)} if len(notification_id) == 24 else {"_id": notification_id}
        query["user_id"] = str(user_id)
        
        notification = await self.db.notifications.find_one(query)
        
        if not notification:
            raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvée")
        
        notification["id"] = str(notification.get("_id", notification.get("id")))
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
        filter_query = {"user_id": str(user_id)}
        
        if unread_only:
            filter_query["read"] = False
        
        if q:
            filter_query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"message": {"$regex": q, "$options": "i"}}
            ]
        
        if type:
            filter_query["type"] = type
        
        # Dates
        df = self._parse_date(date_from)
        dt = self._parse_date(date_to)
        if df or dt:
            date_query = {}
            if df:
                date_query["$gte"] = df
            if dt:
                date_query["$lte"] = dt
            filter_query["created_at"] = date_query
        
        # Tri
        sort_field = sort if sort in ["created_at", "title"] else "created_at"
        sort_dir = -1 if (order or "desc").lower() == "desc" else 1
        
        cursor = self.db.notifications.find(filter_query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        notifications = await cursor.to_list(length=limit)
        total_count = await self.db.notifications.count_documents(filter_query)

        per_page = limit
        page = (skip // limit) + 1 if limit else 1
        total_pages = (total_count + limit - 1) // limit if limit else 1

        for notif in notifications:
            notif["id"] = str(notif.get("_id", notif.get("id")))

        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(notif) for notif in notifications],
            total=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    def _parse_date(self, s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return None
    
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
            query = {"_id": ObjectId(notification_id)} if len(notification_id) == 24 else {"_id": notification_id}
            query["user_id"] = str(user_id)
            
            result = await self.db.notifications.update_one(
                query,
                {"$set": {"read": True, "updated_at": datetime.now(timezone.utc)}}
            )
            
            if result.matched_count == 0:
                raise NotFoundError(f"Notification avec l'ID {notification_id} non trouvée")
            
            notification = await self.db.notifications.find_one(query)
            notification["id"] = str(notification.get("_id", notification.get("id")))
            
            logger.info(
                "Notification marked as read",
                notification_id=notification_id,
                user_id=user_id
            )
            
            return NotificationResponse.model_validate(notification)
            
        except Exception as e:
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
            result = await self.db.notifications.update_many(
                {"user_id": str(user_id), "read": False},
                {"$set": {"read": True, "updated_at": datetime.now(timezone.utc)}}
            )
            
            updated_count = result.modified_count
            logger.info(
                "All notifications marked as read",
                user_id=user_id,
                updated_count=updated_count
            )
            
            return updated_count
            
        except Exception as e:
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
        count = await self.db.notifications.count_documents({"user_id": str(user_id), "read": False})
        return count
    
    async def get_user_notification_statistics(self, user_id: str) -> NotificationStatsResponse:
        """
        RÃ©cupÃ©rer les statistiques des notifications d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            NotificationStatsResponse: Statistiques des notifications
        """
        # Nombre total de notifications
        total_notifications = await self.db.notifications.count_documents({"user_id": str(user_id)})
        
        # Nombre de notifications non lues
        unread_count = await self.get_unread_count(str(user_id))
        
        # Statistiques par type
        pipeline = [
            {"$match": {"user_id": str(user_id)}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        cursor = self.db.notifications.aggregate(pipeline)
        type_stats = {item["_id"]: item["count"] async for item in cursor}

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
            
            result = await self.db.notifications.delete_many({
                "created_at": {"$lt": cutoff_date},
                "read": True
            })
            
            deleted_count = result.deleted_count
            logger.info(
                "Old notifications cleaned up",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "Failed to cleanup old notifications",
                error=str(e)
            )
            raise
