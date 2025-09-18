"""
Schémas Pydantic pour les notifications
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID

class NotificationBase(BaseModel):
    title: str
    message: str
    type: Optional[str] = None
    link: Optional[str] = None
    read: bool = False

class NotificationCreate(NotificationBase):
    user_id: UUID
    related_application_id: Optional[UUID] = None

class NotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    link: Optional[str] = None
    read: Optional[bool] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: UUID
    related_application_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class NotificationStatsResponse(BaseModel):
    total_notifications: int
    unread_count: int
    read_count: int
    notifications_by_type: Dict[str, int]
