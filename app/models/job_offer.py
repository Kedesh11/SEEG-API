"""
Modèle JobOffer basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class JobOffer(BaseModel):
    __tablename__ = "job_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    contract_type = Column(String, nullable=False)
    department = Column(String)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    requirements = Column(JSON)  # Array of strings stored as JSON
    benefits = Column(JSON)      # Array of strings stored as JSON
    responsibilities = Column(JSON)  # Array of strings stored as JSON
    status = Column(String, default="active")
    application_deadline = Column(DateTime(timezone=True))
    date_limite = Column(DateTime(timezone=True))
    reporting_line = Column(String)
    salary_note = Column(String)
    start_date = Column(DateTime(timezone=True))
    profile = Column(Text)
    categorie_metier = Column(String)
    job_grade = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    recruiter = relationship("User", back_populates="job_offers")
    applications = relationship("Application", back_populates="job_offer")
    application_drafts = relationship("ApplicationDraft", back_populates="job_offer")
