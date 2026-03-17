"""
Services optimisés pour les requêtes complexes avec de meilleures relations (Version MongoDB)
"""
import structlog
from typing import Optional, List, Dict, Any, Tuple, Union
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import uuid

logger = structlog.get_logger(__name__)

class OptimizedQueryService:
    """Service pour les requêtes optimisées avec de meilleures relations via MongoDB Aggregation"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
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
        Récupérer les candidatures avec toutes les données liées en utilisant des agrégations MongoDB
        """
        try:
            # Construction du match initial
            match_query = {}
            if status_filter:
                match_query["status"] = status_filter
            if job_offer_id:
                match_query["job_offer_id"] = str(job_offer_id)
            if candidate_id:
                match_query["candidate_id"] = str(candidate_id)
            
            pipeline = [
                {"$match": match_query},
                {"$sort": {"created_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                
                # Jointure Candidat (User + Profile)
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"cand_id": "$candidate_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$or": [
                                            {"$eq": ["$_id", "$$cand_id"]},
                                            {"$eq": ["$_id", {"$toObjectId": "$$cand_id"}]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$lookup": {
                                    "from": "candidate_profiles",
                                    "localField": "_id",
                                    "foreignField": "user_id",
                                    "as": "profile"
                                }
                            },
                            {"$addFields": {"profile": {"$arrayElemAt": ["$profile", 0]}}}
                        ],
                        "as": "candidate"
                    }
                },
                {"$addFields": {"candidate": {"$arrayElemAt": ["$candidate", 0]}}},
                
                # Jointure Offre (JobOffer + Recruiter)
                {
                    "$lookup": {
                        "from": "job_offers",
                        "let": {"job_id": "$job_offer_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$or": [
                                            {"$eq": ["$_id", "$$job_id"]},
                                            {"$eq": ["$_id", {"$toObjectId": "$$job_id"}]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$lookup": {
                                    "from": "users",
                                    "let": {"rec_id": "$recruiter_id"},
                                    "pipeline": [
                                        {
                                            "$match": {
                                                "$expr": {
                                                    "$or": [
                                                        {"$eq": ["$_id", "$$rec_id"]},
                                                        {"$eq": ["$_id", {"$toObjectId": "$$rec_id"}]}
                                                    ]
                                                }
                                            }
                                        }
                                    ],
                                    "as": "recruiter"
                                }
                            },
                            {"$addFields": {"recruiter": {"$arrayElemAt": ["$recruiter", 0]}}}
                        ],
                        "as": "job_offer"
                    }
                },
                {"$addFields": {"job_offer": {"$arrayElemAt": ["$job_offer", 0]}}},
                
                # Historique
                {
                    "$lookup": {
                        "from": "application_history",
                        "localField": "_id",
                        "foreignField": "application_id",
                        "as": "history"
                    }
                },
                
                # Créneaux d'entretien
                {
                    "$lookup": {
                        "from": "interview_slots",
                        "localField": "_id",
                        "foreignField": "application_id",
                        "as": "interview_slots"
                    }
                },
                
                # Notifications
                {
                    "$lookup": {
                        "from": "notifications",
                        "localField": "_id",
                        "foreignField": "related_application_id",
                        "as": "notifications"
                    }
                }
            ]
            
            if include_evaluations:
                pipeline.extend([
                    {
                        "$lookup": {
                            "from": "protocol1_evaluations",
                            "localField": "_id",
                            "foreignField": "application_id",
                            "as": "protocol1_evaluation"
                        }
                    },
                    {"$addFields": {"protocol1_evaluation": {"$arrayElemAt": ["$protocol1_evaluation", 0]}}},
                    {
                        "$lookup": {
                            "from": "protocol2_evaluations",
                            "localField": "_id",
                            "foreignField": "application_id",
                            "as": "protocol2_evaluation"
                        }
                    },
                    {"$addFields": {"protocol2_evaluation": {"$arrayElemAt": ["$protocol2_evaluation", 0]}}}
                ])
            
            if include_documents:
                pipeline.append({
                    "$lookup": {
                        "from": "application_documents",
                        "localField": "_id",
                        "foreignField": "application_id",
                        "as": "documents"
                    }
                })
            
            cursor = self.db.applications.aggregate(pipeline)
            applications_data = await cursor.to_list(length=limit)
            
            # Nettoyage et formatage des données (conversions ObjectId -> str, types, etc.)
            for app in applications_data:
                app["id"] = str(app.pop("_id"))
                if app.get("candidate"):
                    app["candidate"]["id"] = str(app["candidate"].pop("_id"))
                    if app["candidate"].get("profile"):
                        app["candidate"]["profile"]["id"] = str(app["candidate"]["profile"].pop("_id"))
                if app.get("job_offer"):
                    app["job_offer"]["id"] = str(app["job_offer"].pop("_id"))
                    if app["job_offer"].get("recruiter"):
                        app["job_offer"]["recruiter"]["id"] = str(app["job_offer"]["recruiter"].pop("_id"))
                
                # Formater les évaluations
                if "protocol1_evaluation" in app and app["protocol1_evaluation"]:
                    app["protocol1_evaluation"]["id"] = str(app["protocol1_evaluation"].pop("_id"))
                if "protocol2_evaluation" in app and app["protocol2_evaluation"]:
                    app["protocol2_evaluation"]["id"] = str(app["protocol2_evaluation"].pop("_id"))
                
                # Formater les listes
                for key in ["history", "interview_slots", "notifications", "documents"]:
                    if key in app:
                        for item in app[key]:
                            item["id"] = str(item.pop("_id")) if "_id" in item else str(item.get("id"))
            
            total_count = await self.db.applications.count_documents(match_query)
            
            return applications_data, total_count
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des candidatures", error=str(e))
            raise
    
    async def get_dashboard_stats_optimized(self, recruiter_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupérer les statistiques du dashboard via agrégations MongoDB
        """
        try:
            stats = {}
            
            # Filtre recruteur pour les jobs
            job_match = {}
            if recruiter_id:
                job_match["recruiter_id"] = str(recruiter_id)
            
            # Stats des jobs
            total_jobs = await self.db.job_offers.count_documents(job_match)
            active_jobs = await self.db.job_offers.count_documents({**job_match, "status": "active"})
            
            stats['total_jobs'] = total_jobs
            stats['active_jobs'] = active_jobs
            
            # Stats des candidatures
            app_match = {}
            if recruiter_id:
                # Filtrer les candidatures par les jobs du recruteur
                jobs = await self.db.job_offers.find(job_match, {"_id": 1}).to_list(length=None)
                job_ids = [str(j["_id"]) for j in jobs]
                app_match["job_offer_id"] = {"$in": job_ids}
            
            # Agrégation par statut
            status_pipeline = [
                {"$match": app_match},
                {"$group": {
                    "_id": "$status", 
                    "count": {"$sum": 1},
                    "unique_candidates": {"$addToSet": "$candidate_id"}
                }}
            ]
            
            status_cursor = self.db.applications.aggregate(status_pipeline)
            status_stats = await status_cursor.to_list(length=None)
            
            status_counts = {str(row["_id"]): row["count"] for row in status_stats if row.get("_id")}
            total_applications = sum(status_counts.values())
            
            # Candidats uniques (tous statuts confondus)
            unique_candidates_pipeline = [
                {"$match": app_match},
                {"$group": {"_id": None, "unique_count": {"$addToSet": "$candidate_id"}}},
                {"$project": {"count": {"$size": "$unique_count"}}}
            ]
            unique_res = await self.db.applications.aggregate(unique_candidates_pipeline).to_list(length=1)
            unique_candidates = unique_res[0]["count"] if unique_res else 0
            
            stats.update({
                'total_applications': total_applications,
                'unique_candidates': unique_candidates,
                'status_breakdown': status_counts,
                'interviews_scheduled': status_counts.get('incubation', 0),
                'hired': status_counts.get('embauche', 0),
                'rejected': status_counts.get('refuse', 0)
            })
            
            # Stats par département (via JobOffer)
            dept_pipeline = [
                {"$match": job_match},
                {"$lookup": {
                    "from": "applications",
                    "localField": "_id",
                    "foreignField": "job_offer_id",
                    "as": "apps"
                }},
                {"$group": {
                    "_id": "$department",
                    "job_count": {"$sum": 1},
                    "application_count": {"$sum": {"$size": "$apps"}}
                }}
            ]
            
            dept_cursor = self.db.job_offers.aggregate(dept_pipeline)
            dept_stats = await dept_cursor.to_list(length=None)
            
            stats['department_stats'] = [
                {
                    'department': row["_id"] or 'Non spécifié',
                    'job_count': row["job_count"],
                    'application_count': row["application_count"],
                    'coverage_rate': round((row["application_count"] / row["job_count"] * 100) if row["job_count"] > 0 else 0, 2)
                }
                for row in dept_stats
            ]
            
            # Distribution par genre
            # Nécessite de rejoindre les profils
            gender_pipeline = [
                {"$match": app_match},
                {"$lookup": {
                    "from": "candidate_profiles",
                    "let": {"c_id": "$candidate_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$user_id", "$$c_id"]},
                                        {"$eq": ["$user_id", {"$toObjectId": "$$c_id"}]},
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "profile"
                }},
                {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": False}},
                {"$group": {
                    "_id": "$profile.gender",
                    "count": {"$sum": 1}
                }}
            ]
            
            gender_cursor = self.db.applications.aggregate(gender_pipeline)
            gender_stats = await gender_cursor.to_list(length=None)
            
            total_with_gender = sum(row["count"] for row in gender_stats)
            if total_with_gender > 0:
                male_count = sum(row["count"] for row in gender_stats if row["_id"] and str(row["_id"]).lower() in ['homme', 'h', 'm', 'masculin'])
                female_count = sum(row["count"] for row in gender_stats if row["_id"] and str(row["_id"]).lower() in ['femme', 'f', 'feminin', 'féminin'])
                
                stats['gender_distribution'] = {
                    'male_percent': round((male_count / total_with_gender) * 100, 2),
                    'female_percent': round((female_count / total_with_gender) * 100, 2),
                    'total_with_gender': total_with_gender
                }
            
            logger.info("Statistiques dashboard récupérées", recruiter_id=recruiter_id)
            return stats
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des statistiques", error=str(e))
            raise
    
    async def get_candidate_applications_optimized(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Récupérer les candidatures d'un candidat avec données liées via agrégations MongoDB
        """
        try:
            pipeline = [
                {"$match": {"candidate_id": str(candidate_id)}},
                {"$sort": {"created_at": -1}},
                
                # Job Offer + Recruiter
                {"$lookup": {
                    "from": "job_offers",
                    "let": {"j_id": "$job_offer_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$_id", "$$j_id"]},
                                        {"$eq": ["$_id", {"$toObjectId": "$$j_id"}]}
                                    ]
                                }
                            }
                        },
                        {
                            "$lookup": {
                                "from": "users",
                                "let": {"r_id": "$recruiter_id"},
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$or": [
                                                    {"$eq": ["$_id", "$$r_id"]},
                                                    {"$eq": ["$_id", {"$toObjectId": "$$r_id"}]}
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "as": "recruiter"
                            }
                        },
                        {"$addFields": {"recruiter": {"$arrayElemAt": ["$recruiter", 0]}}}
                    ],
                    "as": "job_offer"
                }},
                {"$addFields": {"job_offer": {"$arrayElemAt": ["$job_offer", 0]}}},
                
                # Documents
                {
                    "$lookup": {
                        "from": "application_documents",
                        "localField": "_id",
                        "foreignField": "application_id",
                        "as": "documents"
                    }
                },
                
                # Interview Slots
                {
                    "$lookup": {
                        "from": "interview_slots",
                        "localField": "_id",
                        "foreignField": "application_id",
                        "as": "interview_slots"
                    }
                }
            ]
            
            cursor = self.db.applications.aggregate(pipeline)
            applications = await cursor.to_list(length=None)
            
            # Formatage
            for app in applications:
                app["id"] = str(app.pop("_id"))
                if app.get("job_offer"):
                    app["job_offer"]["id"] = str(app["job_offer"].pop("_id"))
                    if app["job_offer"].get("recruiter"):
                        app["job_offer"]["recruiter"]["id"] = str(app["job_offer"]["recruiter"].pop("_id"))
                
                for key in ["documents", "interview_slots"]:
                    if key in app:
                        for item in app[key]:
                            item["id"] = str(item.pop("_id")) if "_id" in item else str(item.get("id"))
            
            logger.info("Candidatures candidat récupérées", candidate_id=candidate_id, count=len(applications))
            return applications
            
        except Exception as e:
            logger.error("Erreur lors de la récupération des candidatures candidat", error=str(e))
            raise
