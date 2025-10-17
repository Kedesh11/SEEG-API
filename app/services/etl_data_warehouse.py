"""
ETL Data Warehouse Service - Architecture Star Schema
=====================================================
Architecture: Clean Code + SOLID + Data Warehouse Best Practices

Principes appliqués:
- Single Responsibility: Chaque fonction a un rôle unique
- Open/Closed: Extensible sans modification
- Star Schema: Optimisé pour analytics et requêtes BI
- Data Quality: Validation et nettoyage des données
- Idempotence: Réexécution safe
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import structlog
from azure.storage.blob import ContentSettings

from app.services.blob_storage import BlobStorageService

logger = structlog.get_logger(__name__)


class ETLDataWarehouseService:
    """
    Service ETL pour export vers Data Warehouse (Blob Storage).
    
    Architecture Star Schema:
    - Fact Table: fact_applications (candidatures avec métriques)
    - Dimensions: dim_candidates, dim_job_offers, dim_documents, dim_dates
    
    Avantages:
    - ✅ Requêtes analytics rapides
    - ✅ Jointures simples
    - ✅ Dénormalisation partielle (performance)
    - ✅ Clés primaires/étrangères claires
    """
    
    def __init__(self, blob_service: BlobStorageService):
        """
        Initialize ETL Data Warehouse Service.
        
        Args:
            blob_service: Service de connexion Blob Storage
        """
        self.blob_service = blob_service
    
    def _build_dim_candidate(
        self,
        application: Dict[str, Any],
        candidate_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Construit la dimension Candidat (dénormalisée User + CandidateProfile).
        
        Clé primaire: candidate_id
        
        Contient:
        - Infos personnelles (nom, email, téléphone, adresse)
        - Infos professionnelles (matricule, poste, expérience)
        - Profil complet (compétences, salaire, LinkedIn)
        - Statuts (actif, vérifié, interne/externe)
        
        Returns:
            Dimension candidat dénormalisée
        """
        candidate = application.get("candidate", {}) or {}
        profile = candidate_profile or {}
        
        return {
            # ========== CLÉ PRIMAIRE ==========
            "candidate_id": candidate.get("id"),
            
            # ========== INFORMATIONS PERSONNELLES ==========
            "email": candidate.get("email"),
            "first_name": candidate.get("first_name"),
            "last_name": candidate.get("last_name"),
            "full_name": f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip(),
            "phone": candidate.get("phone"),
            "date_of_birth": candidate.get("date_of_birth"),
            "sexe": candidate.get("sexe"),
            "adresse": candidate.get("adresse"),
            
            # ========== INFORMATIONS PROFESSIONNELLES ==========
            "matricule": candidate.get("matricule"),
            "poste_actuel": candidate.get("poste_actuel"),
            "annees_experience": candidate.get("annees_experience"),
            "role": candidate.get("role"),
            
            # ========== STATUTS ==========
            "candidate_status": candidate.get("candidate_status"),  # interne/externe
            "statut": candidate.get("statut"),  # actif/en_attente/bloqué
            "is_internal_candidate": candidate.get("is_internal_candidate"),
            "email_verified": candidate.get("email_verified"),
            "is_active": candidate.get("is_active"),
            
            # ========== PROFIL CANDIDAT (de CandidateProfile) ==========
            "profile_address": profile.get("address"),
            "profile_availability": profile.get("availability"),
            "profile_birth_date": profile.get("birth_date"),
            "current_department": profile.get("current_department"),
            "current_position": profile.get("current_position"),
            "cv_url": profile.get("cv_url"),
            "education": profile.get("education"),
            "expected_salary_min": profile.get("expected_salary_min"),
            "expected_salary_max": profile.get("expected_salary_max"),
            "gender": profile.get("gender"),
            "linkedin_url": profile.get("linkedin_url"),
            "portfolio_url": profile.get("portfolio_url"),
            "skills": profile.get("skills"),  # Array
            "profile_years_experience": profile.get("years_experience"),
            
            # ========== METADATA ==========
            "candidate_created_at": candidate.get("created_at"),
            "profile_id": profile.get("id") if profile else None,
        }
    
    def _build_dim_job_offer(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construit la dimension Offre d'Emploi.
        
        Clé primaire: job_offer_id
        
        Contient:
        - Détails de l'offre (titre, description, localisation)
        - Questions MTP (pour analytics des questions)
        - Métadonnées (dates, status)
        
        Returns:
            Dimension offre d'emploi
        """
        job_offer = application.get("job_offer", {}) or {}
        questions_mtp = job_offer.get("questions_mtp", {}) or {}
        
        return {
            # ========== CLÉ PRIMAIRE ==========
            "job_offer_id": job_offer.get("id"),
            
            # ========== DÉTAILS DE L'OFFRE ==========
            "title": job_offer.get("title"),
            "description": job_offer.get("description"),
            "location": job_offer.get("location"),
            "contract_type": job_offer.get("contract_type"),
            "department": job_offer.get("department"),
            "offer_status": job_offer.get("offer_status"),  # interne/externe/tous
            
            # ========== QUESTIONS MTP ==========
            "questions_mtp": questions_mtp,
            "questions_metier": questions_mtp.get("questions_metier", []),
            "questions_talent": questions_mtp.get("questions_talent", []),
            "questions_paradigme": questions_mtp.get("questions_paradigme", []),
            "questions_metier_count": len(questions_mtp.get("questions_metier", [])),
            "questions_talent_count": len(questions_mtp.get("questions_talent", [])),
            "questions_paradigme_count": len(questions_mtp.get("questions_paradigme", [])),
            "total_questions_count": (
                len(questions_mtp.get("questions_metier", [])) +
                len(questions_mtp.get("questions_talent", [])) +
                len(questions_mtp.get("questions_paradigme", []))
            ),
            
            # ========== METADATA ==========
            "created_at": job_offer.get("created_at"),
        }
    
    def _build_fact_application(
        self,
        application: Dict[str, Any],
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Construit la table de faits Candidature (centrale).
        
        Clés étrangères: candidate_id, job_offer_id
        Clé primaire: application_id
        
        Contient:
        - Références vers dimensions (clés étrangères)
        - Réponses MTP du candidat
        - Références professionnelles
        - Métriques et KPIs
        - Liens vers documents PDF
        
        Returns:
            Fact table application
        """
        mtp_answers = application.get("mtp_answers", {}) or {}
        
        # Construire les références de documents PDF
        document_refs = []
        for doc in documents:
            doc_type = doc.get("document_type", "unknown")
            # Le chemin sera généré par le service Blob Storage
            document_refs.append({
                "document_type": doc_type,
                "file_name": doc.get("file_name"),
                "file_size_bytes": doc.get("file_size", 0),
                "ready_for_ocr": True,
                "uploaded_at": doc.get("uploaded_at")
            })
        
        return {
            # ========== CLÉS ==========
            "application_id": application.get("id"),  # PK
            "candidate_id": application.get("candidate_id"),  # FK → dim_candidates
            "job_offer_id": application.get("job_offer_id"),  # FK → dim_job_offers
            
            # ========== STATUS & WORKFLOW ==========
            "status": application.get("status"),
            "has_been_manager": application.get("has_been_manager"),
            
            # ========== RÉFÉRENCES PROFESSIONNELLES (pour externes) ==========
            "ref_entreprise": application.get("ref_entreprise"),
            "ref_fullname": application.get("ref_fullname"),
            "ref_mail": application.get("ref_mail"),
            "ref_contact": application.get("ref_contact"),
            "reference_contacts": application.get("reference_contacts"),
            
            # ========== RÉPONSES MTP ==========
            "mtp_answers": mtp_answers,
            "reponses_metier": mtp_answers.get("reponses_metier", []),
            "reponses_talent": mtp_answers.get("reponses_talent", []),
            "reponses_paradigme": mtp_answers.get("reponses_paradigme", []),
            
            # ========== MÉTRIQUES & KPIs ==========
            "reponses_metier_count": len(mtp_answers.get("reponses_metier", [])),
            "reponses_talent_count": len(mtp_answers.get("reponses_talent", [])),
            "reponses_paradigme_count": len(mtp_answers.get("reponses_paradigme", [])),
            "total_reponses_count": (
                len(mtp_answers.get("reponses_metier", [])) +
                len(mtp_answers.get("reponses_talent", [])) +
                len(mtp_answers.get("reponses_paradigme", []))
            ),
            "documents_count": len(documents),
            "total_documents_size_bytes": sum(doc.get("file_size", 0) for doc in documents),
            
            # ========== DOCUMENTS (références vers PDF dans Blob) ==========
            "documents": document_refs,
            
            # ========== DATES & TIMESTAMPS ==========
            "availability_start": application.get("availability_start"),
            "created_at": application.get("created_at"),
            "updated_at": application.get("updated_at"),
            
            # ========== METADATA ==========
            "application_year": application.get("created_at", "")[:4] if application.get("created_at") else None,
            "application_month": application.get("created_at", "")[:7] if application.get("created_at") else None,
            "application_date": application.get("created_at", "")[:10] if application.get("created_at") else None,
        }
    
    async def export_star_schema(
        self,
        application: Dict[str, Any],
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Export complet en architecture Star Schema.
        
        Exporte 3 tables vers Blob Storage:
        1. dim_candidates.jsonl - Dimension candidats (user + profile)
        2. dim_job_offers.jsonl - Dimension offres
        3. fact_applications.jsonl - Table de faits avec clés étrangères
        4. documents/*.pdf - PDFs séparés pour OCR
        
        Args:
            application: Données complètes de la candidature
            documents: Liste des documents avec bytes
        
        Returns:
            Résultats de l'export (URLs, chemins, tailles)
        """
        try:
            application_id = application.get("id")
            ingestion_date = datetime.now(timezone.utc)
            date_str = ingestion_date.strftime("%Y-%m-%d")
            
            results = {
                "dim_candidate": None,
                "dim_job_offer": None,
                "fact_application": None,
                "documents": [],
                "total_size_bytes": 0
            }
            
            # =================================================================
            # 1. DIMENSION CANDIDAT (user + candidate_profile dénormalisé)
            # =================================================================
            dim_candidate = self._build_dim_candidate(
                application,
                application.get("candidate_profile")
            )
            
            dim_candidate_path = f"dimensions/dim_candidates/ingestion_date={date_str}/{dim_candidate['candidate_id']}.json"
            dim_candidate_json = json.dumps(dim_candidate, ensure_ascii=False, indent=2)
            
            blob_client = self.blob_service.container_client.get_blob_client(dim_candidate_path)
            blob_client.upload_blob(
                dim_candidate_json,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json", content_encoding="utf-8"),
                metadata={"table": "dim_candidates", "pk": str(dim_candidate['candidate_id']) if dim_candidate.get('candidate_id') else "null", "ingestion_date": date_str}
            )
            
            results["dim_candidate"] = {
                "path": dim_candidate_path,
                "size_bytes": len(dim_candidate_json)
            }
            results["total_size_bytes"] += len(dim_candidate_json)
            
            logger.info("Dimension candidat exportée", candidate_id=dim_candidate['candidate_id'], path=dim_candidate_path)
            
            # =================================================================
            # 2. DIMENSION OFFRE D'EMPLOI
            # =================================================================
            dim_job_offer = self._build_dim_job_offer(application)
            
            dim_job_offer_path = f"dimensions/dim_job_offers/ingestion_date={date_str}/{dim_job_offer['job_offer_id']}.json"
            dim_job_offer_json = json.dumps(dim_job_offer, ensure_ascii=False, indent=2)
            
            blob_client = self.blob_service.container_client.get_blob_client(dim_job_offer_path)
            blob_client.upload_blob(
                dim_job_offer_json,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json", content_encoding="utf-8"),
                metadata={"table": "dim_job_offers", "pk": str(dim_job_offer['job_offer_id']) if dim_job_offer.get('job_offer_id') else "null", "ingestion_date": date_str}
            )
            
            results["dim_job_offer"] = {
                "path": dim_job_offer_path,
                "size_bytes": len(dim_job_offer_json)
            }
            results["total_size_bytes"] += len(dim_job_offer_json)
            
            logger.info("Dimension offre exportée", job_offer_id=dim_job_offer['job_offer_id'], path=dim_job_offer_path)
            
            # =================================================================
            # 3. FACT TABLE APPLICATION (avec FKs vers dimensions)
            # =================================================================
            fact_application = self._build_fact_application(application, documents)
            
            # Enrichir avec les chemins des documents PDF pour référence
            pdf_paths = []
            for doc in documents:
                doc_type = doc.get("document_type", "unknown")
                file_name = doc.get("file_name", f"{doc_type}.pdf")
                pdf_path = f"documents/ingestion_date={date_str}/{application_id}/{doc_type}_{file_name}"
                pdf_paths.append({
                    "document_type": doc_type,
                    "blob_path": pdf_path,
                    "file_name": file_name,
                    "size_bytes": doc.get("file_size", 0)
                })
            
            fact_application["document_blob_paths"] = pdf_paths
            
            fact_application_path = f"facts/fact_applications/ingestion_date={date_str}/{application_id}.json"
            fact_application_json = json.dumps(fact_application, ensure_ascii=False, indent=2)
            
            blob_client = self.blob_service.container_client.get_blob_client(fact_application_path)
            blob_client.upload_blob(
                fact_application_json,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json", content_encoding="utf-8"),
                metadata={
                    "table": "fact_applications",
                    "pk": str(application_id),
                    "fk_candidate": str(dim_candidate['candidate_id']) if dim_candidate.get('candidate_id') else "null",
                    "fk_job_offer": str(dim_job_offer['job_offer_id']) if dim_job_offer.get('job_offer_id') else "null",
                    "ingestion_date": date_str
                }
            )
            
            results["fact_application"] = {
                "path": fact_application_path,
                "size_bytes": len(fact_application_json)
            }
            results["total_size_bytes"] += len(fact_application_json)
            
            logger.info("Fact application exportée", application_id=application_id, path=fact_application_path)
            
            # =================================================================
            # 4. DOCUMENTS PDF (pour OCR)
            # =================================================================
            
            for doc in documents:
                try:
                    doc_type = doc.get("document_type", "unknown")
                    file_name = doc.get("file_name", f"{doc_type}.pdf")
                    file_data = doc.get("file_data")  # bytes
                    
                    if not file_data:
                        logger.warning("Document sans file_data, ignoré", application_id=application_id, document_type=doc_type)
                        continue
                    
                    # Chemin: documents/YYYY-MM-DD/{application_id}/{doc_type}_{filename}
                    pdf_path = f"documents/ingestion_date={date_str}/{application_id}/{doc_type}_{file_name}"
                    
                    blob_client = self.blob_service.container_client.get_blob_client(pdf_path)
                    blob_client.upload_blob(
                        file_data,
                        overwrite=True,
                        content_settings=ContentSettings(content_type="application/pdf"),
                        metadata={
                            "application_id": str(application_id),
                            "candidate_id": str(dim_candidate['candidate_id']) if dim_candidate.get('candidate_id') else "null",
                            "document_type": str(doc_type),
                            "ready_for_ocr": "true",
                            "ingestion_date": date_str
                        }
                    )
                    
                    doc_info = {
                        "document_type": doc_type,
                        "blob_path": pdf_path,
                        "size_bytes": len(file_data) if isinstance(file_data, bytes) else 0
                    }
                    
                    results["documents"].append(doc_info)
                    results["total_size_bytes"] += doc_info["size_bytes"]
                    
                    logger.info(
                        "PDF exporté pour OCR",
                        application_id=application_id,
                        document_type=doc_type,
                        path=pdf_path,
                        size_bytes=doc_info["size_bytes"]
                    )
                    
                except Exception as e:
                    logger.error(
                        "Erreur export document PDF",
                        application_id=application_id,
                        document_type=doc.get("document_type"),
                        error=str(e)
                    )
                    # Continue avec les autres documents
            
            # =================================================================
            # RÉSUMÉ DE L'EXPORT
            # =================================================================
            logger.info(
                "Export Star Schema complet",
                application_id=application_id,
                candidate_id=dim_candidate['candidate_id'],
                job_offer_id=dim_job_offer['job_offer_id'],
                tables_exported=3,
                documents_exported=len(results["documents"]),
                total_size_mb=round(results["total_size_bytes"] / 1024 / 1024, 2)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Erreur lors de l'export Star Schema",
                application_id=application.get("id"),
                error=str(e),
                error_type=type(e).__name__
            )
            raise

