"""
Modèle CandidateProfile basé sur le schéma Supabase
"""
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column, declared_attr

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User

class CandidateProfile(BaseModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "candidate_profiles"

    # Champs spécifiques (id, created_at, updated_at viennent de BaseModel)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True
    )
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    availability: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birth_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cv_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expected_salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    skills: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    years_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relations
    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
