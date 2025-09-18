"""
Modèle SeegAgent basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime

from app.models.base import BaseModel

class SeegAgent(BaseModel):
    __tablename__ = "seeg_agents"

    matricule = Column(Integer, primary_key=True)
    nom = Column(String)
    prenom = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
