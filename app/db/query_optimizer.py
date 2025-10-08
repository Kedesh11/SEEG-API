"""
Module d'optimisation des requêtes SQL pour l'application SEEG-API.

Fournit des fonctions et des patterns pour optimiser les requêtes SQLAlchemy
et réduire le nombre de requêtes à la base de données.
"""
from typing import List, Optional, Type, Any
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload, contains_eager, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
import structlog

logger = structlog.get_logger(__name__)


class QueryOptimizer:
    """Classe pour optimiser les requêtes SQLAlchemy."""
    
    @staticmethod
    def optimize_user_query(query: Select) -> Select:
        """
        Optimise une requête sur la table User.
        
        Args:
            query: Requête SQLAlchemy
            
        Returns:
            Requête optimisée avec eager loading
        """
        # Charger le profil candidat si nécessaire
        query = query.options(
            selectinload('candidate_profile'),
            selectinload('notifications').selectinload('application')
        )
        return query
    
    @staticmethod
    def optimize_job_offer_query(query: Select) -> Select:
        """
        Optimise une requête sur la table JobOffer.
        
        Args:
            query: Requête SQLAlchemy
            
        Returns:
            Requête optimisée avec eager loading
        """
        # Charger les relations nécessaires
        query = query.options(
            selectinload('recruiter'),
            selectinload('applications').selectinload('candidate'),
            selectinload('application_drafts')
        )
        return query
    
    @staticmethod
    def optimize_application_query(query: Select) -> Select:
        """
        Optimise une requête sur la table Application.
        
        Args:
            query: Requête SQLAlchemy
            
        Returns:
            Requête optimisée avec eager loading
        """
        # Charger toutes les relations nécessaires en une seule requête
        query = query.options(
            selectinload('candidate').selectinload('candidate_profile'),
            selectinload('job_offer').selectinload('recruiter'),
            selectinload('documents'),
            selectinload('history').selectinload('changed_by_user'),
            selectinload('protocol1_evaluation').selectinload('evaluator'),
            selectinload('protocol2_evaluation').selectinload('evaluator'),
            selectinload('interview_slots'),
            selectinload('notifications')
        )
        return query
    
    @staticmethod
    def optimize_notification_query(query: Select) -> Select:
        """
        Optimise une requête sur la table Notification.
        
        Args:
            query: Requête SQLAlchemy
            
        Returns:
            Requête optimisée avec eager loading
        """
        query = query.options(
            selectinload('user'),
            selectinload('application').selectinload('job_offer')
        )
        return query
    
    @staticmethod
    async def get_paginated_results(
        db: AsyncSession,
        query: Select,
        page: int = 1,
        per_page: int = 20,
        optimize: bool = True
    ) -> tuple[List[Any], int]:
        """
        Récupère des résultats paginés avec le compte total.
        
        Args:
            db: Session de base de données
            query: Requête SQLAlchemy
            page: Numéro de page (commence à 1)
            per_page: Nombre d'éléments par page
            optimize: Appliquer l'optimisation de requête
            
        Returns:
            Tuple (résultats, total)
        """
        # Calculer l'offset
        offset = (page - 1) * per_page
        
        # Obtenir le compte total en une seule requête
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Appliquer la pagination
        paginated_query = query.offset(offset).limit(per_page)
        
        # Exécuter la requête
        result = await db.execute(paginated_query)
        items = result.scalars().all()
        
        return items, total
    
    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        model: Type[Any],
        objects: List[dict]
    ) -> List[Any]:
        """
        Création en masse d'objets pour réduire les requêtes.
        
        Args:
            db: Session de base de données
            model: Modèle SQLAlchemy
            objects: Liste de dictionnaires avec les données
            
        Returns:
            Liste des objets créés
        """
        instances = [model(**obj) for obj in objects]
        db.add_all(instances)
        await db.commit()
        
        # Rafraîchir tous les objets en une seule requête
        for instance in instances:
            await db.refresh(instance)
        
        return instances
    
    @staticmethod
    async def bulk_update(
        db: AsyncSession,
        model: Type[Any],
        updates: List[dict]
    ) -> int:
        """
        Mise à jour en masse pour réduire les requêtes.
        
        Args:
            db: Session de base de données
            model: Modèle SQLAlchemy
            updates: Liste de dictionnaires avec 'id' et les champs à mettre à jour
            
        Returns:
            Nombre d'objets mis à jour
        """
        if not updates:
            return 0
        
        # Grouper les mises à jour par valeurs communes
        update_groups = {}
        for update in updates:
            obj_id = update.pop('id')
            update_key = str(sorted(update.items()))
            
            if update_key not in update_groups:
                update_groups[update_key] = {'values': update, 'ids': []}
            update_groups[update_key]['ids'].append(obj_id)
        
        total_updated = 0
        
        # Exécuter les mises à jour groupées
        for group in update_groups.values():
            stmt = (
                model.__table__.update()
                .where(model.id.in_(group['ids']))
                .values(**group['values'])
            )
            result = await db.execute(stmt)
            total_updated += result.rowcount
        
        await db.commit()
        return total_updated


# Décorateurs pour l'optimisation automatique
def optimize_query(model_name: str):
    """
    Décorateur pour optimiser automatiquement une requête.
    
    Args:
        model_name: Nom du modèle ('user', 'job_offer', 'application', etc.)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Récupérer la requête depuis la fonction
            query = await func(*args, **kwargs)
            
            # Appliquer l'optimisation appropriée
            optimizer = QueryOptimizer()
            optimize_method = f"optimize_{model_name}_query"
            
            if hasattr(optimizer, optimize_method):
                query = getattr(optimizer, optimize_method)(query)
                logger.debug(f"Requête optimisée pour {model_name}")
            
            return query
        
        return wrapper
    return decorator


# Fonctions utilitaires pour les requêtes communes
async def get_user_with_full_profile(db: AsyncSession, user_id: str):
    """Récupère un utilisateur avec toutes ses relations."""
    query = select(User).where(User.id == user_id)
    query = QueryOptimizer.optimize_user_query(query)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_job_offer_with_applications(db: AsyncSession, job_id: str):
    """Récupère une offre d'emploi avec toutes ses candidatures."""
    query = select(JobOffer).where(JobOffer.id == job_id)
    query = QueryOptimizer.optimize_job_offer_query(query)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_application_complete(db: AsyncSession, application_id: str):
    """Récupère une candidature avec toutes ses relations."""
    query = select(Application).where(Application.id == application_id)
    query = QueryOptimizer.optimize_application_query(query)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Import des modèles nécessaires
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application
