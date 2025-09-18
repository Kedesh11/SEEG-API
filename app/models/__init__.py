"""
Modèles SQLAlchemy pour l'application
"""
from .base import Base
from .user import User
from .candidate_profile import CandidateProfile
from .seeg_agent import SeegAgent
from .job_offer import JobOffer
from .application import Application, ApplicationDocument, ApplicationDraft, ApplicationHistory
from .notification import Notification
from .interview import InterviewSlot
from .evaluation import Protocol1Evaluation, Protocol2Evaluation

__all__ = [
    "Base",
    "User",
    "CandidateProfile", 
    "SeegAgent",
    "JobOffer",
    "Application",
    "ApplicationDocument",
    "ApplicationDraft", 
    "ApplicationHistory",
    "Notification",
    "InterviewSlot",
    "Protocol1Evaluation",
    "Protocol2Evaluation"
]
