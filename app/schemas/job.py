"""
Schémas Pydantic pour les offres d'emploi
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class JobOfferBase(BaseModel):
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    status: str = "active"
    is_internal_only: bool = False  # True = Offre réservée aux candidats INTERNES, False = Accessible à tous
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP pour l'évaluation des candidats
    question_metier: Optional[str] = Field(None, description="Question évaluant les compétences techniques et opérationnelles")
    question_talent: Optional[str] = Field(None, description="Question évaluant les aptitudes personnelles et le potentiel")
    question_paradigme: Optional[str] = Field(None, description="Question évaluant la vision, les valeurs et la compatibilité culturelle")

class JobOfferCreate(JobOfferBase):
    recruiter_id: UUID

class JobOfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    status: Optional[str] = None
    is_internal_only: Optional[bool] = None  # True = Offre réservée aux candidats INTERNES, False = Accessible à tous
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP pour l'évaluation des candidats
    question_metier: Optional[str] = None
    question_talent: Optional[str] = None
    question_paradigme: Optional[str] = None

class JobOfferResponse(JobOfferBase):
    id: UUID
    recruiter_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
