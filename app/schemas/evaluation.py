"""
Schémas Pydantic pour les évaluations
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class Protocol1EvaluationBase(BaseModel):
    status: str = "pending"
    completed: bool = False
    documents_verified: bool = False
    
    # Documentary scores
    cv_score: Optional[Decimal] = None
    cv_comments: Optional[str] = None
    diplomes_certificats_score: Optional[Decimal] = None
    diplomes_certificats_comments: Optional[str] = None
    lettre_motivation_score: Optional[Decimal] = None
    lettre_motivation_comments: Optional[str] = None
    documentary_score: Optional[Decimal] = None
    
    # MTP scores
    metier_score: Optional[Decimal] = None
    metier_comments: Optional[str] = None
    metier_notes: Optional[str] = None
    paradigme_score: Optional[Decimal] = None
    paradigme_comments: Optional[str] = None
    paradigme_notes: Optional[str] = None
    talent_score: Optional[Decimal] = None
    talent_comments: Optional[str] = None
    talent_notes: Optional[str] = None
    mtp_score: Optional[Decimal] = None
    
    # Interview scores
    interview_metier_score: Optional[Decimal] = None
    interview_metier_comments: Optional[str] = None
    interview_paradigme_score: Optional[Decimal] = None
    interview_paradigme_comments: Optional[str] = None
    interview_talent_score: Optional[Decimal] = None
    interview_talent_comments: Optional[str] = None
    interview_score: Optional[Decimal] = None
    interview_date: Optional[datetime] = None
    
    # Gap analysis
    gap_competence_score: Optional[Decimal] = None
    gap_competence_comments: Optional[str] = None
    
    # Adherence
    adherence_metier: Optional[bool] = None
    adherence_paradigme: Optional[bool] = None
    adherence_talent: Optional[bool] = None
    
    # Final scores
    overall_score: Optional[Decimal] = None
    total_score: Optional[Decimal] = None
    general_summary: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "in_progress",
                "cv_score": 15,
                "mtp_score": 14,
                "interview_score": 16,
                "overall_score": 15,
                "general_summary": "Solide parcours et adéquation au poste."
            }
        }

class Protocol1EvaluationCreate(Protocol1EvaluationBase):
    application_id: UUID
    evaluator_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "evaluator_id": "00000000-0000-0000-0000-0000000000EE",
                "cv_score": 15,
                "mtp_score": 14,
                "interview_score": 16
            }
        }

class Protocol1EvaluationUpdate(BaseModel):
    status: Optional[str] = None
    completed: Optional[bool] = None
    documents_verified: Optional[bool] = None
    cv_score: Optional[Decimal] = None
    cv_comments: Optional[str] = None
    diplomes_certificats_score: Optional[Decimal] = None
    diplomes_certificats_comments: Optional[str] = None
    lettre_motivation_score: Optional[Decimal] = None
    lettre_motivation_comments: Optional[str] = None
    documentary_score: Optional[Decimal] = None
    metier_score: Optional[Decimal] = None
    metier_comments: Optional[str] = None
    metier_notes: Optional[str] = None
    paradigme_score: Optional[Decimal] = None
    paradigme_comments: Optional[str] = None
    paradigme_notes: Optional[str] = None
    talent_score: Optional[Decimal] = None
    talent_comments: Optional[str] = None
    talent_notes: Optional[str] = None
    mtp_score: Optional[Decimal] = None
    interview_metier_score: Optional[Decimal] = None
    interview_metier_comments: Optional[str] = None
    interview_paradigme_score: Optional[Decimal] = None
    interview_paradigme_comments: Optional[str] = None
    interview_talent_score: Optional[Decimal] = None
    interview_talent_comments: Optional[str] = None
    interview_score: Optional[Decimal] = None
    interview_date: Optional[datetime] = None
    gap_competence_score: Optional[Decimal] = None
    gap_competence_comments: Optional[str] = None
    adherence_metier: Optional[bool] = None
    adherence_paradigme: Optional[bool] = None
    adherence_talent: Optional[bool] = None
    overall_score: Optional[Decimal] = None
    total_score: Optional[Decimal] = None
    general_summary: Optional[str] = None

class Protocol1EvaluationResponse(Protocol1EvaluationBase):
    id: UUID
    application_id: UUID
    evaluator_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Protocol2EvaluationBase(BaseModel):
    completed: bool = False
    interview_completed: bool = False
    physical_visit: bool = False
    skills_gap_assessed: bool = False
    job_sheet_created: bool = False
    qcm_role_completed: bool = False
    qcm_codir_completed: bool = False
    
    # Scores
    qcm_role_score: Optional[Decimal] = None
    qcm_codir_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    
    # Notes
    interview_notes: Optional[str] = None
    visit_notes: Optional[str] = None
    skills_gap_notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "qcm_role_completed": True,
                "qcm_codir_completed": True,
                "qcm_role_score": 17,
                "qcm_codir_score": 16,
                "overall_score": 16.5
            }
        }

class Protocol2EvaluationCreate(Protocol2EvaluationBase):
    application_id: UUID
    evaluator_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "evaluator_id": "00000000-0000-0000-0000-0000000000EE",
                "qcm_role_completed": True,
                "qcm_codir_completed": True,
                "qcm_role_score": 17,
                "qcm_codir_score": 16
            }
        }

class Protocol2EvaluationUpdate(BaseModel):
    completed: Optional[bool] = None
    interview_completed: Optional[bool] = None
    physical_visit: Optional[bool] = None
    skills_gap_assessed: Optional[bool] = None
    job_sheet_created: Optional[bool] = None
    qcm_role_completed: Optional[bool] = None
    qcm_codir_completed: Optional[bool] = None
    qcm_role_score: Optional[Decimal] = None
    qcm_codir_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    interview_notes: Optional[str] = None
    visit_notes: Optional[str] = None
    skills_gap_notes: Optional[str] = None

class Protocol2EvaluationResponse(Protocol2EvaluationBase):
    id: UUID
    application_id: UUID
    evaluator_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
