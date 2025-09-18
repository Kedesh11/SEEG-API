"""
Modèle InterviewSlot basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class InterviewSlot(BaseModel):
    __tablename__ = "interview_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    candidate_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    date = Column(String, nullable=False)  # Date as string (YYYY-MM-DD)
    time = Column(String, nullable=False)  # Time as string (HH:MM)
    status = Column(String, default="scheduled")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    application = relationship("Application", back_populates="interview_slots")
