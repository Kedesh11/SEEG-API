"""
Schémas Pydantic pour les offres d'emploi
"""
from pydantic import BaseModel, Field, field_validator
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
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Questions MTP au format: {questions_metier: [...], questions_talent: [...], questions_paradigme: [...]}"
    )
    
    @field_validator('questions_mtp')
    @classmethod
    def validate_mtp_questions(cls, v):
        """Valider que les questions MTP respectent les limites"""
        if v is None:
            return v
        
        # Vérifier les limites: 7 métier max, 3 talent max, 3 paradigme max
        if 'questions_metier' in v and len(v['questions_metier']) > 7:
            raise ValueError("Maximum 7 questions métier autorisées")
        if 'questions_talent' in v and len(v['questions_talent']) > 3:
            raise ValueError("Maximum 3 questions talent autorisées")
        if 'questions_paradigme' in v and len(v['questions_paradigme']) > 3:
            raise ValueError("Maximum 3 questions paradigme autorisées")
        
        return v

class JobOfferCreate(JobOfferBase):
    recruiter_id: Optional[UUID] = None  # Ajouté automatiquement depuis le token JWT

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
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = None

class JobOfferResponse(JobOfferBase):
    id: UUID
    recruiter_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
