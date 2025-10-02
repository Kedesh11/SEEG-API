"""
Modèle User basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # candidate, recruiter, admin, observer
    phone = Column(String)
    date_of_birth = Column(DateTime(timezone=True))
    sexe = Column(String)
    matricule = Column(Integer, unique=True, index=True)
    hashed_password = Column(String, nullable=False)  # Ajout du champ pour le mot de passe haché
    
    # Nouveaux champs
    email_verified = Column(Boolean, default=False, nullable=False)  # Email vérifié ou non
    last_login = Column(DateTime(timezone=True), nullable=True)  # Dernière connexion
    is_active = Column(Boolean, default=True, nullable=False)  # Compte actif ou désactivé
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relations
    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False)
    job_offers = relationship("JobOffer", back_populates="recruiter")
    applications = relationship("Application", back_populates="candidate")
    notifications = relationship("Notification", back_populates="user")
    protocol1_evaluations = relationship("Protocol1Evaluation", back_populates="evaluator")
    protocol2_evaluations = relationship("Protocol2Evaluation", back_populates="evaluator")
    application_history = relationship("ApplicationHistory", back_populates="changed_by_user")
