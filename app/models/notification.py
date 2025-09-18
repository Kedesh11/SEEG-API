"""
Modèle Notification basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel

class Notification(BaseModel):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    related_application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String)
    link = Column(String)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="notifications")
    application = relationship("Application", back_populates="notifications")
