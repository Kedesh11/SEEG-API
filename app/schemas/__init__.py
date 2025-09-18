"""
Schémas Pydantic pour l'API
"""
from .user import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserWithProfile,
    CandidateProfileBase, CandidateProfileCreate, CandidateProfileUpdate, CandidateProfileResponse
)
from .job import JobOfferBase, JobOfferCreate, JobOfferUpdate, JobOfferResponse, JobOfferWithApplications
from .application import (
    ApplicationBase, ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationWithDetails,
    ApplicationDocumentBase, ApplicationDocumentCreate, ApplicationDocumentResponse,
    ApplicationDraftBase, ApplicationDraftCreate, ApplicationDraftUpdate, ApplicationDraftResponse,
    ApplicationHistoryBase, ApplicationHistoryCreate, ApplicationHistoryResponse
)
from .evaluation import (
    Protocol1EvaluationBase, Protocol1EvaluationCreate, Protocol1EvaluationUpdate, Protocol1EvaluationResponse,
    Protocol2EvaluationBase, Protocol2EvaluationCreate, Protocol2EvaluationUpdate, Protocol2EvaluationResponse
)
from .notification import NotificationBase, NotificationCreate, NotificationUpdate, NotificationResponse
from .interview import InterviewSlotBase, InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse
from .seeg_agent import SeegAgentBase, SeegAgentCreate, SeegAgentUpdate, SeegAgentResponse

__all__ = [
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserWithProfile",
    "CandidateProfileBase", "CandidateProfileCreate", "CandidateProfileUpdate", "CandidateProfileResponse",
    
    # Job schemas
    "JobOfferBase", "JobOfferCreate", "JobOfferUpdate", "JobOfferResponse", "JobOfferWithApplications",
    
    # Application schemas
    "ApplicationBase", "ApplicationCreate", "ApplicationUpdate", "ApplicationResponse", "ApplicationWithDetails",
    "ApplicationDocumentBase", "ApplicationDocumentCreate", "ApplicationDocumentResponse",
    "ApplicationDraftBase", "ApplicationDraftCreate", "ApplicationDraftUpdate", "ApplicationDraftResponse",
    "ApplicationHistoryBase", "ApplicationHistoryCreate", "ApplicationHistoryResponse",
    
    # Evaluation schemas
    "Protocol1EvaluationBase", "Protocol1EvaluationCreate", "Protocol1EvaluationUpdate", "Protocol1EvaluationResponse",
    "Protocol2EvaluationBase", "Protocol2EvaluationCreate", "Protocol2EvaluationUpdate", "Protocol2EvaluationResponse",
    
    # Notification schemas
    "NotificationBase", "NotificationCreate", "NotificationUpdate", "NotificationResponse",
    
    # Interview schemas
    "InterviewSlotBase", "InterviewSlotCreate", "InterviewSlotUpdate", "InterviewSlotResponse",
    
    # SeegAgent schemas
    "SeegAgentBase", "SeegAgentCreate", "SeegAgentUpdate", "SeegAgentResponse"
]
