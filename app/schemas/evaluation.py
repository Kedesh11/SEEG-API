"""
Schémas Pydantic pour les évaluations
=====================================
Architecture: Type-Safe + Protocoles MTP + Documentation Complète

Schémas principaux:
- Protocol1Evaluation: Évaluation candidats EXTERNES (3 phases : documentaire, MTP, entretien)
- Protocol2Evaluation: Évaluation candidats INTERNES (QCM + entretiens)

Protocole MTP (Métier, Talent, Paradigme):
- Phase 1: Évaluation documentaire (CV, diplômes, lettre)
- Phase 2: Analyse réponses MTP écrites
- Phase 3: Entretien avec évaluation MTP orale
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

# ============================================================================
# CONSTANTES - Statuts d'évaluation et limites de scores
# ============================================================================

# Statuts d'évaluation
EVAL_STATUS_PENDING = "pending"         # En attente
EVAL_STATUS_IN_PROGRESS = "in_progress"  # En cours
EVAL_STATUS_COMPLETED = "completed"     # Terminée
EVAL_STATUS_REJECTED = "rejected"       # Rejetée
ALLOWED_EVAL_STATUS = {EVAL_STATUS_PENDING, EVAL_STATUS_IN_PROGRESS, EVAL_STATUS_COMPLETED, EVAL_STATUS_REJECTED}

# Limites de scores (grille MTP SEEG)
SCORE_MIN = 0      # Score minimum
SCORE_MAX = 20     # Score maximum (notation /20)
SCORE_PASS = 10    # Score de passage minimum

# Pondérations Protocol 1 (Candidats EXTERNES)
WEIGHT_DOCUMENTARY = 0.2   # 20% - Analyse documents
WEIGHT_MTP = 0.4           # 40% - Réponses MTP écrites
WEIGHT_INTERVIEW = 0.4     # 40% - Entretien

# Pondérations Protocol 2 (Candidats INTERNES)
WEIGHT_QCM_ROLE = 0.5      # 50% - QCM métier
WEIGHT_QCM_CODIR = 0.5     # 50% - QCM CODIR

class Protocol1EvaluationBase(BaseModel):
    """
    Schéma de base pour l'évaluation Protocol 1 (Candidats EXTERNES).
    
    **Protocole en 3 phases**:
    1. Phase Documentaire (20%) : Évaluation CV, diplômes, lettre de motivation
    2. Phase MTP Écrite (40%) : Analyse réponses MTP (Métier, Talent, Paradigme)
    3. Phase Entretien (40%) : Entretien oral avec évaluation MTP
    
    **Grille de notation**: /20 pour chaque critère
    **Score de passage**: 10/20 minimum
    """
    status: str = Field(EVAL_STATUS_PENDING, description=f"Statut: {', '.join(ALLOWED_EVAL_STATUS)}")
    completed: bool = Field(False, description="Évaluation complète (toutes phases)")
    documents_verified: bool = Field(False, description="Documents vérifiés")
    
    # ========== PHASE 1: SCORES DOCUMENTAIRES (20%) ==========
    cv_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score CV /{SCORE_MAX}")
    cv_comments: Optional[str] = Field(None, description="Commentaires sur le CV")
    diplomes_certificats_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score diplômes/certificats /{SCORE_MAX}")
    diplomes_certificats_comments: Optional[str] = Field(None, description="Commentaires sur les diplômes")
    lettre_motivation_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score lettre de motivation /{SCORE_MAX}")
    lettre_motivation_comments: Optional[str] = Field(None, description="Commentaires sur la lettre")
    documentary_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score documentaire global /{SCORE_MAX}")
    
    # ========== PHASE 2: SCORES MTP ÉCRITS (40%) ==========
    metier_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Métier (réponses écrites) /{SCORE_MAX}")
    metier_comments: Optional[str] = Field(None, description="Commentaires Métier")
    metier_notes: Optional[str] = Field(None, description="Notes détaillées Métier")
    paradigme_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Paradigme (réponses écrites) /{SCORE_MAX}")
    paradigme_comments: Optional[str] = Field(None, description="Commentaires Paradigme")
    paradigme_notes: Optional[str] = Field(None, description="Notes détaillées Paradigme")
    talent_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Talent (réponses écrites) /{SCORE_MAX}")
    talent_comments: Optional[str] = Field(None, description="Commentaires Talent")
    talent_notes: Optional[str] = Field(None, description="Notes détaillées Talent")
    mtp_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score MTP global /{SCORE_MAX}")
    
    # ========== PHASE 3: SCORES ENTRETIEN (40%) ==========
    interview_metier_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Métier (entretien) /{SCORE_MAX}")
    interview_metier_comments: Optional[str] = Field(None, description="Commentaires Métier entretien")
    interview_paradigme_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Paradigme (entretien) /{SCORE_MAX}")
    interview_paradigme_comments: Optional[str] = Field(None, description="Commentaires Paradigme entretien")
    interview_talent_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score Talent (entretien) /{SCORE_MAX}")
    interview_talent_comments: Optional[str] = Field(None, description="Commentaires Talent entretien")
    interview_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score entretien global /{SCORE_MAX}")
    interview_date: Optional[datetime] = Field(None, description="Date de l'entretien")
    
    # ========== GAP ANALYSIS ==========
    gap_competence_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description="Score gap de compétences")
    gap_competence_comments: Optional[str] = Field(None, description="Commentaires gap de compétences")
    
    # ========== ADHÉRENCE MTP ==========
    adherence_metier: Optional[bool] = Field(None, description="Adhérence au paradigme Métier SEEG")
    adherence_paradigme: Optional[bool] = Field(None, description="Adhérence au paradigme organisationnel SEEG")
    adherence_talent: Optional[bool] = Field(None, description="Adhérence aux valeurs Talent SEEG")
    
    # ========== SCORES FINAUX ==========
    overall_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score global final /{SCORE_MAX}")
    total_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score total agrégé /{SCORE_MAX}")
    general_summary: Optional[str] = Field(None, description="Synthèse générale de l'évaluation")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Évaluation Protocol 1 complète (candidat externe)",
                    "value": {
                        "status": "completed",
                        "completed": True,
                        "documents_verified": True,
                        "cv_score": 16,
                        "cv_comments": "CV bien structuré, expérience pertinente",
                        "diplomes_certificats_score": 18,
                        "diplomes_certificats_comments": "Master + Certifications Azure",
                        "lettre_motivation_score": 15,
                        "lettre_motivation_comments": "Motivation claire",
                        "documentary_score": 16.3,
                        "metier_score": 17,
                        "metier_comments": "Excellente maîtrise technique",
                        "paradigme_score": 14,
                        "paradigme_comments": "Bonne vision stratégique",
                        "talent_score": 16,
                        "talent_comments": "Soft skills adaptés",
                        "mtp_score": 15.7,
                        "interview_metier_score": 18,
                        "interview_paradigme_score": 15,
                        "interview_talent_score": 17,
                        "interview_score": 16.7,
                        "interview_date": "2024-10-15T10:00:00Z",
                        "adherence_metier": True,
                        "adherence_paradigme": True,
                        "adherence_talent": True,
                        "overall_score": 16.2,
                        "total_score": 16.2,
                        "general_summary": "Candidat excellent, forte adéquation au poste. Recommandé pour embauche."
                    }
                }
            ]
        }

class Protocol1EvaluationCreate(Protocol1EvaluationBase):
    """
    Schéma pour créer une évaluation Protocol 1.
    
    Requiert l'ID de la candidature et de l'évaluateur.
    """
    application_id: UUID = Field(..., description="ID de la candidature à évaluer")
    evaluator_id: UUID = Field(..., description="ID du recruteur évaluateur")

    model_config = {
        "json_schema_extra": {
            "example": {
                "application_id": "724f8672-e3a4-4fa1-9856-06ac455bf518",
                "evaluator_id": "770e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "documents_verified": True,
                "cv_score": 15,
                "mtp_score": 14,
                "interview_score": 16
            }
        }
    }

class Protocol1EvaluationUpdate(BaseModel):
    status: Optional[str] = None
    completed: Optional[bool] = None
    documents_verified: Optional[bool] = None
    cv_score: Optional[Decimal] = None
    cv_comments: Optional[str] = None
    diplomes_certificats_score: Optional[Decimal] = None
    diplomes_certificats_comments: Optional[str] = None
    lettre_motivation_score: Optional[Decimal] = None
    lettre_motivation_comments: Optional[str] = None
    documentary_score: Optional[Decimal] = None
    metier_score: Optional[Decimal] = None
    metier_comments: Optional[str] = None
    metier_notes: Optional[str] = None
    paradigme_score: Optional[Decimal] = None
    paradigme_comments: Optional[str] = None
    paradigme_notes: Optional[str] = None
    talent_score: Optional[Decimal] = None
    talent_comments: Optional[str] = None
    talent_notes: Optional[str] = None
    mtp_score: Optional[Decimal] = None
    interview_metier_score: Optional[Decimal] = None
    interview_metier_comments: Optional[str] = None
    interview_paradigme_score: Optional[Decimal] = None
    interview_paradigme_comments: Optional[str] = None
    interview_talent_score: Optional[Decimal] = None
    interview_talent_comments: Optional[str] = None
    interview_score: Optional[Decimal] = None
    interview_date: Optional[datetime] = None
    gap_competence_score: Optional[Decimal] = None
    gap_competence_comments: Optional[str] = None
    adherence_metier: Optional[bool] = None
    adherence_paradigme: Optional[bool] = None
    adherence_talent: Optional[bool] = None
    overall_score: Optional[Decimal] = None
    total_score: Optional[Decimal] = None
    general_summary: Optional[str] = None

class Protocol1EvaluationResponse(Protocol1EvaluationBase):
    """
    Schéma de réponse pour une évaluation Protocol 1 avec métadonnées.
    """
    id: UUID = Field(..., description="ID unique de l'évaluation")
    application_id: UUID = Field(..., description="ID de la candidature évaluée")
    evaluator_id: Optional[UUID] = Field(None, description="ID de l'évaluateur")
    created_at: datetime = Field(..., description="Date de création de l'évaluation")
    updated_at: datetime = Field(..., description="Date de dernière modification")
    
    model_config = {
        "from_attributes": True
    }

class Protocol2EvaluationBase(BaseModel):
    """
    Schéma de base pour l'évaluation Protocol 2 (Candidats INTERNES).
    
    **Protocole spécifique employés SEEG**:
    1. QCM Métier/Rôle (50%) : Test connaissances métier
    2. QCM CODIR (50%) : Test vision stratégique et leadership
    3. Entretien complémentaire (optionnel)
    4. Visite physique (optionnel)
    5. Gap analysis (identification besoins formation)
    
    **Grille de notation**: /20 pour chaque QCM
    **Score de passage**: 10/20 minimum
    """
    completed: bool = Field(False, description="Évaluation complète")
    interview_completed: bool = Field(False, description="Entretien effectué")
    physical_visit: bool = Field(False, description="Visite physique effectuée")
    skills_gap_assessed: bool = Field(False, description="Gap de compétences évalué")
    job_sheet_created: bool = Field(False, description="Fiche de poste créée")
    qcm_role_completed: bool = Field(False, description="QCM métier/rôle complété")
    qcm_codir_completed: bool = Field(False, description="QCM CODIR (direction) complété")
    
    # ========== SCORES QCM ==========
    qcm_role_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score QCM métier/rôle /{SCORE_MAX}")
    qcm_codir_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score QCM CODIR /{SCORE_MAX}")
    overall_score: Optional[Decimal] = Field(None, ge=SCORE_MIN, le=SCORE_MAX, description=f"Score global final /{SCORE_MAX}")
    
    # ========== NOTES ==========
    interview_notes: Optional[str] = Field(None, description="Notes de l'entretien")
    visit_notes: Optional[str] = Field(None, description="Notes de la visite physique")
    skills_gap_notes: Optional[str] = Field(None, description="Notes sur le gap de compétences")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Évaluation Protocol 2 complète (candidat interne)",
                    "value": {
                        "completed": True,
                        "qcm_role_completed": True,
                        "qcm_codir_completed": True,
                        "interview_completed": True,
                        "skills_gap_assessed": True,
                        "qcm_role_score": 17,
                        "qcm_codir_score": 16,
                        "overall_score": 16.5,
                        "interview_notes": "Candidat motivé, excellente connaissance de l'entreprise",
                        "skills_gap_notes": "Formation Azure DevOps recommandée"
                    }
                }
            ]
        }

class Protocol2EvaluationCreate(Protocol2EvaluationBase):
    """
    Schéma pour créer une évaluation Protocol 2.
    
    Requiert l'ID de la candidature et de l'évaluateur.
    """
    application_id: UUID = Field(..., description="ID de la candidature à évaluer")
    evaluator_id: UUID = Field(..., description="ID du recruteur évaluateur")

    model_config = {
        "json_schema_extra": {
            "example": {
                "application_id": "724f8672-e3a4-4fa1-9856-06ac455bf518",
                "evaluator_id": "770e8400-e29b-41d4-a716-446655440000",
                "qcm_role_completed": True,
                "qcm_codir_completed": True,
                "qcm_role_score": 17,
                "qcm_codir_score": 16
            }
        }
    }

class Protocol2EvaluationUpdate(BaseModel):
    completed: Optional[bool] = None
    interview_completed: Optional[bool] = None
    physical_visit: Optional[bool] = None
    skills_gap_assessed: Optional[bool] = None
    job_sheet_created: Optional[bool] = None
    qcm_role_completed: Optional[bool] = None
    qcm_codir_completed: Optional[bool] = None
    qcm_role_score: Optional[Decimal] = None
    qcm_codir_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    interview_notes: Optional[str] = None
    visit_notes: Optional[str] = None
    skills_gap_notes: Optional[str] = None

class Protocol2EvaluationResponse(Protocol2EvaluationBase):
    """
    Schéma de réponse pour une évaluation Protocol 2 avec métadonnées.
    """
    id: UUID = Field(..., description="ID unique de l'évaluation")
    application_id: UUID = Field(..., description="ID de la candidature évaluée")
    evaluator_id: Optional[UUID] = Field(None, description="ID de l'évaluateur")
    created_at: datetime = Field(..., description="Date de création de l'évaluation")
    updated_at: datetime = Field(..., description="Date de dernière modification")
    
    model_config = {
        "from_attributes": True
    }
