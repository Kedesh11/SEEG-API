"""
Modèles améliorés avec de meilleures relations
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Numeric, LargeBinary, ARRAY
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import uuid

from app.models.base import BaseModel

# ===== MODÈLES AMÉLIORÉS =====

class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)  # candidate, recruiter, admin, observer
    phone = Column(String)
    date_of_birth = Column(DateTime(timezone=True))
    sexe = Column(String)
    matricule = Column(String, unique=True, index=True)
    
    # Relations améliorées
    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    job_offers = relationship("JobOffer", back_populates="recruiter", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    protocol1_evaluations = relationship("Protocol1Evaluation", back_populates="evaluator", cascade="all, delete-orphan")
    protocol2_evaluations = relationship("Protocol2Evaluation", back_populates="evaluator", cascade="all, delete-orphan")
    application_history = relationship("ApplicationHistory", back_populates="changed_by_user", cascade="all, delete-orphan")
    interview_slots = relationship("InterviewSlot", back_populates="recruiter", cascade="all, delete-orphan")

class CandidateProfile(BaseModel):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    address = Column(String)
    availability = Column(String)
    birth_date = Column(DateTime(timezone=True))
    current_department = Column(String)
    current_position = Column(String)
    cv_url = Column(String)
    education = Column(String)
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    gender = Column(String, index=True)  # Index pour les statistiques
    linkedin_url = Column(String)
    portfolio_url = Column(String)
    skills = Column(ARRAY(String))
    years_experience = Column(Integer, index=True)  # Index pour les filtres
    
    # Relations améliorées
    user = relationship("User", back_populates="candidate_profile")
    experiences = relationship("Experience", back_populates="profile", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="profile", cascade="all, delete-orphan")
    skills_detailed = relationship("Skill", back_populates="profile", cascade="all, delete-orphan")

class Experience(BaseModel):
    __tablename__ = "experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    description = Column(Text)
    is_current = Column(Boolean, default=False)
    
    # Relations
    profile = relationship("CandidateProfile", back_populates="experiences")

class Education(BaseModel):
    __tablename__ = "educations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    is_current = Column(Boolean, default=False)
    
    # Relations
    profile = relationship("CandidateProfile", back_populates="educations")

class Skill(BaseModel):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False, index=True)
    level = Column(Integer)  # 1-5 niveau de compétence
    category = Column(String, index=True)  # technique, soft, language, etc.
    
    # Relations
    profile = relationship("CandidateProfile", back_populates="skills_detailed")

class JobOffer(BaseModel):
    __tablename__ = "job_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False, index=True)
    contract_type = Column(String, nullable=False, index=True)
    department = Column(String, index=True)  # Index pour les statistiques
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    requirements = Column(ARRAY(String))
    benefits = Column(ARRAY(String))
    responsibilities = Column(ARRAY(String))
    status = Column(String, default="active", index=True)
    application_deadline = Column(DateTime(timezone=True), index=True)
    date_limite = Column(DateTime(timezone=True), index=True)
    reporting_line = Column(String)
    salary_note = Column(String)
    start_date = Column(DateTime(timezone=True))
    profile = Column(Text)
    categorie_metier = Column(String, index=True)
    job_grade = Column(String)
    
    # Relations améliorées
    recruiter = relationship("User", back_populates="job_offers")
    applications = relationship("Application", back_populates="job_offer", cascade="all, delete-orphan")
    application_drafts = relationship("ApplicationDraft", back_populates="job_offer", cascade="all, delete-orphan")

class Application(BaseModel):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), index=True)
    status = Column(String, default="pending", index=True)
    
    reference_contacts = Column(Text)
    availability_start = Column(DateTime(timezone=True))
    
    # MTP Questions
    mtp_answers = Column(ARRAY(String))  # Amélioration: utiliser ARRAY au lieu de JSON
    mtp_metier_q1 = Column(Text)
    mtp_metier_q2 = Column(Text)
    mtp_metier_q3 = Column(Text)
    mtp_paradigme_q1 = Column(Text)
    mtp_paradigme_q2 = Column(Text)
    mtp_paradigme_q3 = Column(Text)
    mtp_talent_q1 = Column(Text)
    mtp_talent_q2 = Column(Text)
    mtp_talent_q3 = Column(Text)
    
    # Relations améliorées
    candidate = relationship("User", back_populates="applications")
    job_offer = relationship("JobOffer", back_populates="applications")
    documents = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")
    history = relationship("ApplicationHistory", back_populates="application", cascade="all, delete-orphan")
    protocol1_evaluation = relationship("Protocol1Evaluation", back_populates="application", uselist=False, cascade="all, delete-orphan")
    protocol2_evaluation = relationship("Protocol2Evaluation", back_populates="application", uselist=False, cascade="all, delete-orphan")
    interview_slots = relationship("InterviewSlot", back_populates="application", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="application", cascade="all, delete-orphan")

class ApplicationDocument(BaseModel):
    __tablename__ = "application_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    document_type = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_data = Column(BYTEA, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, default="application/pdf")
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relations
    application = relationship("Application", back_populates="documents")

class InterviewSlot(BaseModel):
    __tablename__ = "interview_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)  # NOUVEAU
    candidate_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    date = Column(String, nullable=False, index=True)
    time = Column(String, nullable=False)
    status = Column(String, default="scheduled", index=True)
    meeting_link = Column(String)  # NOUVEAU: pour les entretiens en ligne
    notes = Column(Text)  # NOUVEAU: notes de l'entretien
    
    # Relations améliorées
    application = relationship("Application", back_populates="interview_slots")
    recruiter = relationship("User", back_populates="interview_slots")

class Notification(BaseModel):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # AMÉLIORATION: UUID au lieu d'Integer
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    related_application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, index=True)
    link = Column(String)
    read = Column(Boolean, default=False, index=True)
    priority = Column(String, default="normal")  # NOUVEAU: normal, high, urgent
    
    # Relations améliorées
    user = relationship("User", back_populates="notifications")
    application = relationship("Application", back_populates="notifications")

# ===== INDEX COMPOSITES POUR PERFORMANCE =====

# Index composites pour les requêtes fréquentes
# Ces index seront créés via une migration séparée

"""
Index recommandés à créer :

1. applications_candidate_job_idx ON applications(candidate_id, job_offer_id)
2. applications_status_created_idx ON applications(status, created_at)
3. applications_job_status_idx ON applications(job_offer_id, status)
4. job_offers_recruiter_status_idx ON job_offers(recruiter_id, status)
5. notifications_user_read_idx ON notifications(user_id, read)
6. interview_slots_date_status_idx ON interview_slots(date, status)
7. candidate_profiles_gender_experience_idx ON candidate_profiles(gender, years_experience)
"""
