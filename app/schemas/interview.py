"""
Schémas Pydantic pour les entretiens
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID

class InterviewSlotBase(BaseModel):
    candidate_name: str
    job_title: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    status: str = "scheduled"

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_name": "KABA Marie",
                "job_title": "Ingénieur Réseaux",
                "date": "2025-10-05",
                "time": "10:00",
                "status": "scheduled"
            }
        }

class InterviewSlotCreate(InterviewSlotBase):
    application_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "candidate_name": "KABA Marie",
                "job_title": "Ingénieur Réseaux",
                "date": "2025-10-05",
                "time": "10:00"
            }
        }

class InterviewSlotUpdate(BaseModel):
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None

class InterviewSlotResponse(InterviewSlotBase):
    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "00000000-0000-0000-0000-0000000000SS",
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "candidate_name": "KABA Marie",
                "job_title": "Ingénieur Réseaux",
                "date": "2025-10-05",
                "time": "10:00",
                "status": "scheduled",
                "created_at": "2025-09-22T10:00:00Z",
                "updated_at": "2025-09-22T10:30:00Z"
            }
        }

class InterviewSlotListResponse(BaseModel):
    slots: List[InterviewSlotResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class InterviewStatsResponse(BaseModel):
    total_interviews: int
    scheduled_interviews: int
    completed_interviews: int
    cancelled_interviews: int
    interviews_by_status: Dict[str, int]
