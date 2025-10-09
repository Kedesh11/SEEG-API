"""
Service pour la gestion des Ã©valuations (Protocol 1 et Protocol 2)
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import structlog

from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.models.application import Application
from app.models.user import User
from app.schemas.evaluation import (
    Protocol1EvaluationCreate, Protocol1EvaluationUpdate, Protocol1EvaluationResponse,
    Protocol2EvaluationCreate, Protocol2EvaluationUpdate, Protocol2EvaluationResponse
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)


class EvaluationService:
    """Service pour la gestion des Ã©valuations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Protocol 1 Evaluation Methods
    async def create_protocol1_evaluation(
        self,
        evaluation_data: Protocol1EvaluationCreate,
        evaluator_id: str
    ) -> Protocol1EvaluationResponse:
        """
        CrÃ©er une nouvelle Ã©valuation Protocol 1
        
        Args:
            evaluation_data: DonnÃ©es de l'Ã©valuation
            evaluator_id: ID de l'Ã©valuateur
            
        Returns:
            Protocol1EvaluationResponse: Ã‰valuation crÃ©Ã©e
        """
        try:
            # VÃ©rification de l'existence de la candidature
            app_result = await self.db.execute(
                select(Application).where(Application.id == evaluation_data.application_id)
            )
            application = app_result.scalar_one_or_none()
            
            if not application:
                raise NotFoundError("Candidature non trouvÃ©e")
            
            # VÃ©rification si une Ã©valuation existe dÃ©jÃ 
            existing_eval = await self.db.execute(
                select(Protocol1Evaluation).where(
                    Protocol1Evaluation.application_id == evaluation_data.application_id
                )
            )
            
            if existing_eval.scalar_one_or_none():
                raise BusinessLogicError("Une Ã©valuation Protocol 1 existe dÃ©jÃ  pour cette candidature")
            
            # Calcul du score total
            total_score = self._calculate_protocol1_total_score(evaluation_data)
            
            # CrÃ©ation de l'Ã©valuation
            evaluation = Protocol1Evaluation(
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id,
                documentary_score=evaluation_data.documentary_score,
                documentary_notes=evaluation_data.documentary_notes,
                mtp_adherence_score=evaluation_data.mtp_adherence_score,
                mtp_adherence_notes=evaluation_data.mtp_adherence_notes,
                interview_score=evaluation_data.interview_score,
                interview_notes=evaluation_data.interview_notes,
                overall_score=total_score,
                recommendation=evaluation_data.recommendation,
                additional_notes=evaluation_data.additional_notes,
                evaluation_date=datetime.now(timezone.utc)
            )
            
            self.db.add(evaluation)
            #  PAS de commit ici
            await self.db.refresh(evaluation)
            
            logger.info(
                "Protocol 1 evaluation created",
                evaluation_id=str(evaluation.id),
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id,
                overall_score=total_score
            )
            
            return Protocol1EvaluationResponse.model_validate(evaluation)
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to create Protocol 1 evaluation",
                error=str(e),
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id
            )
            raise
    
    async def update_protocol1_evaluation(
        self,
        evaluation_id: str,
        evaluation_data: Protocol1EvaluationUpdate,
        updated_by: str
    ) -> Protocol1EvaluationResponse:
        """
        Mettre Ã  jour une Ã©valuation Protocol 1
        
        Args:
            evaluation_id: ID de l'Ã©valuation
            evaluation_data: DonnÃ©es de mise Ã  jour
            updated_by: ID de l'utilisateur qui effectue la mise Ã  jour
            
        Returns:
            Protocol1EvaluationResponse: Ã‰valuation mise Ã  jour
        """
        try:
            # VÃ©rification de l'existence de l'Ã©valuation
            result = await self.db.execute(
                select(Protocol1Evaluation).where(Protocol1Evaluation.id == evaluation_id)
            )
            evaluation = result.scalar_one_or_none()
            
            if not evaluation:
                raise NotFoundError(f"Ã‰valuation Protocol 1 avec l'ID {evaluation_id} non trouvÃ©e")
            
            # Mise Ã  jour des champs
            update_data = evaluation_data.model_dump(exclude_unset=True)
            
            # Recalcul du score total si nÃ©cessaire
            if any(field in update_data for field in ['documentary_score', 'mtp_adherence_score', 'interview_score']):
                # RÃ©cupÃ©ration des valeurs actuelles
                current_data = evaluation_data.model_dump()
                for field in ['documentary_score', 'mtp_adherence_score', 'interview_score']:
                    if field not in current_data:
                        current_data[field] = getattr(evaluation, field)
                
                # CrÃ©ation d'un objet temporaire pour le calcul
                temp_eval = Protocol1EvaluationCreate(**current_data)
                update_data['overall_score'] = self._calculate_protocol1_total_score(temp_eval)
            
            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                
                await self.db.execute(
                    update(Protocol1Evaluation)
                    .where(Protocol1Evaluation.id == evaluation_id)
                    .values(**update_data)
                )
                
                #  PAS de commit ici
                
                # RÃ©cupÃ©ration de l'Ã©valuation mise Ã  jour
                result = await self.db.execute(
                    select(Protocol1Evaluation).where(Protocol1Evaluation.id == evaluation_id)
                )
                evaluation = result.scalar_one()
                
                logger.info(
                    "Protocol 1 evaluation updated",
                    evaluation_id=evaluation_id,
                    updated_by=updated_by,
                    updated_fields=list(update_data.keys())
                )
            
            return Protocol1EvaluationResponse.model_validate(evaluation)
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to update Protocol 1 evaluation",
                evaluation_id=evaluation_id,
                error=str(e)
            )
            raise
    
    async def get_protocol1_evaluation(
        self, 
        evaluation_id: str
    ) -> Protocol1EvaluationResponse:
        """
        RÃ©cupÃ©rer une Ã©valuation Protocol 1 par son ID
        
        Args:
            evaluation_id: ID de l'Ã©valuation
            
        Returns:
            Protocol1EvaluationResponse: Ã‰valuation
        """
        result = await self.db.execute(
            select(Protocol1Evaluation)
            .options(
                selectinload(Protocol1Evaluation.application),
                selectinload(Protocol1Evaluation.evaluator)
            )
            .where(Protocol1Evaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            raise NotFoundError(f"Ã‰valuation Protocol 1 avec l'ID {evaluation_id} non trouvÃ©e")
        
        return Protocol1EvaluationResponse.model_validate(evaluation)
    
    async def get_protocol1_evaluations_by_application(
        self, 
        application_id: str
    ) -> List[Protocol1EvaluationResponse]:
        """
        RÃ©cupÃ©rer les Ã©valuations Protocol 1 pour une candidature
        
        Args:
            application_id: ID de la candidature
            
        Returns:
            List[Protocol1EvaluationResponse]: Liste des Ã©valuations
        """
        result = await self.db.execute(
            select(Protocol1Evaluation)
            .options(selectinload(Protocol1Evaluation.evaluator))
            .where(Protocol1Evaluation.application_id == application_id)
            .order_by(desc(Protocol1Evaluation.evaluation_date))
        )
        
        evaluations = result.scalars().all()
        return [Protocol1EvaluationResponse.model_validate(eval) for eval in evaluations]
    
    # Protocol 2 Evaluation Methods
    async def create_protocol2_evaluation(
        self,
        evaluation_data: Protocol2EvaluationCreate,
        evaluator_id: str
    ) -> Protocol2EvaluationResponse:
        """
        CrÃ©er une nouvelle Ã©valuation Protocol 2
        
        Args:
            evaluation_data: DonnÃ©es de l'Ã©valuation
            evaluator_id: ID de l'Ã©valuateur
            
        Returns:
            Protocol2EvaluationResponse: Ã‰valuation crÃ©Ã©e
        """
        try:
            # VÃ©rification de l'existence de la candidature
            app_result = await self.db.execute(
                select(Application).where(Application.id == evaluation_data.application_id)
            )
            application = app_result.scalar_one_or_none()
            
            if not application:
                raise NotFoundError("Candidature non trouvÃ©e")
            
            # VÃ©rification si une Ã©valuation existe dÃ©jÃ 
            existing_eval = await self.db.execute(
                select(Protocol2Evaluation).where(
                    Protocol2Evaluation.application_id == evaluation_data.application_id
                )
            )
            
            if existing_eval.scalar_one_or_none():
                raise BusinessLogicError("Une Ã©valuation Protocol 2 existe dÃ©jÃ  pour cette candidature")
            
            # Calcul du score total
            total_score = self._calculate_protocol2_total_score(evaluation_data)
            
            # CrÃ©ation de l'Ã©valuation
            evaluation = Protocol2Evaluation(
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id,
                technical_skills_score=evaluation_data.technical_skills_score,
                technical_skills_notes=evaluation_data.technical_skills_notes,
                soft_skills_score=evaluation_data.soft_skills_score,
                soft_skills_notes=evaluation_data.soft_skills_notes,
                cultural_fit_score=evaluation_data.cultural_fit_score,
                cultural_fit_notes=evaluation_data.cultural_fit_notes,
                leadership_potential_score=evaluation_data.leadership_potential_score,
                leadership_potential_notes=evaluation_data.leadership_potential_notes,
                overall_score=total_score,
                recommendation=evaluation_data.recommendation,
                additional_notes=evaluation_data.additional_notes,
                evaluation_date=datetime.now(timezone.utc)
            )
            
            self.db.add(evaluation)
            #  PAS de commit ici
            await self.db.refresh(evaluation)
            
            logger.info(
                "Protocol 2 evaluation created",
                evaluation_id=str(evaluation.id),
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id,
                overall_score=total_score
            )
            
            return Protocol2EvaluationResponse.model_validate(evaluation)
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to create Protocol 2 evaluation",
                error=str(e),
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id
            )
            raise
    
    async def get_protocol2_evaluation(
        self, 
        evaluation_id: str
    ) -> Protocol2EvaluationResponse:
        """
        RÃ©cupÃ©rer une Ã©valuation Protocol 2 par son ID
        
        Args:
            evaluation_id: ID de l'Ã©valuation
            
        Returns:
            Protocol2EvaluationResponse: Ã‰valuation
        """
        result = await self.db.execute(
            select(Protocol2Evaluation)
            .options(
                selectinload(Protocol2Evaluation.application),
                selectinload(Protocol2Evaluation.evaluator)
            )
            .where(Protocol2Evaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            raise NotFoundError(f"Ã‰valuation Protocol 2 avec l'ID {evaluation_id} non trouvÃ©e")
        
        return Protocol2EvaluationResponse.model_validate(evaluation)
    
    async def get_protocol2_evaluations_by_application(
        self, 
        application_id: str
    ) -> List[Protocol2EvaluationResponse]:
        """
        RÃ©cupÃ©rer les Ã©valuations Protocol 2 pour une candidature
        
        Args:
            application_id: ID de la candidature
            
        Returns:
            List[Protocol2EvaluationResponse]: Liste des Ã©valuations
        """
        result = await self.db.execute(
            select(Protocol2Evaluation)
            .options(selectinload(Protocol2Evaluation.evaluator))
            .where(Protocol2Evaluation.application_id == application_id)
            .order_by(desc(Protocol2Evaluation.evaluation_date))
        )
        
        evaluations = result.scalars().all()
        return [Protocol2EvaluationResponse.model_validate(eval) for eval in evaluations]
    
    # Helper Methods
    def _calculate_protocol1_total_score(self, evaluation_data: Protocol1EvaluationCreate) -> float:
        """
        Calculer le score total pour Protocol 1
        
        Args:
            evaluation_data: DonnÃ©es de l'Ã©valuation
            
        Returns:
            float: Score total calculÃ©
        """
        # PondÃ©ration des scores (Ã  ajuster selon les besoins)
        weights = {
            'documentary': 0.3,
            'mtp_adherence': 0.4,
            'interview': 0.3
        }
        
        total_score = (
            evaluation_data.documentary_score * weights['documentary'] +
            evaluation_data.mtp_adherence_score * weights['mtp_adherence'] +
            evaluation_data.interview_score * weights['interview']
        )
        
        return round(total_score, 2)
    
    def _calculate_protocol2_total_score(self, evaluation_data: Protocol2EvaluationCreate) -> float:
        """
        Calculer le score total pour Protocol 2
        
        Args:
            evaluation_data: DonnÃ©es de l'Ã©valuation
            
        Returns:
            float: Score total calculÃ©
        """
        # PondÃ©ration des scores (Ã  ajuster selon les besoins)
        weights = {
            'technical_skills': 0.3,
            'soft_skills': 0.25,
            'cultural_fit': 0.25,
            'leadership_potential': 0.2
        }
        
        total_score = (
            evaluation_data.technical_skills_score * weights['technical_skills'] +
            evaluation_data.soft_skills_score * weights['soft_skills'] +
            evaluation_data.cultural_fit_score * weights['cultural_fit'] +
            evaluation_data.leadership_potential_score * weights['leadership_potential']
        )
        
        return round(total_score, 2)
    
    async def get_evaluation_statistics(self) -> Dict[str, Any]:
        """
        RÃ©cupÃ©rer les statistiques des Ã©valuations
        
        Returns:
            Dict[str, Any]: Statistiques des Ã©valuations
        """
        # Statistiques Protocol 1
        p1_total = await self.db.execute(select(func.count(Protocol1Evaluation.id)))
        p1_count = p1_total.scalar()
        
        p1_avg_score = await self.db.execute(
            select(func.avg(Protocol1Evaluation.overall_score))
        )
        p1_avg = p1_avg_score.scalar() or 0
        
        # Statistiques Protocol 2
        p2_total = await self.db.execute(select(func.count(Protocol2Evaluation.id)))
        p2_count = p2_total.scalar()
        
        p2_avg_score = await self.db.execute(
            select(func.avg(Protocol2Evaluation.overall_score))
        )
        p2_avg = p2_avg_score.scalar() or 0
        
        return {
            "protocol1": {
                "total_evaluations": p1_count,
                "average_score": round(p1_avg, 2)
            },
            "protocol2": {
                "total_evaluations": p2_count,
                "average_score": round(p2_avg, 2)
            }
        }
