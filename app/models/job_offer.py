"""
Modèle JobOffer basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    requirements = Column(JSONB)  # Array of strings stored as JSONB (better performance)
    benefits = Column(JSONB)      # Array of strings stored as JSONB
    responsibilities = Column(JSONB)  # Array of strings stored as JSONB
    status = Column(String, default="active")
    
    # Statut de visibilité de l'offre
    # "tous" = Accessible à tous (internes + externes)
    # "interne" = Réservée aux candidats internes SEEG uniquement
    # "externe" = Réservée aux candidats externes uniquement
    offer_status = Column(String, default="tous", nullable=False)
    
    application_deadline = Column(DateTime(timezone=True))
    date_limite = Column(DateTime(timezone=True))
    reporting_line = Column(String)
    salary_note = Column(String)
    start_date = Column(DateTime(timezone=True))
    profile = Column(Text)
    categorie_metier = Column(String)
    job_grade = Column(String)
    
    # Questions MTP pour l'évaluation des candidats (stockées en JSONB)
    # Format: {"questions_metier": ["Q1", "Q2", ...], "questions_talent": [...], "questions_paradigme": [...]}
    # Max: 7 questions métier (internes), 3 talent, 3 paradigme
    questions_mtp = Column(JSONB, nullable=True, comment="Questions MTP sous forme de JSON structuré")
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)  # type: ignore[assignment]
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)  # type: ignore[assignment]

    # Relations
    recruiter = relationship("User", back_populates="job_offers")
    applications = relationship("Application", back_populates="job_offer")
    application_drafts = relationship("ApplicationDraft", back_populates="job_offer")
