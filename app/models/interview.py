"""
Modèle InterviewSlot basé sur le schéma Supabase
Compatible avec InterviewCalendarModal.tsx
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.base import BaseModel

class InterviewSlot(BaseModel):
    __tablename__ = "interview_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)
    candidate_name = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    date = Column(String, nullable=False)  # Date as string (YYYY-MM-DD)
    time = Column(String, nullable=False)  # Time as string (HH:mm:ss)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled
    is_available = Column(Boolean, default=False, nullable=False)  # true = créneau libre, false = occupé
    location = Column(String, nullable=True)  # Lieu de l'entretien
    notes = Column(Text, nullable=True)  # Notes supplémentaires
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relations
    application = relationship("Application", back_populates="interview_slots")
