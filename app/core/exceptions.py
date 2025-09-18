"""
Exceptions personnalisées pour l'application
"""
from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Exception de base pour l'application"""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Erreur de validation des données"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 422)


class NotFoundError(BaseAppException):
    """Erreur de ressource non trouvée"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 404)


class UnauthorizedError(BaseAppException):
    """Erreur d'autorisation"""
    
    def __init__(self, message: str = "Non autorisé", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 401)


class ForbiddenError(BaseAppException):
    """Erreur d'accès interdit"""
    
    def __init__(self, message: str = "Accès interdit", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 403)


class ConflictError(BaseAppException):
    """Erreur de conflit"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 409)


class BusinessLogicError(BaseAppException):
    """Erreur de logique métier"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 400)


class EmailError(BaseAppException):
    """Erreur d'envoi d'email"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 500)


class FileError(BaseAppException):
    """Erreur de gestion de fichier"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 500)


class DatabaseError(BaseAppException):
    """Erreur de base de données"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 500)


class RateLimitError(BaseAppException):
    """Erreur de limite de taux"""
    
    def __init__(self, message: str = "Limite de taux dépassée", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 429)


class MaintenanceError(BaseAppException):
    """Erreur de maintenance"""
    
    def __init__(self, message: str = "Service en maintenance", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, 503)
