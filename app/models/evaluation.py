"""
Modèles d'évaluation basés sur le schéma Supabase
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class Protocol1Evaluation(BaseModel):
    __tablename__ = "protocol1_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Status and completion
    status = Column(String, default="pending")
    completed = Column(Boolean, default=False)
    documents_verified = Column(Boolean, default=False)
    
    # Documentary scores
    cv_score = Column(Numeric(5, 2))
    cv_comments = Column(Text)
    diplomes_certificats_score = Column(Numeric(5, 2))
    diplomes_certificats_comments = Column(Text)
    lettre_motivation_score = Column(Numeric(5, 2))
    lettre_motivation_comments = Column(Text)
    documentary_score = Column(Numeric(5, 2))
    
    # MTP scores
    metier_score = Column(Numeric(5, 2))
    metier_comments = Column(Text)
    metier_notes = Column(Text)
    paradigme_score = Column(Numeric(5, 2))
    paradigme_comments = Column(Text)
    paradigme_notes = Column(Text)
    talent_score = Column(Numeric(5, 2))
    talent_comments = Column(Text)
    talent_notes = Column(Text)
    mtp_score = Column(Numeric(5, 2))
    
    # Interview scores
    interview_metier_score = Column(Numeric(5, 2))
    interview_metier_comments = Column(Text)
    interview_paradigme_score = Column(Numeric(5, 2))
    interview_paradigme_comments = Column(Text)
    interview_talent_score = Column(Numeric(5, 2))
    interview_talent_comments = Column(Text)
    interview_score = Column(Numeric(5, 2))
    interview_date = Column(DateTime(timezone=True))
    
    # Gap analysis
    gap_competence_score = Column(Numeric(5, 2))
    gap_competence_comments = Column(Text)
    
    # Adherence
    adherence_metier = Column(Boolean)
    adherence_paradigme = Column(Boolean)
    adherence_talent = Column(Boolean)
    
    # Final scores
    overall_score = Column(Numeric(5, 2))
    total_score = Column(Numeric(5, 2))
    general_summary = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    application = relationship("Application", back_populates="protocol1_evaluation")
    evaluator = relationship("User", back_populates="protocol1_evaluations")

class Protocol2Evaluation(BaseModel):
    __tablename__ = "protocol2_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Status and completion
    completed = Column(Boolean, default=False)
    interview_completed = Column(Boolean, default=False)
    physical_visit = Column(Boolean, default=False)
    skills_gap_assessed = Column(Boolean, default=False)
    job_sheet_created = Column(Boolean, default=False)
    qcm_role_completed = Column(Boolean, default=False)
    qcm_codir_completed = Column(Boolean, default=False)
    
    # Scores
    qcm_role_score = Column(Numeric(5, 2))
    qcm_codir_score = Column(Numeric(5, 2))
    overall_score = Column(Numeric(5, 2))
    
    # Notes
    interview_notes = Column(Text)
    visit_notes = Column(Text)
    skills_gap_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    application = relationship("Application", back_populates="protocol2_evaluation")
    evaluator = relationship("User", back_populates="protocol2_evaluations")
