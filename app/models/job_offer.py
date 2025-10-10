"""
Modèle JobOffer basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class JobOffer(BaseModel):
    __tablename__ = "job_offers"  # type: ignore[assignment]

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
    is_internal_only = Column(Boolean, default=False, nullable=False)  # True = Réservée aux candidats INTERNES uniquement, False = Accessible à TOUS (internes + externes)
    application_deadline = Column(DateTime(timezone=True))
    date_limite = Column(DateTime(timezone=True))
    reporting_line = Column(String)
    salary_note = Column(String)
    start_date = Column(DateTime(timezone=True))
    profile = Column(Text)
    categorie_metier = Column(String)
    job_grade = Column(String)
    
    # Questions MTP pour l'évaluation des candidats
    question_metier = Column(Text, nullable=True, comment="Question évaluant les compétences techniques et opérationnelles")
    question_talent = Column(Text, nullable=True, comment="Question évaluant les aptitudes personnelles et le potentiel")
    question_paradigme = Column(Text, nullable=True, comment="Question évaluant la vision, les valeurs et la compatibilité culturelle")
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)  # type: ignore[assignment]
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)  # type: ignore[assignment]

    # Relations
    recruiter = relationship("User", back_populates="job_offers")
    applications = relationship("Application", back_populates="job_offer")
    application_drafts = relationship("ApplicationDraft", back_populates="job_offer")
