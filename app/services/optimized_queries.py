"""
Services optimisés pour les requêtes complexes avec de meilleures relations
"""
import structlog
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from uuid import UUID
from datetime import datetime, timedelta

from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application, ApplicationDocument
from app.models.candidate_profile import CandidateProfile
from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.models.interview import InterviewSlot
from app.models.notification import Notification

logger = structlog.get_logger(__name__)

class OptimizedQueryService:
    """Service pour les requêtes optimisées avec de meilleures relations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_applications_with_full_data(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status_filter: Optional[str] = None,
        job_offer_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        include_documents: bool = True,
        include_evaluations: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Récupérer les candidatures avec toutes les données liées en une seule requête
        """
        try:
            # Construction de la requête de base
            query = select(Application)
            count_query = select(func.count(Application.id))
            
            # Préchargement des relations
            if include_documents:
                query = query.options(selectinload(Application.documents))
            
            if include_evaluations:
                query = query.options(
                    selectinload(Application.protocol1_evaluation),
                    selectinload(Application.protocol2_evaluation)
                )
            
            # Toujours précharger les relations essentielles
            query = query.options(
                joinedload(Application.candidate).selectinload(User.candidate_profile),
                joinedload(Application.job_offer).joinedload(JobOffer.recruiter),
                selectinload(Application.history),
                selectinload(Application.interview_slots),
                selectinload(Application.notifications)
            )
            
            # Appliquer les filtres
            conditions = []
            if status_filter:
                conditions.append(Application.status == status_filter)
            if job_offer_id:
                conditions.append(Application.job_offer_id == UUID(job_offer_id))
            if candidate_id:
                conditions.append(Application.candidate_id == UUID(candidate_id))
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Pagination
            query = query.offset(skip).limit(limit).order_by(desc(Application.created_at))
            
            # Exécution des requêtes
            result = await self.db.execute(query)
            applications = result.unique().scalars().all()
            
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Transformation des données
            applications_data = []
            for app in applications:
                app_data = {
                    'id': str(app.id),
                    'candidate_id': str(app.candidate_id),
                    'job_offer_id': str(app.job_offer_id),
                    'status': app.status,
                    'reference_contacts': app.reference_contacts,
                    'availability_start': app.availability_start.isoformat() if app.availability_start else None,
                    'mtp_answers': app.mtp_answers,
                    'created_at': app.created_at.isoformat(),
                    'updated_at': app.updated_at.isoformat(),
                    
                    # Données du candidat
                    'candidate': {
                        'id': str(app.candidate.id),
                        'first_name': app.candidate.first_name,
                        'last_name': app.candidate.last_name,
                        'email': app.candidate.email,
                        'phone': app.candidate.phone,
                        'date_of_birth': app.candidate.date_of_birth.isoformat() if app.candidate.date_of_birth else None,
                        'profile': {
                            'id': str(app.candidate.candidate_profile.id) if app.candidate.candidate_profile else None,
                            'gender': app.candidate.candidate_profile.gender if app.candidate.candidate_profile else None,
                            'current_position': app.candidate.candidate_profile.current_position if app.candidate.candidate_profile else None,
                            'years_experience': app.candidate.candidate_profile.years_experience if app.candidate.candidate_profile else None,
                            'address': app.candidate.candidate_profile.address if app.candidate.candidate_profile else None,
                            'linkedin_url': app.candidate.candidate_profile.linkedin_url if app.candidate.candidate_profile else None,
                            'portfolio_url': app.candidate.candidate_profile.portfolio_url if app.candidate.candidate_profile else None,
                        } if app.candidate.candidate_profile else None
                    },
                    
                    # Données de l'offre d'emploi
                    'job_offer': {
                        'id': str(app.job_offer.id),
                        'title': app.job_offer.title,
                        'description': app.job_offer.description,
                        'location': app.job_offer.location,
                        'contract_type': app.job_offer.contract_type,
                        'department': app.job_offer.department,
                        'salary_min': app.job_offer.salary_min,
                        'salary_max': app.job_offer.salary_max,
                        'status': app.job_offer.status,
                        'application_deadline': app.job_offer.application_deadline.isoformat() if app.job_offer.application_deadline else None,
                        'date_limite': app.job_offer.date_limite.isoformat() if app.job_offer.date_limite else None,
                        'recruiter': {
                            'id': str(app.job_offer.recruiter.id),
                            'first_name': app.job_offer.recruiter.first_name,
                            'last_name': app.job_offer.recruiter.last_name,
                            'email': app.job_offer.recruiter.email,
                        }
                    },
                    
                    # Documents
                    'documents': [
                        {
                            'id': str(doc.id),
                            'document_type': doc.document_type,
                            'file_name': doc.file_name,
                            'file_size': doc.file_size,
                            'file_type': doc.file_type,
                            'uploaded_at': doc.uploaded_at.isoformat()
                        } for doc in app.documents
                    ] if include_documents else [],
                    
                    # Évaluations
                    'evaluations': {
                        'protocol1': {
                            'id': str(app.protocol1_evaluation.id) if app.protocol1_evaluation else None,
                            'status': app.protocol1_evaluation.status if app.protocol1_evaluation else None,
                            'completed': app.protocol1_evaluation.completed if app.protocol1_evaluation else None,
                            'overall_score': float(app.protocol1_evaluation.overall_score) if app.protocol1_evaluation and app.protocol1_evaluation.overall_score else None,
                        } if app.protocol1_evaluation else None,
                        'protocol2': {
                            'id': str(app.protocol2_evaluation.id) if app.protocol2_evaluation else None,
                            'completed': app.protocol2_evaluation.completed if app.protocol2_evaluation else None,
                            'overall_score': float(app.protocol2_evaluation.overall_score) if app.protocol2_evaluation and app.protocol2_evaluation.overall_score else None,
                        } if app.protocol2_evaluation else None,
                    } if include_evaluations else {},
                    
                    # Historique
                    'history': [
                        {
                            'id': str(h.id),
                            'previous_status': h.previous_status,
                            'new_status': h.new_status,
                            'notes': h.notes,
                            'changed_at': h.changed_at.isoformat(),
                            'changed_by': str(h.changed_by) if h.changed_by else None
                        } for h in app.history
                    ],
                    
                    # Créneaux d'entretien
                    'interview_slots': [
                        {
                            'id': str(slot.id),
                            'candidate_name': slot.candidate_name,
                            'job_title': slot.job_title,
                            'date': slot.date,
                            'time': slot.time,
                            'status': slot.status,
                            'meeting_link': slot.meeting_link,
                            'notes': slot.notes
                        } for slot in app.interview_slots
                    ],
                    
                    # Notifications
                    'notifications': [
                        {
                            'id': str(notif.id),
                            'title': notif.title,
                            'message': notif.message,
                            'type': notif.type,
                            'read': notif.read,
                            'priority': notif.priority,
                            'created_at': notif.created_at.isoformat()
                        } for notif in app.notifications
                    ]
                }
                applications_data.append(app_data)
            
            logger.info("Applications récupérées avec succès", 
                       count=len(applications_data), 
                       total=total_count,
                       filters={'status': status_filter, 'job_offer_id': job_offer_id, 'candidate_id': candidate_id})
            
            return applications_data, total_count
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des candidatures", error=str(e))
            raise
    
    async def get_dashboard_stats_optimized(self, recruiter_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupérer les statistiques du dashboard de manière optimisée
        """
        try:
            stats = {}
            
            # Base query pour les offres d'emploi
            job_query = select(JobOffer)
            if recruiter_id:
                job_query = job_query.where(JobOffer.recruiter_id == UUID(recruiter_id))
            
            # Statistiques des offres d'emploi
            job_result = await self.db.execute(job_query)
            jobs = job_result.scalars().all()
            
            stats['total_jobs'] = len(jobs)
            stats['active_jobs'] = len([j for j in jobs if j.status == 'active'])
            
            # Statistiques des candidatures avec une seule requête
            app_query = select(
                Application.status,
                func.count(Application.id).label('count'),
                func.count(func.distinct(Application.candidate_id)).label('unique_candidates')
            )
            
            if recruiter_id:
                app_query = app_query.join(JobOffer).where(JobOffer.recruiter_id == UUID(recruiter_id))
            
            app_query = app_query.group_by(Application.status)
            
            app_result = await self.db.execute(app_query)
            app_stats = app_result.all()
            
            # Traitement des statistiques
            status_counts = {row.status: row.count for row in app_stats}
            total_applications = sum(status_counts.values())
            unique_candidates = max([row.unique_candidates for row in app_stats], default=0)
            
            stats.update({
                'total_applications': total_applications,
                'unique_candidates': unique_candidates,
                'status_breakdown': status_counts,
                'interviews_scheduled': status_counts.get('incubation', 0),
                'hired': status_counts.get('embauche', 0),
                'rejected': status_counts.get('refuse', 0)
            })
            
            # Statistiques par département
            dept_query = select(
                JobOffer.department,
                func.count(JobOffer.id).label('job_count'),
                func.count(Application.id).label('application_count')
            ).outerjoin(Application).group_by(JobOffer.department)
            
            if recruiter_id:
                dept_query = dept_query.where(JobOffer.recruiter_id == UUID(recruiter_id))
            
            dept_result = await self.db.execute(dept_query)
            dept_stats = dept_result.all()
            
            stats['department_stats'] = [
                {
                    'department': row.department or 'Non spécifié',
                    'job_count': row.job_count,
                    'application_count': row.application_count,
                    'coverage_rate': round((row.application_count / row.job_count * 100) if row.job_count > 0 else 0, 2)
                }
                for row in dept_stats
            ]
            
            # Statistiques de genre (si disponible)
            gender_query = select(
                CandidateProfile.gender,
                func.count(func.distinct(Application.candidate_id)).label('count')
            ).join(User, CandidateProfile.user_id == User.id)\
             .join(Application, Application.candidate_id == User.id)
            
            if recruiter_id:
                gender_query = gender_query.join(JobOffer).where(JobOffer.recruiter_id == UUID(recruiter_id))
            
            gender_query = gender_query.group_by(CandidateProfile.gender)
            
            gender_result = await self.db.execute(gender_query)
            gender_stats = gender_result.all()
            
            total_with_gender = sum(row.count for row in gender_stats)
            if total_with_gender > 0:
                male_count = next((row.count for row in gender_stats if row.gender and row.gender.lower() in ['homme', 'h', 'm', 'masculin']), 0)
                female_count = next((row.count for row in gender_stats if row.gender and row.gender.lower() in ['femme', 'f', 'feminin', 'féminin']), 0)
                
                stats['gender_distribution'] = {
                    'male_percent': round((male_count / total_with_gender) * 100, 2),
                    'female_percent': round((female_count / total_with_gender) * 100, 2),
                    'total_with_gender': total_with_gender
                }
            
            logger.info("Statistiques dashboard récupérées", recruiter_id=recruiter_id, stats=stats)
            return stats
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des statistiques", error=str(e))
            raise
    
    async def get_candidate_applications_optimized(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Récupérer les candidatures d'un candidat avec toutes les données liées
        """
        try:
            query = select(Application).where(Application.candidate_id == UUID(candidate_id))
            query = query.options(
                joinedload(Application.job_offer).joinedload(JobOffer.recruiter),
                selectinload(Application.documents),
                selectinload(Application.history),
                selectinload(Application.interview_slots),
                selectinload(Application.protocol1_evaluation),
                selectinload(Application.protocol2_evaluation)
            ).order_by(desc(Application.created_at))
            
            result = await self.db.execute(query)
            applications = result.unique().scalars().all()
            
            applications_data = []
            for app in applications:
                app_data = {
                    'id': str(app.id),
                    'status': app.status,
                    'created_at': app.created_at.isoformat(),
                    'updated_at': app.updated_at.isoformat(),
                    'job_offer': {
                        'id': str(app.job_offer.id),
                        'title': app.job_offer.title,
                        'location': app.job_offer.location,
                        'contract_type': app.job_offer.contract_type,
                        'department': app.job_offer.department,
                        'date_limite': app.job_offer.date_limite.isoformat() if app.job_offer.date_limite else None,
                        'recruiter': {
                            'first_name': app.job_offer.recruiter.first_name,
                            'last_name': app.job_offer.recruiter.last_name,
                            'email': app.job_offer.recruiter.email
                        }
                    },
                    'documents': [
                        {
                            'id': str(doc.id),
                            'document_type': doc.document_type,
                            'file_name': doc.file_name,
                            'file_size': doc.file_size,
                            'uploaded_at': doc.uploaded_at.isoformat()
                        } for doc in app.documents
                    ],
                    'interview_slots': [
                        {
                            'id': str(slot.id),
                            'date': slot.date,
                            'time': slot.time,
                            'status': slot.status,
                            'meeting_link': slot.meeting_link
                        } for slot in app.interview_slots
                    ],
                    'evaluations': {
                        'protocol1_completed': app.protocol1_evaluation.completed if app.protocol1_evaluation else False,
                        'protocol2_completed': app.protocol2_evaluation.completed if app.protocol2_evaluation else False,
                    }
                }
                applications_data.append(app_data)
            
            logger.info("Candidatures candidat récupérées", candidate_id=candidate_id, count=len(applications_data))
            return applications_data
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des candidatures candidat", error=str(e))
            raise
