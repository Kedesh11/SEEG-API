"""
Schémas Pydantic pour les entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID
import re

class InterviewSlotBase(BaseModel):
    date: str = Field(..., description="Format: YYYY-MM-DD (ex: '2025-10-15')")
    time: str = Field(..., description="Format: HH:mm:ss (ex: '09:00:00')")
    application_id: Optional[UUID] = Field(None, description="ID de la candidature liée")
    candidate_name: Optional[str] = Field(None, description="Nom complet du candidat")
    job_title: Optional[str] = Field(None, description="Titre du poste")
    status: str = Field(default="scheduled", description="scheduled, completed, cancelled")
    is_available: bool = Field(default=False, description="true = créneau libre, false = occupé")
    location: Optional[str] = Field(None, description="Lieu de l'entretien")
    notes: Optional[str] = Field(None, description="Notes supplémentaires")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Valider le format de date YYYY-MM-DD"""
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Format de date invalide. Attendu: YYYY-MM-DD")
        return v
    
    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Valider le format d'heure HH:mm:ss"""
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', v):
            raise ValueError("Format d'heure invalide. Attendu: HH:mm:ss")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Valider le statut"""
        allowed_statuses = ['scheduled', 'completed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f"Statut invalide. Autorisés: {', '.join(allowed_statuses)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-15",
                "time": "09:00:00",
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "candidate_name": "John Doe",
                "job_title": "Développeur Full Stack",
                "status": "scheduled",
                "is_available": False,
                "location": "Libreville",
                "notes": "Entretien technique"
            }
        }

class InterviewSlotCreate(BaseModel):
    date: str = Field(..., description="Format: YYYY-MM-DD")
    time: str = Field(..., description="Format: HH:mm:ss")
    application_id: UUID = Field(..., description="ID de la candidature")
    candidate_name: str = Field(..., description="Nom du candidat")
    job_title: str = Field(..., description="Titre du poste")
    status: str = Field(default="scheduled", description="scheduled, completed, cancelled")
    location: Optional[str] = Field(None, description="Lieu de l'entretien")
    notes: Optional[str] = Field(None, description="Notes supplémentaires")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Format de date invalide. Attendu: YYYY-MM-DD")
        return v
    
    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', v):
            raise ValueError("Format d'heure invalide. Attendu: HH:mm:ss")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-15",
                "time": "09:00:00",
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "candidate_name": "John Doe",
                "job_title": "Développeur Full Stack",
                "status": "scheduled",
                "location": "Libreville",
                "notes": "Entretien programmé"
            }
        }

class InterviewSlotUpdate(BaseModel):
    date: Optional[str] = Field(None, description="Format: YYYY-MM-DD")
    time: Optional[str] = Field(None, description="Format: HH:mm:ss")
    application_id: Optional[UUID] = None
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Format de date invalide. Attendu: YYYY-MM-DD")
        return v
    
    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^\d{2}:\d{2}:\d{2}$', v):
            raise ValueError("Format d'heure invalide. Attendu: HH:mm:ss")
        return v

class InterviewSlotResponse(BaseModel):
    id: UUID
    date: str
    time: str
    application_id: Optional[UUID]
    candidate_name: Optional[str]
    job_title: Optional[str]
    status: str
    is_available: bool
    location: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "00000000-0000-0000-0000-0000000000SS",
                "date": "2025-10-15",
                "time": "09:00:00",
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "candidate_name": "John Doe",
                "job_title": "Développeur Full Stack",
                "status": "scheduled",
                "is_available": False,
                "location": "Libreville",
                "notes": "Entretien technique",
                "created_at": "2025-10-02T10:00:00Z",
                "updated_at": "2025-10-02T10:00:00Z"
            }
        }
    }

class InterviewSlotListResponse(BaseModel):
    data: List[InterviewSlotResponse]
    total: int
    page: int
    per_page: int
    total_pages: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "data": [],
                "total": 0,
                "page": 1,
                "per_page": 50,
                "total_pages": 0
            }
        }

class InterviewStatsResponse(BaseModel):
    total_interviews: int
    scheduled_interviews: int
    completed_interviews: int
    cancelled_interviews: int
    interviews_by_status: Dict[str, int]
