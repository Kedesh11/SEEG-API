"""
Service pour la gestion des fichiers
"""
from typing import List, Optional, Dict, Any, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from datetime import datetime, timezone
import structlog
import aiofiles
import os
import uuid
import mimetypes
from pathlib import Path
import hashlib

from app.models.application import ApplicationDocument
from app.core.config.config import settings
from app.core.exceptions import FileError, ValidationError

logger = structlog.get_logger(__name__)


class FileService:
    """Service pour la gestion des fichiers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        application_id: str,
        document_type: str,
        uploaded_by: str
    ) -> Dict[str, Any]:
        """
        TÃ©lÃ©charger un fichier
        
        Args:
            file_content: Contenu du fichier
            filename: Nom du fichier
            application_id: ID de la candidature
            document_type: Type de document
            uploaded_by: ID de l'utilisateur qui tÃ©lÃ©charge
            
        Returns:
            Dict contenant les informations du fichier tÃ©lÃ©chargÃ©
            
        Raises:
            FileError: Si le tÃ©lÃ©chargement Ã©choue
            ValidationError: Si les donnÃ©es sont invalides
        """
        try:
            # Validation de la taille du fichier
            file_size = len(file_content)
            if file_size > settings.MAX_FILE_SIZE:
                raise ValidationError(f"Le fichier est trop volumineux. Taille maximale: {settings.MAX_FILE_SIZE} bytes")
            
            # Validation du type de fichier
            file_extension = Path(filename).suffix.lower().lstrip('.')
            if file_extension not in settings.ALLOWED_FILE_TYPES:
                raise ValidationError(f"Type de fichier non autorisÃ©. Types autorisÃ©s: {', '.join(settings.ALLOWED_FILE_TYPES)}")
            
            # GÃ©nÃ©ration d'un nom de fichier unique
            file_id = str(uuid.uuid4())
            safe_filename = self._sanitize_filename(filename)
            unique_filename = f"{file_id}_{safe_filename}"
            
            # Chemin de stockage
            file_path = self.upload_dir / unique_filename
            
            # Calcul du hash du fichier
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # DÃ©termination du type MIME
            mime_type, _ = mimetypes.guess_type(filename)
            
            # Sauvegarde du fichier
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Enregistrement en base de donnÃ©es
            document = ApplicationDocument(
                application_id=application_id,
                filename=filename,
                file_path=str(file_path),
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                document_type=document_type,
                uploaded_by=uploaded_by,
                uploaded_at=datetime.now(timezone.utc)
            )
            
            self.db.add(document)
            #  PAS de commit ici
            await self.db.refresh(document)
            
            logger.info(
                "File uploaded successfully",
                file_id=str(document.id),
                filename=filename,
                file_size=file_size,
                application_id=application_id
            )
            
            return {
                "id": str(document.id),
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "document_type": document_type,
                "uploaded_at": document.uploaded_at,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            # Nettoyage du fichier en cas d'erreur
            if 'file_path' in locals() and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            
            logger.error(
                "Failed to upload file",
                filename=filename,
                application_id=application_id,
                error=str(e)
            )
            raise FileError(f"Ã‰chec du tÃ©lÃ©chargement du fichier: {str(e)}")
    
    async def get_file(self, document_id: str) -> Dict[str, Any]:
        """
        RÃ©cupÃ©rer les informations d'un fichier
        
        Args:
            document_id: ID du document
            
        Returns:
            Dict contenant les informations du fichier
            
        Raises:
            FileError: Si le fichier n'existe pas
        """
        result = await self.db.execute(
            select(ApplicationDocument).where(ApplicationDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise FileError(f"Document avec l'ID {document_id} non trouvÃ©")
        
        # VÃ©rification de l'existence du fichier
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise FileError(f"Le fichier physique n'existe pas: {document.file_path}")
        
        return {
            "id": str(document.id),
            "filename": document.filename,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "document_type": document.document_type,
            "uploaded_at": document.uploaded_at,
            "file_path": document.file_path
        }
    
    async def download_file(self, document_id: str) -> bytes:
        """
        TÃ©lÃ©charger le contenu d'un fichier
        
        Args:
            document_id: ID du document
            
        Returns:
            bytes: Contenu du fichier
            
        Raises:
            FileError: Si le fichier n'existe pas ou ne peut pas Ãªtre lu
        """
        result = await self.db.execute(
            select(ApplicationDocument).where(ApplicationDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise FileError(f"Document avec l'ID {document_id} non trouvÃ©")
        
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise FileError(f"Le fichier physique n'existe pas: {document.file_path}")
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            logger.info(
                "File downloaded",
                document_id=document_id,
                filename=document.filename,
                file_size=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to download file",
                document_id=document_id,
                error=str(e)
            )
            raise FileError(f"Impossible de lire le fichier: {str(e)}")
    
    async def delete_file(self, document_id: str, deleted_by: str) -> bool:
        """
        Supprimer un fichier
        
        Args:
            document_id: ID du document
            deleted_by: ID de l'utilisateur qui supprime
            
        Returns:
            bool: True si la suppression a rÃ©ussi
            
        Raises:
            FileError: Si le fichier n'existe pas
        """
        try:
            result = await self.db.execute(
                select(ApplicationDocument).where(ApplicationDocument.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise FileError(f"Document avec l'ID {document_id} non trouvÃ©")
            
            file_path = Path(document.file_path)
            
            # Suppression du fichier physique
            if file_path.exists():
                file_path.unlink()
            
            # Suppression de l'enregistrement en base
            await self.db.execute(
                delete(ApplicationDocument).where(ApplicationDocument.id == document_id)
            )
            #  PAS de commit ici
            
            logger.info(
                "File deleted",
                document_id=document_id,
                filename=document.filename,
                deleted_by=deleted_by
            )
            
            return True
            
        except Exception as e:
            #  PAS de rollback ici - géré par get_db()
            logger.error(
                "Failed to delete file",
                document_id=document_id,
                error=str(e)
            )
            raise FileError(f"Ã‰chec de la suppression du fichier: {str(e)}")
    
    async def get_application_files(self, application_id: str) -> List[Dict[str, Any]]:
        """
        RÃ©cupÃ©rer tous les fichiers d'une candidature
        
        Args:
            application_id: ID de la candidature
            
        Returns:
            List[Dict]: Liste des fichiers
        """
        result = await self.db.execute(
            select(ApplicationDocument)
            .where(ApplicationDocument.application_id == application_id)
            .order_by(ApplicationDocument.uploaded_at.desc())
        )
        
        documents = result.scalars().all()
        
        return [
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "document_type": doc.document_type,
                "uploaded_at": doc.uploaded_at
            }
            for doc in documents
        ]
    
    async def get_file_statistics(self) -> Dict[str, Any]:
        """
        RÃ©cupÃ©rer les statistiques des fichiers
        
        Returns:
            Dict contenant les statistiques
        """
        from sqlalchemy import func
        
        # Nombre total de fichiers
        total_result = await self.db.execute(select(func.count(ApplicationDocument.id)))
        total_files = total_result.scalar()
        
        # Taille totale des fichiers
        size_result = await self.db.execute(select(func.sum(ApplicationDocument.file_size)))
        total_size = size_result.scalar() or 0
        
        # Statistiques par type de document
        type_result = await self.db.execute(
            select(
                ApplicationDocument.document_type,
                func.count(ApplicationDocument.id),
                func.sum(ApplicationDocument.file_size)
            )
            .group_by(ApplicationDocument.document_type)
        )
        
        type_stats = {}
        for row in type_result.fetchall():
            type_stats[row[0]] = {
                "count": row[1],
                "total_size": row[2] or 0
            }
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "type_distribution": type_stats
        }
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Nettoyer le nom de fichier pour la sÃ©curitÃ©
        
        Args:
            filename: Nom de fichier original
            
        Returns:
            str: Nom de fichier nettoyÃ©
        """
        # Suppression des caractÃ¨res dangereux
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_filename = filename
        
        for char in dangerous_chars:
            safe_filename = safe_filename.replace(char, '_')
        
        # Limitation de la longueur
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:255-len(ext)] + ext
        
        return safe_filename
    
    async def cleanup_orphaned_files(self) -> int:
        """
        Nettoyer les fichiers orphelins (sans enregistrement en base)
        
        Returns:
            int: Nombre de fichiers supprimÃ©s
        """
        try:
            # RÃ©cupÃ©ration de tous les fichiers en base
            result = await self.db.execute(select(ApplicationDocument.file_path))
            db_files = {Path(row[0]) for row in result.fetchall()}
            
            # RÃ©cupÃ©ration de tous les fichiers physiques
            physical_files = set(self.upload_dir.glob('*'))
            
            # Identification des fichiers orphelins
            orphaned_files = physical_files - db_files
            
            # Suppression des fichiers orphelins
            deleted_count = 0
            for file_path in orphaned_files:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info("Orphaned file deleted", file_path=str(file_path))
                except Exception as e:
                    logger.error("Failed to delete orphaned file", file_path=str(file_path), error=str(e))
            
            logger.info("Orphaned files cleanup completed", deleted_count=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup orphaned files", error=str(e))
            return 0
