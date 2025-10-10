"""
Modèles Application basés sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer, LargeBinary, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class Application(BaseModel):
    __tablename__ = "applications"  # type: ignore[assignment]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"))
    status = Column(String, default="pending")
    
    reference_contacts = Column(Text)
    availability_start = Column(DateTime(timezone=True))
    
    # Champ de qualification pour candidats internes
    has_been_manager = Column(Boolean, nullable=False, default=False, comment="Indique si le candidat interne a déjà occupé un poste de chef/manager")
    
    # Champs de recommandation pour candidats externes
    ref_entreprise = Column(String(255), nullable=True, comment="Nom de l'entreprise/organisation recommandante")
    ref_fullname = Column(String(255), nullable=True, comment="Nom complet du référent")
    ref_mail = Column(String(255), nullable=True, comment="Adresse e-mail du référent")
    ref_contact = Column(String(50), nullable=True, comment="Numéro de téléphone du référent")
    
    # MTP Questions
    mtp_answers = Column(JSON)
    mtp_metier_q1 = Column(Text)
    mtp_metier_q2 = Column(Text)
    mtp_metier_q3 = Column(Text)
    mtp_paradigme_q1 = Column(Text)
    mtp_paradigme_q2 = Column(Text)
    mtp_paradigme_q3 = Column(Text)
    mtp_talent_q1 = Column(Text)
    mtp_talent_q2 = Column(Text)
    mtp_talent_q3 = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)  # type: ignore[assignment]
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)  # type: ignore[assignment]

    # Relations
    candidate = relationship("User", back_populates="applications")
    job_offer = relationship("JobOffer", back_populates="applications")
    documents = relationship("ApplicationDocument", back_populates="application")
    history = relationship("ApplicationHistory", back_populates="application")
    protocol1_evaluation = relationship("Protocol1Evaluation", back_populates="application", uselist=False)
    protocol2_evaluation = relationship("Protocol2Evaluation", back_populates="application", uselist=False)
    interview_slots = relationship("InterviewSlot", back_populates="application")
    notifications = relationship("Notification", back_populates="application")

class ApplicationDocument(BaseModel):
    __tablename__ = "application_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    document_type = Column(String, nullable=False)  # 'cover_letter', 'cv', 'certificats', 'diplome'
    file_name = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)  # Fichier PDF stocké en binaire
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, default="application/pdf")  # Type MIME
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    application = relationship("Application", back_populates="documents")

class ApplicationDraft(BaseModel):
    __tablename__ = "application_drafts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), primary_key=True)
    form_data = Column(JSON)
    ui_state = Column(JSON)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = relationship("User")
    job_offer = relationship("JobOffer", back_populates="application_drafts")

class ApplicationHistory(BaseModel):
    __tablename__ = "application_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    previous_status = Column(String)
    new_status = Column(String)
    notes = Column(Text)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relations
    application = relationship("Application", back_populates="history")
    changed_by_user = relationship("User", back_populates="application_history")
