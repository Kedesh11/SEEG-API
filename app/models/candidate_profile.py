"""
Modèle CandidateProfile basé sur le schéma Supabase
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel

class CandidateProfile(BaseModel):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    address = Column(String)
    availability = Column(String)
    birth_date = Column(DateTime(timezone=True))
    current_department = Column(String)
    current_position = Column(String)
    cv_url = Column(String)
    education = Column(String)
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    gender = Column(String)
    linkedin_url = Column(String)
    portfolio_url = Column(String)
    skills = Column(String)  # JSON string pour compatibilité SQLite
    years_experience = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = relationship("User", back_populates="candidate_profile")
