"""
Utilitaires pour sérialiser les candidatures avec leurs relations
Best Practice: Séparation des responsabilités (SRP)
"""
import structlog
from typing import Dict, Any
from app.schemas.application_detailed import (
    ApplicationDetailed,
    CandidateInfo,
    CandidateProfileInfo,
    JobOfferInfo
)

logger = structlog.get_logger(__name__)


def serialize_application_with_relations(
    application: Any,
    include_candidate: bool = True,
    include_job_offer: bool = True
) -> Dict[str, Any]:
    """
    Sérialise une candidature avec ses relations de manière robuste
    
    Args:
        application: Instance SQLAlchemy Application avec relations chargées
        include_candidate: Inclure les infos du candidat (défaut: True)
        include_job_offer: Inclure les infos de l'offre (défaut: True)
        
    Returns:
        Dict avec toutes les données sérialisées
        
    Best Practices:
        - Gestion explicite des erreurs
        - Accès défensif aux attributs (getattr)
        - Logging détaillé pour debugging
        - Fail-safe: retourne au minimum les données de base
    """
    try:
        logger.info("🚀 Début sérialisation application",
                   application_id=str(application.id),
                   include_candidate=include_candidate,
                   include_job_offer=include_job_offer)
        
        # Données de base de la candidature (toujours présentes)
        result = {
            'id': str(application.id),
            'candidate_id': str(application.candidate_id),
            'job_offer_id': str(application.job_offer_id),
            'status': str(application.status),
            'reference_contacts': application.reference_contacts,
            'availability_start': application.availability_start.isoformat() if (application.availability_start is not None) else None,  # type: ignore
            'has_been_manager': bool(application.has_been_manager),
            'ref_entreprise': application.ref_entreprise,
            'ref_fullname': application.ref_fullname,
            'ref_mail': application.ref_mail,
            'ref_contact': application.ref_contact,
            'mtp_answers': application.mtp_answers,
            'created_at': application.created_at.isoformat() if (application.created_at is not None) else None,  # type: ignore
            'updated_at': application.updated_at.isoformat() if (application.updated_at is not None) else None,  # type: ignore
        }
        
        # Enrichir avec les informations du candidat (si demandé)
        if include_candidate:
            candidate = getattr(application, 'candidate', None)
            
            if candidate is not None:
                logger.debug("Sérialisation candidat",
                           candidate_id=str(candidate.id))
                
                candidate_data = {
                    'id': str(candidate.id),
                    'email': str(candidate.email),
                    'first_name': str(candidate.first_name),
                    'last_name': str(candidate.last_name),
                    'phone': str(candidate.phone) if candidate.phone else None,
                    'date_of_birth': str(candidate.date_of_birth) if getattr(candidate, 'date_of_birth', None) else None,
                    'sexe': str(candidate.sexe) if getattr(candidate, 'sexe', None) else None,
                    'role': str(candidate.role),
                    'is_active': bool(candidate.is_active) if hasattr(candidate, 'is_active') else True,
                    'candidate_status': str(candidate.candidate_status) if getattr(candidate, 'candidate_status', None) else None,
                    'created_at': candidate.created_at.isoformat() if hasattr(candidate, 'created_at') and candidate.created_at else None,
                }
                
                # Ajouter le profil candidat si disponible
                profile = getattr(candidate, 'candidate_profile', None)
                if profile is not None:
                    logger.debug("Sérialisation profil candidat",
                               profile_id=str(profile.id) if hasattr(profile, 'id') else None)
                    
                    candidate_data['candidate_profile'] = {
                        'id': str(profile.id) if hasattr(profile, 'id') else None,
                        'years_experience': profile.years_experience if hasattr(profile, 'years_experience') else None,
                        'current_position': profile.current_position if hasattr(profile, 'current_position') else None,
                        'current_department': profile.current_department if hasattr(profile, 'current_department') else None,
                        'availability': profile.availability if hasattr(profile, 'availability') else None,
                        'skills': profile.skills if hasattr(profile, 'skills') else None,
                        'education': profile.education if hasattr(profile, 'education') else None,
                        'expected_salary_min': profile.expected_salary_min if hasattr(profile, 'expected_salary_min') else None,
                        'expected_salary_max': profile.expected_salary_max if hasattr(profile, 'expected_salary_max') else None,
                        'linkedin_url': profile.linkedin_url if hasattr(profile, 'linkedin_url') else None,
                        'portfolio_url': profile.portfolio_url if hasattr(profile, 'portfolio_url') else None,
                    }
                
                result['candidate'] = candidate_data
            else:
                logger.debug("Relation candidate non chargée",
                           application_id=str(application.id))
        
        # Enrichir avec les informations de l'offre (si demandé)
        if include_job_offer:
            job_offer = getattr(application, 'job_offer', None)
            
            if job_offer is not None:
                logger.debug("Sérialisation job_offer",
                           job_offer_id=str(job_offer.id))
                
                result['job_offer'] = {
                    'id': str(job_offer.id),
                    'title': str(job_offer.title),
                    'department': str(job_offer.department) if getattr(job_offer, 'department', None) else None,
                    'location': str(job_offer.location) if hasattr(job_offer, 'location') else None,
                    'contract_type': str(job_offer.contract_type) if hasattr(job_offer, 'contract_type') else None,
                    'description': str(job_offer.description) if hasattr(job_offer, 'description') else None,
                    'salary_min': job_offer.salary_min if hasattr(job_offer, 'salary_min') else None,
                    'salary_max': job_offer.salary_max if hasattr(job_offer, 'salary_max') else None,
                    'status': str(job_offer.status) if hasattr(job_offer, 'status') else None,
                }
            else:
                logger.debug("Relation job_offer non chargée",
                           application_id=str(application.id))
        
        logger.debug("Sérialisation application terminée",
                   application_id=str(application.id),
                   has_candidate=('candidate' in result),
                   has_job_offer=('job_offer' in result))
        
        return result
        
    except Exception as e:
        logger.error("Erreur sérialisation application",
                    application_id=str(application.id) if hasattr(application, 'id') else None,
                    error=str(e),
                    exc_info=True)
        # Fail-safe: retourner au moins les données de base
        return {
            'id': str(application.id),
            'candidate_id': str(application.candidate_id),
            'job_offer_id': str(application.job_offer_id),
            'status': str(application.status),
            'error': 'Erreur lors de la sérialisation des relations'
        }

