"""
Modèle User basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # candidate, recruiter, admin, observer
    phone = Column(String)
    date_of_birth = Column(Date, nullable=True, comment="Date de naissance du candidat")
    sexe = Column(String(1), nullable=True, comment="Sexe: M (Homme) ou F (Femme)")
    matricule = Column(Integer, unique=True, index=True, nullable=True, comment="Matricule SEEG (obligatoire pour candidats internes)")
    hashed_password = Column(String, nullable=False)  # Ajout du champ pour le mot de passe haché
    
    # Champs d'authentification et activation
    email_verified = Column(Boolean, default=False, nullable=False, comment="Email vérifié ou non")
    last_login = Column(DateTime(timezone=True), nullable=True, comment="Dernière connexion")
    is_active = Column(Boolean, default=True, nullable=False, comment="Compte actif ou désactivé (legacy)")
    is_internal_candidate = Column(Boolean, default=False, nullable=False, comment="True = interne (avec matricule), False = externe (sans matricule)")
    
    # Nouveaux champs pour le système d'authentification enrichi
    adresse = Column(Text, nullable=True, comment="Adresse complète du candidat")
    candidate_status = Column(String(10), nullable=True, comment="Type de candidat: 'interne' ou 'externe'")
    statut = Column(String(20), nullable=False, default="actif", comment="Statut du compte: actif, en_attente, inactif, bloqué, archivé")
    poste_actuel = Column(Text, nullable=True, comment="Poste actuel du candidat")
    annees_experience = Column(Integer, nullable=True, comment="Années d'expérience professionnelle")
    no_seeg_email = Column(Boolean, nullable=False, default=False, comment="Candidat interne sans email @seeg-gabon.com")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  # type: ignore[assignment]
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))  # type: ignore[assignment]
    
    # Relations
    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False)
    job_offers = relationship("JobOffer", back_populates="recruiter")
    applications = relationship("Application", back_populates="candidate")
    notifications = relationship("Notification", back_populates="user")
    protocol1_evaluations = relationship("Protocol1Evaluation", back_populates="evaluator")
    protocol2_evaluations = relationship("Protocol2Evaluation", back_populates="evaluator")
    application_history = relationship("ApplicationHistory", back_populates="changed_by_user")
