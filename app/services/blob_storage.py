"""
Service ETL temps réel vers Azure Blob Storage
Architecture: Clean Code + Event-Driven + Data Lake (Raw/Curated/Features)
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from azure.storage.blob import BlobServiceClient, ContentSettings
import structlog

logger = structlog.get_logger(__name__)


class BlobStorageService:
    """
    Service pour exporter les données vers Azure Blob Storage en temps réel.
    
    Architecture Data Lake:
    - raw/ : Données brutes (JSON original)
    - curated/ : Données nettoyées et enrichies
    - features/ : Features pour ML/Analytics
    
    Partitioning:
    - Par date d'ingestion (YYYY-MM-DD)
    - Par run_id pour traçabilité
    - Par type d'entité (applications, users, etc.)
    """
    
    def __init__(
        self,
        connection_string: str,
        container_name: str = "raw"
    ):
        """
        Initialise le client Blob Storage.
        
        Args:
            connection_string: Connection string Azure Storage
            container_name: Nom du conteneur (raw, curated, features)
        """
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)
    
    def _generate_blob_path(
        self,
        entity_type: str,
        entity_id: str,
        ingestion_date: Optional[datetime] = None
    ) -> str:
        """
        Génère le chemin du blob selon les conventions Data Lake.
        
        Format: {entity_type}/ingestion_date={YYYY-MM-DD}/{entity_id}.json
        
        Args:
            entity_type: Type d'entité (applications, users, job_offers, etc.)
            entity_id: ID unique de l'entité
            ingestion_date: Date d'ingestion (default: now)
        
        Returns:
            Chemin complet du blob
        """
        if ingestion_date is None:
            ingestion_date = datetime.now(timezone.utc)
        
        date_str = ingestion_date.strftime("%Y-%m-%d")
        return f"{entity_type}/ingestion_date={date_str}/{entity_id}.json"
    
    async def export_application_with_documents(
        self,
        application_data: Dict[str, Any],
        application_id: str,
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Exporte une candidature COMPLÈTE vers Blob Storage :
        1. JSON avec toutes les infos (candidat, candidature, offre)
        2. PDF séparés (pour OCR ultérieur)
        
        Args:
            application_data: Données complètes de la candidature
            application_id: ID de la candidature
            documents: Liste des documents (avec file_data en bytes)
        
        Returns:
            Dict avec blob_urls et metadata
        
        Raises:
            Exception si l'export échoue
        """
        try:
            ingestion_date = datetime.now(timezone.utc)
            date_str = ingestion_date.strftime("%Y-%m-%d")
            
            results = {
                "json_export": None,
                "pdf_exports": [],
                "total_size_bytes": 0
            }
            
            # ========================================================================
            # 1. EXPORT JSON - Toutes les informations (sans les bytes PDF)
            # ========================================================================
            
            # Nettoyer les documents (retirer file_data pour le JSON)
            cleaned_application_data = application_data.copy()
            
            # Enrichir avec metadata d'ingestion
            enriched_data = {
                "_metadata": {
                    "entity_type": "application",
                    "entity_id": application_id,
                    "ingestion_timestamp": ingestion_date.isoformat(),
                    "source": "seeg-api",
                    "version": "1.0",
                    "has_documents": documents is not None and len(documents) > 0,
                    "documents_count": len(documents) if documents else 0
                },
                **cleaned_application_data
            }
            
            # Chemin JSON
            json_blob_path = f"applications/ingestion_date={date_str}/json/{application_id}.json"
            
            # Convertir en JSON
            json_content = json.dumps(enriched_data, ensure_ascii=False, indent=2)
            
            # Upload JSON
            json_blob_client = self.container_client.get_blob_client(json_blob_path)
            
            json_blob_client.upload_blob(
                json_content,
                overwrite=True,
                content_settings=ContentSettings(
                    content_type="application/json",
                    content_encoding="utf-8"
                ),
                metadata={
                    "entity_type": "application",
                    "entity_id": application_id,
                    "ingestion_date": date_str,
                    "format": "json"
                }
            )
            
            results["json_export"] = {
                "blob_url": json_blob_client.url,
                "blob_path": json_blob_path,
                "size_bytes": len(json_content)
            }
            results["total_size_bytes"] += len(json_content)
            
            logger.info(
                "JSON exporté vers Blob Storage",
                application_id=application_id,
                blob_path=json_blob_path,
                size_bytes=len(json_content)
            )
            
            # ========================================================================
            # 2. EXPORT PDF - Chaque document séparément (pour OCR)
            # ========================================================================
            
            if documents:
                for doc in documents:
                    try:
                        doc_type = doc.get("document_type", "unknown")
                        file_name = doc.get("file_name", f"{doc_type}.pdf")
                        file_data = doc.get("file_data")  # bytes
                        
                        if not file_data:
                            logger.warning(
                                "Document sans file_data, ignoré",
                                application_id=application_id,
                                document_type=doc_type
                            )
                            continue
                        
                        # Chemin PDF : applications/YYYY-MM-DD/documents/{application_id}/{document_type}.pdf
                        pdf_blob_path = f"applications/ingestion_date={date_str}/documents/{application_id}/{doc_type}_{file_name}"
                        
                        # Upload PDF
                        pdf_blob_client = self.container_client.get_blob_client(pdf_blob_path)
                        
                        pdf_blob_client.upload_blob(
                            file_data,
                            overwrite=True,
                            content_settings=ContentSettings(
                                content_type="application/pdf"
                            ),
                            metadata={
                                "entity_type": "application_document",
                                "application_id": application_id,
                                "document_type": doc_type,
                                "ingestion_date": date_str,
                                "ready_for_ocr": "true"
                            }
                        )
                        
                        pdf_export_info = {
                            "document_type": doc_type,
                            "blob_url": pdf_blob_client.url,
                            "blob_path": pdf_blob_path,
                            "size_bytes": len(file_data) if isinstance(file_data, bytes) else 0
                        }
                        
                        results["pdf_exports"].append(pdf_export_info)
                        results["total_size_bytes"] += pdf_export_info["size_bytes"]
                        
                        logger.info(
                            "PDF exporté pour OCR",
                            application_id=application_id,
                            document_type=doc_type,
                            blob_path=pdf_blob_path,
                            size_bytes=pdf_export_info["size_bytes"]
                        )
                        
                    except Exception as e:
                        logger.error(
                            "Erreur lors de l'export d'un document PDF",
                            application_id=application_id,
                            document_type=doc.get("document_type"),
                            error=str(e)
                        )
                        # Continue avec les autres documents
            
            logger.info(
                "Export complet réussi",
                application_id=application_id,
                json_exported=True,
                pdfs_exported=len(results["pdf_exports"]),
                total_size_mb=round(results["total_size_bytes"] / 1024 / 1024, 2)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Erreur lors de l'export complet vers Blob Storage",
                application_id=application_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def export_batch(
        self,
        entity_type: str,
        entities: List[Dict[str, Any]],
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exporte un batch d'entités en format JSON Lines.
        
        Args:
            entity_type: Type d'entités (applications, users, etc.)
            entities: Liste des entités à exporter
            run_id: ID du run (généré automatiquement si None)
        
        Returns:
            Metadata de l'export
        """
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        try:
            ingestion_date = datetime.now(timezone.utc)
            date_str = ingestion_date.strftime("%Y-%m-%d")
            
            # Chemin avec partitioning
            blob_path = f"{entity_type}/ingestion_date={date_str}/run_id={run_id}/data.jsonl"
            
            # Convertir en JSON Lines (une ligne JSON par entité)
            json_lines = "\n".join([
                json.dumps(entity, ensure_ascii=False)
                for entity in entities
            ])
            
            # Upload
            blob_client = self.container_client.get_blob_client(blob_path)
            
            content_settings = ContentSettings(
                content_type="application/jsonl",
                content_encoding="utf-8"
            )
            
            blob_client.upload_blob(
                json_lines,
                overwrite=True,
                content_settings=content_settings,
                metadata={
                    "entity_type": entity_type,
                    "run_id": run_id,
                    "count": str(len(entities)),
                    "ingestion_date": date_str
                }
            )
            
            logger.info(
                "Batch exporté vers Blob Storage",
                entity_type=entity_type,
                count=len(entities),
                run_id=run_id,
                blob_path=blob_path
            )
            
            return {
                "blob_url": blob_client.url,
                "blob_path": blob_path,
                "run_id": run_id,
                "count": len(entities),
                "size_bytes": len(json_lines)
            }
            
        except Exception as e:
            logger.error(
                "Erreur lors de l'export batch",
                entity_type=entity_type,
                count=len(entities),
                error=str(e)
            )
            raise

