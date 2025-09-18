"""
Schémas Pydantic pour les agents SEEG
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SeegAgentBase(BaseModel):
    matricule: int
    nom: Optional[str] = None
    prenom: Optional[str] = None

class SeegAgentCreate(SeegAgentBase):
    pass

class SeegAgentUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None

class SeegAgentResponse(SeegAgentBase):
    created_at: datetime
    
    class Config:
        from_attributes = True
