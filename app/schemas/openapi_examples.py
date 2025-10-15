"""
Exemples OpenAPI pour la documentation Swagger
"""

# ============================================================================
# USER EXAMPLES
# ============================================================================

USER_WITH_PROFILE_EXAMPLE = {
    "id": "bf0c73bd-09e0-4aad-afaa-94b16901e916",
    "email": "candidate@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "role": "candidate",
    "phone": "+24177012345",
    "date_of_birth": "1990-05-15",
    "sexe": "M",
    "matricule": 12345,
    "email_verified": True,
    "last_login": "2025-10-15T10:30:00Z",
    "is_active": True,
    "is_internal_candidate": True,
    "adresse": "Libreville, Gabon",
    "candidate_status": "actif",
    "statut": "actif",
    "poste_actuel": "Développeur Senior",
    "annees_experience": 5,
    "no_seeg_email": False,
    "created_at": "2025-01-10T08:00:00Z",
    "updated_at": "2025-10-15T10:30:00Z",
    "candidate_profile": {
        "id": "profile-uuid",
        "user_id": "bf0c73bd-09e0-4aad-afaa-94b16901e916",
        "years_experience": 5,
        "current_position": "Développeur Senior",
        "availability": "Immédiate",
        "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "expected_salary_min": 800000,
        "expected_salary_max": 1200000,
        "address": "Libreville, Gabon",
        "linkedin_url": "https://linkedin.com/in/jeandupont",
        "portfolio_url": "https://portfolio.jeandupont.com",
        "created_at": "2025-01-10T08:00:00Z",
        "updated_at": "2025-10-15T10:30:00Z"
    }
}

USER_WITHOUT_PROFILE_EXAMPLE = {
    **{k: v for k, v in USER_WITH_PROFILE_EXAMPLE.items() if k != "candidate_profile"},
    "candidate_profile": None
}

USER_LIST_RESPONSE_EXAMPLE = {
    "success": True,
    "message": "5 utilisateur(s) récupéré(s)",
    "data": [
        {
            "id": "user-1-uuid",
            "email": "admin@seeg-gabon.com",
            "first_name": "Admin",
            "last_name": "SEEG",
            "role": "admin",
            "matricule": 1001,
            "statut": "actif",
            "is_active": True
        },
        {
            "id": "user-2-uuid",
            "email": "recruiter@seeg-gabon.com",
            "first_name": "Marie",
            "last_name": "RECRUTEUSE",
            "role": "recruiter",
            "matricule": 1002,
            "statut": "actif",
            "is_active": True
        }
    ],
    "total": 5,
    "page": 1,
    "per_page": 100
}

# ============================================================================
# AUTH EXAMPLES
# ============================================================================

LOGIN_REQUEST_JSON_EXAMPLE = {
    "email": "candidate@example.com",
    "password": "MotdepasseFort123!"
}

LOGIN_REQUEST_FORM_EXAMPLE = {
    "username": "candidate@example.com",
    "password": "MotdepasseFort123!"
}

LOGIN_RESPONSE_EXAMPLE = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": USER_WITH_PROFILE_EXAMPLE
}

SIGNUP_REQUEST_EXAMPLE = {
    "email": "newcandidate@example.com",
    "password": "MotdepasseFort123!",
    "first_name": "Pierre",
    "last_name": "Martin",
    "phone": "+24177012345",
    "date_of_birth": "1995-03-20",
    "sexe": "M",
    "matricule": 12346,
    "is_internal_candidate": False
}

SIGNUP_RESPONSE_EXAMPLE = {
    **USER_WITHOUT_PROFILE_EXAMPLE,
    "email": "newcandidate@example.com",
    "first_name": "Pierre",
    "last_name": "Martin"
}

# ============================================================================
# APPLICATION EXAMPLES
# ============================================================================

APPLICATION_DETAIL_EXAMPLE = {
    "id": "app-uuid",
    "candidate_id": "candidate-uuid",
    "job_offer_id": "job-uuid",
    "status": "pending",
    "cover_letter": "Je suis très motivé pour ce poste...",
    "reference_contacts": ["contact1@example.com"],
    "availability_start": "2025-11-01",
    "has_been_manager": True,
    "ref_entreprise": "Entreprise ABC",
    "ref_fullname": "Référent XYZ",
    "ref_mail": "referent@abc.com",
    "ref_contact": "+24177011111",
    "mtp_answers": {
        "reponses_metier": ["Réponse 1", "Réponse 2"],
        "reponses_talent": ["Réponse A", "Réponse B"],
        "reponses_paradigme": ["Réponse I", "Réponse II"]
    },
    "created_at": "2025-10-15T09:00:00Z",
    "updated_at": "2025-10-15T09:00:00Z",
    "candidate": {
        "id": "candidate-uuid",
        "email": "candidate@example.com",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+24177012345",
        "matricule": 12345
    },
    "job_offer": {
        "id": "job-uuid",
        "title": "Développeur Full Stack",
        "department": "IT",
        "status": "active",
        "offer_status": "tous"
    }
}

APPLICATION_LIST_RESPONSE_EXAMPLE = {
    "success": True,
    "message": "Candidatures récupérées",
    "data": [APPLICATION_DETAIL_EXAMPLE],
    "total": 1,
    "page": 1,
    "per_page": 100
}

# ============================================================================
# JOB OFFER EXAMPLES
# ============================================================================

JOB_OFFER_DETAIL_EXAMPLE = {
    "id": "job-uuid",
    "title": "Développeur Full Stack Senior",
    "department": "IT",
    "location": "Libreville",
    "contract_type": "CDI",
    "description": "Nous recherchons un développeur...",
    "requirements": ["5 ans d'expérience", "Python", "React"],
    "responsibilities": ["Développer des applications", "Maintenir le code"],
    "benefits": ["Assurance santé", "Formation continue"],
    "status": "active",
    "offer_status": "tous",
    "salary_min": 800000,
    "salary_max": 1200000,
    "questions_mtp": {
        "questions_metier": ["Question métier 1", "Question métier 2"],
        "questions_talent": ["Question talent 1", "Question talent 2"],
        "questions_paradigme": ["Question paradigme 1", "Question paradigme 2"]
    },
    "created_at": "2025-10-01T08:00:00Z",
    "updated_at": "2025-10-15T10:00:00Z"
}

# ============================================================================
# ACCESS REQUEST EXAMPLES
# ============================================================================

ACCESS_REQUEST_EXAMPLE = {
    "id": "request-uuid",
    "user_id": "user-uuid",
    "email": "internal@example.com",
    "first_name": "Paul",
    "last_name": "Candidate",
    "phone": "+24177012345",
    "matricule": "12347",
    "request_type": "internal_no_seeg_email",
    "status": "pending",
    "rejection_reason": None,
    "viewed": False,
    "created_at": "2025-10-15T08:00:00Z",
    "reviewed_at": None,
    "reviewed_by": None,
    "updated_at": None
}

ACCESS_REQUEST_LIST_RESPONSE_EXAMPLE = {
    "success": True,
    "message": "Demandes d'accès récupérées",
    "data": {
        "requests": [ACCESS_REQUEST_EXAMPLE],
        "total": 1,
        "pending_count": 1,
        "unviewed_count": 1
    }
}

