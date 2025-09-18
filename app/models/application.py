"""
Modèles Application basés sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class Application(BaseModel):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"))
    status = Column(String, default="pending")
    cover_letter = Column(Text)
    motivation = Column(Text)
    reference_contacts = Column(Text)
    availability_start = Column(DateTime(timezone=True))
    url_idee_projet = Column(String)
    url_lettre_integrite = Column(String)
    
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
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

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
    document_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_size = Column(Integer)
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
