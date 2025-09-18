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
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None

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
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None

class JobOfferResponse(JobOfferBase):
    id: UUID
    recruiter_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
