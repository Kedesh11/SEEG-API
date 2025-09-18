"""
Schémas Pydantic pour les entretiens
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class InterviewSlotBase(BaseModel):
    candidate_name: str
    job_title: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    status: str = "scheduled"

class InterviewSlotCreate(InterviewSlotBase):
    application_id: UUID

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
