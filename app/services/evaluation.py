"""
Service pour la gestion des Ã©valuations (Protocol 1 et Protocol 2)
"""
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
import structlog
from app.schemas.evaluation import (
    Protocol1EvaluationCreate, Protocol1EvaluationUpdate, Protocol1EvaluationResponse,
    Protocol2EvaluationCreate, Protocol2EvaluationUpdate, Protocol2EvaluationResponse
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)


class EvaluationService:
    """Service pour la gestion des Ã©valuations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
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
            # Vérification de l'existence de la candidature
            app_id = str(evaluation_data.application_id)
            app_query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
            application = await self.db.applications.find_one(app_query)
            
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Vérification si une évaluation existe déjà
            existing_eval = await self.db.protocol1_evaluations.find_one({"application_id": app_id})
            
            if existing_eval:
                raise BusinessLogicError("Une évaluation Protocol 1 existe déjà pour cette candidature")
            
            # Calcul du score total
            total_score = self._calculate_protocol1_total_score(evaluation_data)
            
            # Création de l'évaluation avec les champs du schéma
            evaluation_dict = evaluation_data.model_dump(exclude={'application_id', 'evaluator_id'})
            evaluation_dict['application_id'] = app_id
            evaluation_dict['evaluator_id'] = str(evaluator_id)
            evaluation_dict['overall_score'] = total_score
            evaluation_dict['created_at'] = datetime.now(timezone.utc)
            evaluation_dict['updated_at'] = datetime.now(timezone.utc)
            
            result = await self.db.protocol1_evaluations.insert_one(evaluation_dict)
            evaluation_dict['_id'] = result.inserted_id
            evaluation_dict['id'] = str(result.inserted_id)
            
            logger.info(
                "Protocol 1 evaluation created",
                evaluation_id=str(result.inserted_id),
                application_id=app_id,
                evaluator_id=evaluator_id,
                overall_score=total_score
            )
            
            return Protocol1EvaluationResponse.model_validate(evaluation_dict)
            
        except Exception as e:
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
            # Vérification de l'existence de l'évaluation
            query = {"_id": ObjectId(evaluation_id)} if len(evaluation_id) == 24 else {"_id": evaluation_id}
            evaluation = await self.db.protocol1_evaluations.find_one(query)
            
            if not evaluation:
                raise NotFoundError(f"Évaluation Protocol 1 avec l'ID {evaluation_id} non trouvée")
            
            # Mise à jour des champs
            update_data = evaluation_data.model_dump(exclude_unset=True)
            
            # Recalcul du score total si nécessaire
            if any(field in update_data for field in ['documentary_score', 'mtp_score', 'interview_score']):
                current_data = evaluation.copy()
                current_data.update(update_data)
                
                # Création d'un objet temporaire pour le calcul
                temp_eval = Protocol1EvaluationCreate(**current_data)
                update_data['overall_score'] = self._calculate_protocol1_total_score(temp_eval)
            
            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                
                await self.db.protocol1_evaluations.update_one(
                    query,
                    {"$set": update_data}
                )
                
                evaluation = await self.db.protocol1_evaluations.find_one(query)
                evaluation['id'] = str(evaluation['_id'])
                
                logger.info(
                    "Protocol 1 evaluation updated",
                    evaluation_id=evaluation_id,
                    updated_by=updated_by,
                    updated_fields=list(update_data.keys())
                )
            
            return Protocol1EvaluationResponse.model_validate(evaluation)
            
        except Exception as e:
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
        query = {"_id": ObjectId(evaluation_id)} if len(evaluation_id) == 24 else {"_id": evaluation_id}
        evaluation = await self.db.protocol1_evaluations.find_one(query)
        
        if not evaluation:
            raise NotFoundError(f"Évaluation Protocol 1 avec l'ID {evaluation_id} non trouvée")
        
        # Fetch relations
        app_id = evaluation.get("application_id")
        if app_id:
            app_query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
            evaluation["application"] = await self.db.applications.find_one(app_query)
        
        evaluator_id = evaluation.get("evaluator_id")
        if evaluator_id:
            user_query = {"_id": ObjectId(evaluator_id)} if len(evaluator_id) == 24 else {"_id": evaluator_id}
            evaluation["evaluator"] = await self.db.users.find_one(user_query)
        
        evaluation['id'] = str(evaluation['_id'])
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
        cursor = self.db.protocol1_evaluations.find({"application_id": str(application_id)}).sort("created_at", -1)
        evaluations = await cursor.to_list(length=100)
        
        for eval in evaluations:
            eval['id'] = str(eval['_id'])
            evaluator_id = eval.get("evaluator_id")
            if evaluator_id:
                user_query = {"_id": ObjectId(evaluator_id)} if len(evaluator_id) == 24 else {"_id": evaluator_id}
                eval["evaluator"] = await self.db.users.find_one(user_query)
                
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
            # Vérification de l'existence de la candidature
            app_id = str(evaluation_data.application_id)
            app_query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
            application = await self.db.applications.find_one(app_query)
            
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Vérification si une évaluation existe déjà
            existing_eval = await self.db.protocol2_evaluations.find_one({"application_id": app_id})
            
            if existing_eval:
                raise BusinessLogicError("Une évaluation Protocol 2 existe déjà pour cette candidature")
            
            # Calcul du score total
            total_score = self._calculate_protocol2_total_score(evaluation_data)
            
            # Création de l'évaluation avec les champs du schéma
            evaluation_dict = evaluation_data.model_dump(exclude={'application_id', 'evaluator_id'})
            evaluation_dict['application_id'] = app_id
            evaluation_dict['evaluator_id'] = str(evaluator_id)
            evaluation_dict['overall_score'] = total_score
            evaluation_dict['created_at'] = datetime.now(timezone.utc)
            evaluation_dict['updated_at'] = datetime.now(timezone.utc)
            
            result = await self.db.protocol2_evaluations.insert_one(evaluation_dict)
            evaluation_dict['_id'] = result.inserted_id
            evaluation_dict['id'] = str(result.inserted_id)
            
            logger.info(
                "Protocol 2 evaluation created",
                evaluation_id=str(result.inserted_id),
                application_id=app_id,
                evaluator_id=evaluator_id,
                overall_score=total_score
            )
            
            return Protocol2EvaluationResponse.model_validate(evaluation_dict)
            
        except Exception as e:
            logger.error(
                "Failed to create Protocol 2 evaluation",
                error=str(e),
                application_id=evaluation_data.application_id,
                evaluator_id=evaluator_id
            )
            raise
    
    async def update_protocol2_evaluation(
        self,
        evaluation_id: str,
        evaluation_data: Protocol2EvaluationUpdate,
        updated_by: str
    ) -> Protocol2EvaluationResponse:
        """
        Mettre à jour une évaluation Protocol 2
        
        Args:
            evaluation_id: ID de l'évaluation
            evaluation_data: Données de mise à jour
            updated_by: ID de l'utilisateur qui effectue la mise à jour
            
        Returns:
            Protocol2EvaluationResponse: Évaluation mise à jour
        """
        try:
            # Vérification de l'existence de l'évaluation
            query = {"_id": ObjectId(evaluation_id)} if len(evaluation_id) == 24 else {"_id": evaluation_id}
            evaluation = await self.db.protocol2_evaluations.find_one(query)
            
            if not evaluation:
                raise NotFoundError(f"Évaluation Protocol 2 avec l'ID {evaluation_id} non trouvée")
            
            # Mise à jour des champs
            update_data = evaluation_data.model_dump(exclude_unset=True)
            
            # Recalcul du score total si nécessaire
            if any(field in update_data for field in ['qcm_role_score', 'qcm_codir_score']):
                current_data = evaluation.copy()
                current_data.update(update_data)
                
                # Création d'un objet temporaire pour le calcul
                temp_eval = Protocol2EvaluationCreate(**current_data)
                update_data['overall_score'] = self._calculate_protocol2_total_score(temp_eval)
            
            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                
                await self.db.protocol2_evaluations.update_one(
                    query,
                    {"$set": update_data}
                )
                
                evaluation = await self.db.protocol2_evaluations.find_one(query)
                evaluation['id'] = str(evaluation['_id'])
                
                logger.info(
                    "Protocol 2 evaluation updated",
                    evaluation_id=evaluation_id,
                    updated_by=updated_by,
                    updated_fields=list(update_data.keys())
                )
            
            return Protocol2EvaluationResponse.model_validate(evaluation)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update Protocol 2 evaluation",
                evaluation_id=evaluation_id,
                error=str(e),
                updated_by=updated_by
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
        query = {"_id": ObjectId(evaluation_id)} if len(evaluation_id) == 24 else {"_id": evaluation_id}
        evaluation = await self.db.protocol2_evaluations.find_one(query)
        
        if not evaluation:
            raise NotFoundError(f"Évaluation Protocol 2 avec l'ID {evaluation_id} non trouvée")
        
        # Fetch relations
        app_id = evaluation.get("application_id")
        if app_id:
            app_query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
            evaluation["application"] = await self.db.applications.find_one(app_query)
        
        evaluator_id = evaluation.get("evaluator_id")
        if evaluator_id:
            user_query = {"_id": ObjectId(evaluator_id)} if len(evaluator_id) == 24 else {"_id": evaluator_id}
            evaluation["evaluator"] = await self.db.users.find_one(user_query)
        
        evaluation['id'] = str(evaluation['_id'])
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
        cursor = self.db.protocol2_evaluations.find({"application_id": str(application_id)}).sort("created_at", -1)
        evaluations = await cursor.to_list(length=100)
        
        for eval in evaluations:
            eval['id'] = str(eval['_id'])
            evaluator_id = eval.get("evaluator_id")
            if evaluator_id:
                user_query = {"_id": ObjectId(evaluator_id)} if len(evaluator_id) == 24 else {"_id": evaluator_id}
                eval["evaluator"] = await self.db.users.find_one(user_query)
                
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
        # PondÃ©ration des scores (Ã  ajuster selon les besoins)
        weights = {
            'documentary': 0.3,
            'mtp': 0.4,
            'interview': 0.3
        }
        
        # Utiliser les vrais noms de champs du schéma
        doc_score = float(evaluation_data.documentary_score or 0)
        mtp_score = float(evaluation_data.mtp_score or 0)
        interview_score = float(evaluation_data.interview_score or 0)
        
        total_score = (
            doc_score * weights['documentary'] +
            mtp_score * weights['mtp'] +
            interview_score * weights['interview']
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
        # PondÃ©ration des scores (Ã  ajuster selon les besoins)
        # Protocol 2 utilise qcm_role_score et qcm_codir_score
        weights = {
            'qcm_role': 0.5,
            'qcm_codir': 0.5
        }
        
        # Utiliser les vrais noms de champs du schéma
        role_score = float(evaluation_data.qcm_role_score or 0)
        codir_score = float(evaluation_data.qcm_codir_score or 0)
        
        total_score = (
            role_score * weights['qcm_role'] +
            codir_score * weights['qcm_codir']
        )
        
        return round(total_score, 2)
    
    async def get_evaluation_statistics(self) -> Dict[str, Any]:
        """
        RÃ©cupÃ©rer les statistiques des Ã©valuations
        
        Returns:
            Dict[str, Any]: Statistiques des Ã©valuations
        """
        # Statistiques Protocol 1
        p1_count = await self.db.protocol1_evaluations.count_documents({})
        
        p1_pipeline = [
            {"$group": {"_id": None, "avg_score": {"$avg": "$overall_score"}}}
        ]
        p1_cursor = self.db.protocol1_evaluations.aggregate(p1_pipeline)
        p1_avg_res = await p1_cursor.to_list(length=1)
        p1_avg = p1_avg_res[0]["avg_score"] if p1_avg_res else 0
        
        # Statistiques Protocol 2
        p2_count = await self.db.protocol2_evaluations.count_documents({})
        
        p2_pipeline = [
            {"$group": {"_id": None, "avg_score": {"$avg": "$overall_score"}}}
        ]
        p2_cursor = self.db.protocol2_evaluations.aggregate(p2_pipeline)
        p2_avg_res = await p2_cursor.to_list(length=1)
        p2_avg = p2_avg_res[0]["avg_score"] if p2_avg_res else 0
        
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
