"""
Schémas Pydantic pour les offres d'emploi
=========================================
Architecture: Type-Safe + Validation MTP + Documentation Complète

Schémas principaux:
- JobOfferBase/Response: Offre d'emploi avec questions MTP
- JobOfferCreate/Update: Création et modification d'offres
- Gestion questions MTP (Métier, Talent, Paradigme)
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ============================================================================
# CONSTANTES - Types de contrats et statuts d'offres
# ============================================================================

# Types de contrats
CONTRACT_TYPE_CDI = "CDI"              # Contrat à Durée Indéterminée
CONTRACT_TYPE_CDD = "CDD"              # Contrat à Durée Déterminée
CONTRACT_TYPE_STAGE = "Stage"          # Stage
CONTRACT_TYPE_ALTERNANCE = "Alternance"  # Alternance
CONTRACT_TYPE_FREELANCE = "Freelance"  # Freelance/Consultant
ALLOWED_CONTRACT_TYPES = {
    CONTRACT_TYPE_CDI,
    CONTRACT_TYPE_CDD,
    CONTRACT_TYPE_STAGE,
    CONTRACT_TYPE_ALTERNANCE,
    CONTRACT_TYPE_FREELANCE
}

# Statuts d'offres (visibilité)
OFFER_STATUS_ALL = "tous"      # Visible par internes ET externes
OFFER_STATUS_INTERNAL = "interne"  # Réservée aux employés SEEG uniquement
OFFER_STATUS_EXTERNAL = "externe"  # Réservée aux candidats externes uniquement
ALLOWED_OFFER_STATUS = {OFFER_STATUS_ALL, OFFER_STATUS_INTERNAL, OFFER_STATUS_EXTERNAL}

# Statuts d'activation
JOB_STATUS_ACTIVE = "active"        # Offre publiée et visible
JOB_STATUS_DRAFT = "draft"          # Brouillon non publié
JOB_STATUS_CLOSED = "closed"        # Offre fermée/pourvue
JOB_STATUS_ARCHIVED = "archived"    # Offre archivée
ALLOWED_JOB_STATUS = {JOB_STATUS_ACTIVE, JOB_STATUS_DRAFT, JOB_STATUS_CLOSED, JOB_STATUS_ARCHIVED}

# Limites questions MTP
MTP_MAX_QUESTIONS_METIER = 7   # Maximum questions métier
MTP_MAX_QUESTIONS_TALENT = 3   # Maximum questions talent
MTP_MAX_QUESTIONS_PARADIGME = 3  # Maximum questions paradigme

class JobOfferBase(BaseModel):
    """
    Schéma de base pour une offre d'emploi.
    
    Contient:
    - Informations de base (titre, description, localisation)
    - Conditions d'emploi (contrat, salaire, département)
    - Questions MTP pour évaluation candidats
    - Statuts et visibilité
    """
    title: str = Field(..., min_length=5, max_length=200, description="Titre du poste")
    description: str = Field(..., min_length=20, description="Description détaillée du poste")
    location: str = Field(..., min_length=2, max_length=100, description="Localisation (ville, pays)")
    contract_type: str = Field(..., description=f"Type de contrat: {', '.join(ALLOWED_CONTRACT_TYPES)}")
    department: Optional[str] = Field(None, max_length=100, description="Département SEEG concerné")
    salary_min: Optional[int] = Field(None, ge=0, description="Salaire minimum (FCFA)")
    salary_max: Optional[int] = Field(None, ge=0, description="Salaire maximum (FCFA)")
    requirements: Optional[List[str]] = Field(None, description="Compétences et qualifications requises")
    benefits: Optional[List[str]] = Field(None, description="Avantages offerts (assurance, transport, etc.)")
    responsibilities: Optional[List[str]] = Field(None, description="Responsabilités principales du poste")
    status: str = Field(JOB_STATUS_ACTIVE, description=f"Statut: {', '.join(ALLOWED_JOB_STATUS)}")
    
    # Statut de visibilité de l'offre
    offer_status: str = Field(
        default=OFFER_STATUS_ALL,
        description=f"Visibilité: '{OFFER_STATUS_ALL}' (tous), '{OFFER_STATUS_INTERNAL}' (SEEG uniquement), '{OFFER_STATUS_EXTERNAL}' (externes uniquement)"
    )
    
    application_deadline: Optional[datetime] = Field(None, description="Date limite de candidature")
    date_limite: Optional[datetime] = Field(None, description="Date limite (alias)")
    reporting_line: Optional[str] = Field(None, description="Ligne hiérarchique / Supérieur direct")
    salary_note: Optional[str] = Field(None, description="Note sur la rémunération (à négocier, avantages, etc.)")
    start_date: Optional[datetime] = Field(None, description="Date de prise de poste souhaitée")
    profile: Optional[str] = Field(None, description="Profil recherché détaillé")
    categorie_metier: Optional[str] = Field(None, description="Catégorie métier SEEG")
    job_grade: Optional[str] = Field(None, description="Grade du poste")
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = Field(
        None,
        description=f"Questions MTP structurées: {{questions_metier: [...max {MTP_MAX_QUESTIONS_METIER}], questions_talent: [...max {MTP_MAX_QUESTIONS_TALENT}], questions_paradigme: [...max {MTP_MAX_QUESTIONS_PARADIGME}]}}"
    )
    
    @field_validator('questions_mtp')
    @classmethod
    def validate_mtp_questions(cls, v):
        """
        Valide que les questions MTP respectent les limites.
        
        Limites:
        - Métier: Maximum 7 questions
        - Talent: Maximum 3 questions
        - Paradigme: Maximum 3 questions
        """
        if v is None:
            return v
        
        # Vérifier les limites
        if 'questions_metier' in v and len(v['questions_metier']) > MTP_MAX_QUESTIONS_METIER:
            raise ValueError(f"Maximum {MTP_MAX_QUESTIONS_METIER} questions métier autorisées")
        if 'questions_talent' in v and len(v['questions_talent']) > MTP_MAX_QUESTIONS_TALENT:
            raise ValueError(f"Maximum {MTP_MAX_QUESTIONS_TALENT} questions talent autorisées")
        if 'questions_paradigme' in v and len(v['questions_paradigme']) > MTP_MAX_QUESTIONS_PARADIGME:
            raise ValueError(f"Maximum {MTP_MAX_QUESTIONS_PARADIGME} questions paradigme autorisées")
        
        return v

class JobOfferCreate(JobOfferBase):
    """
    Schéma pour créer une offre d'emploi.
    
    Le recruiter_id est automatiquement extrait du token JWT (non fourni dans le payload).
    """
    recruiter_id: Optional[UUID] = Field(None, description="ID du recruteur (auto-rempli depuis JWT)")
    
    # Champs legacy pour compatibilité avec le frontend (format string)
    question_metier: Optional[str] = Field(None, exclude=True, description="[LEGACY] Questions métier en texte multiligne")
    question_talent: Optional[str] = Field(None, exclude=True, description="[LEGACY] Questions talent en texte multiligne")
    question_paradigme: Optional[str] = Field(None, exclude=True, description="[LEGACY] Questions paradigme en texte multiligne")
    
    @model_validator(mode='after')
    def transform_mtp_questions(self):
        """
        Transformer les questions MTP du format legacy (strings) au format structuré (Dict[str, List[str]]).
        
        **Règles de transformation**:
        - Si questions_mtp existe déjà → le garder tel quel
        - Sinon, si question_* existent → les transformer en questions_mtp structuré
        - Chaque question est séparée par un retour à la ligne (\\n)
        
        **Pattern**: Backward Compatibility avec migration progressive vers nouveau format
        """
        # Si questions_mtp est déjà fourni, ne rien faire
        if self.questions_mtp is not None:
            return self
        
        # Sinon, construire questions_mtp depuis les champs legacy
        questions_dict = {}
        
        # Transformer question_metier
        if self.question_metier:
            # Séparer les questions par retour à la ligne et nettoyer
            questions = [q.strip() for q in self.question_metier.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_metier'] = questions
        
        # Transformer question_talent
        if self.question_talent:
            questions = [q.strip() for q in self.question_talent.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_talent'] = questions
        
        # Transformer question_paradigme
        if self.question_paradigme:
            questions = [q.strip() for q in self.question_paradigme.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_paradigme'] = questions
        
        # Assigner le dictionnaire structuré si non vide
        if questions_dict:
            self.questions_mtp = questions_dict
        
        return self
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Offre INTERNE - Ingénieur DevOps (SEEG uniquement)",
                    "value": {
                        "title": "Ingénieur DevOps Senior",
                        "description": "Nous recherchons un Ingénieur DevOps pour moderniser notre infrastructure cloud Azure et automatiser nos déploiements.",
                        "location": "Libreville, Gabon",
                        "contract_type": "CDI",
                        "department": "Direction des Systèmes d'Information",
                        "salary_min": 1500000,
                        "salary_max": 2500000,
                        "requirements": [
                            "Maîtrise d'Azure (VMs, App Services, AKS)",
                            "Expérience avec Kubernetes et Docker",
                            "Connaissance des outils CI/CD (Azure DevOps, GitHub Actions)",
                            "Minimum 5 ans d'expérience"
                        ],
                        "benefits": [
                            "Assurance santé famille",
                            "Véhicule de fonction",
                            "Formation continue Azure",
                            "Prime de performance"
                        ],
                        "responsibilities": [
                            "Gestion infrastructure cloud Azure",
                            "Automatisation des déploiements",
                            "Monitoring et optimisation",
                            "Support équipes dev"
                        ],
                        "status": "active",
                        "offer_status": "interne",
                        "reporting_line": "Directeur SI",
                        "salary_note": "Négociable selon expérience + avantages",
                        "questions_mtp": {
                            "questions_metier": [
                                "Décrivez votre expérience avec Kubernetes en production",
                                "Quels outils CI/CD avez-vous utilisés et pourquoi ?",
                                "Comment gérez-vous la haute disponibilité dans le cloud ?"
                            ],
                            "questions_talent": [
                                "Comment gérez-vous une panne critique en production ?",
                                "Comment vous tenez-vous à jour technologiquement ?"
                            ],
                            "questions_paradigme": [
                                "Quel est votre vision de l'automatisation dans une entreprise ?"
                            ]
                        }
                    }
                },
                {
                    "description": "Offre EXTERNE - Développeur Full Stack (candidats externes)",
                    "value": {
                        "title": "Développeur Full Stack JavaScript",
                        "description": "Rejoignez notre équipe digitale pour développer nos applications web modernes.",
                        "location": "Libreville, Gabon",
                        "contract_type": "CDI",
                        "department": "Digital",
                        "salary_min": 800000,
                        "salary_max": 1200000,
                        "requirements": [
                            "React.js et Node.js",
                            "PostgreSQL",
                            "APIs REST",
                            "Minimum 3 ans d'expérience"
                        ],
                        "benefits": ["Assurance santé", "Formation"],
                        "status": "active",
                        "offer_status": "externe",
                        "questions_mtp": {
                            "questions_metier": [
                                "Décrivez un projet React complexe que vous avez réalisé",
                                "Comment optimisez-vous les performances d'une API Node.js ?"
                            ],
                            "questions_talent": [
                                "Comment travaillez-vous en équipe agile ?"
                            ],
                            "questions_paradigme": [
                                "Quelle est votre vision du développement web moderne ?"
                            ]
                        }
                    }
                },
                {
                    "description": "Offre PUBLIQUE - Stage IT (tous candidats)",
                    "value": {
                        "title": "Stagiaire Développement Web",
                        "description": "Stage de 6 mois pour découvrir le développement web professionnel.",
                        "location": "Libreville, Gabon",
                        "contract_type": "Stage",
                        "department": "IT",
                        "status": "active",
                        "offer_status": "tous",
                        "salary_note": "Gratification de stage selon la loi",
                        "questions_mtp": None
                    }
                }
            ]
        }

class JobOfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    status: Optional[str] = None
    offer_status: Optional[str] = Field(
        None,
        description="Visibilité de l'offre: 'tous', 'interne', 'externe'"
    )
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = None
    
    # Champs legacy pour compatibilité avec le frontend (format string)
    question_metier: Optional[str] = Field(None, exclude=True)
    question_talent: Optional[str] = Field(None, exclude=True)
    question_paradigme: Optional[str] = Field(None, exclude=True)
    
    @model_validator(mode='after')
    def transform_mtp_questions(self):
        """
        Transformer les questions MTP du format legacy (strings) au format structuré (Dict[str, List[str]])
        
        Règle de transformation:
        - Si questions_mtp existe déjà → le garder tel quel
        - Sinon, si question_* existent → les transformer en questions_mtp structuré
        - Chaque question est séparée par un retour à la ligne (\n)
        """
        # Si questions_mtp est déjà fourni, ne rien faire
        if self.questions_mtp is not None:
            return self
        
        # Sinon, construire questions_mtp depuis les champs legacy
        questions_dict = {}
        
        # Transformer question_metier
        if self.question_metier:
            questions = [q.strip() for q in self.question_metier.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_metier'] = questions
        
        # Transformer question_talent
        if self.question_talent:
            questions = [q.strip() for q in self.question_talent.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_talent'] = questions
        
        # Transformer question_paradigme
        if self.question_paradigme:
            questions = [q.strip() for q in self.question_paradigme.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_paradigme'] = questions
        
        # Assigner le dictionnaire structuré si non vide
        if questions_dict:
            self.questions_mtp = questions_dict
        
        return self

class JobOfferResponse(JobOfferBase):
    """
    Schéma de réponse pour une offre d'emploi avec métadonnées.
    
    Inclut les IDs et timestamps système.
    """
    id: UUID = Field(..., description="ID unique de l'offre")
    recruiter_id: UUID = Field(..., description="ID du recruteur créateur")
    created_at: datetime = Field(..., description="Date de création de l'offre")
    updated_at: datetime = Field(..., description="Date de dernière modification")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1b0f63c6-db77-4ed7-a424-aa2342a4fc43",
                "recruiter_id": "770e8400-e29b-41d4-a716-446655440000",
                "title": "Ingénieur DevOps Senior",
                "description": "Nous recherchons un Ingénieur DevOps expérimenté...",
                "location": "Libreville, Gabon",
                "contract_type": "CDI",
                "department": "Direction des Systèmes d'Information",
                "salary_min": 1500000,
                "salary_max": 2500000,
                "requirements": [
                    "Maîtrise d'Azure",
                    "Kubernetes et Docker",
                    "5+ ans d'expérience"
                ],
                "benefits": [
                    "Assurance santé famille",
                    "Véhicule de fonction"
                ],
                "responsibilities": [
                    "Gestion infrastructure cloud",
                    "Automatisation CI/CD"
                ],
                "status": "active",
                "offer_status": "interne",
                "questions_mtp": {
                    "questions_metier": [
                        "Décrivez votre expérience avec Kubernetes",
                        "Quels outils CI/CD maîtrisez-vous ?"
                    ],
                    "questions_talent": [
                        "Comment gérez-vous une crise en production ?"
                    ],
                    "questions_paradigme": [
                        "Votre vision de l'automatisation ?"
                    ]
                },
                "created_at": "2024-10-01T10:00:00Z",
                "updated_at": "2024-10-17T15:30:00Z"
            }
        }


# ============================================================================
# SCHÉMAS PUBLICS (sans authentification)
# ============================================================================

class JobOfferPublicResponse(BaseModel):
    """Schéma de réponse publique pour les offres (sans infos sensibles)"""
    id: UUID
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_note: Optional[str] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    offer_status: str = Field(description="Visibilité: 'tous', 'interne', 'externe'")
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobOfferDetailPublicResponse(BaseModel):
    """Schéma de réponse détaillée publique pour une offre (avec questions MTP)"""
    id: UUID
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_note: Optional[str] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    offer_status: str = Field(description="Visibilité: 'tous', 'interne', 'externe'")
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP (si disponibles)
    questions_mtp: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Questions MTP au format JSON"
    )
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
