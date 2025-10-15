"""
Exceptions personnalisées pour l'application
Suit le principe de hiérarchie d'exceptions et de séparation des préoccupations
"""
from typing import Optional, Dict, Any


class ApplicationError(Exception):
    """Classe de base pour toutes les exceptions de l'application"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir l'exception en dictionnaire pour la réponse API"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


# Exceptions de validation
class ValidationError(ApplicationError):
    """Erreur de validation des données"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class DataIntegrityError(ApplicationError):
    """Erreur d'intégrité des données"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DATA_INTEGRITY_ERROR", **kwargs)


# Exceptions de ressources
class NotFoundError(ApplicationError):
    """Ressource non trouvée"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, error_code="NOT_FOUND", details=details)


class AlreadyExistsError(ApplicationError):
    """Ressource existe déjà"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(message, error_code="ALREADY_EXISTS", details=details)


# Exceptions d'autorisation
class AuthenticationError(ApplicationError):
    """Erreur d'authentification"""
    
    def __init__(self, message: str = "Authentification échouée", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(ApplicationError):
    """Erreur d'autorisation"""
    
    def __init__(self, message: str = "Accès non autorisé", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


# Alias pour compatibilité
class UnauthorizedError(AuthenticationError):
    """Alias pour AuthenticationError (compatibilité)"""
    pass


class EmailError(ApplicationError):
    """Erreur liée à l'envoi d'email"""
    
    def __init__(self, message: str, recipient: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if recipient:
            details["recipient"] = recipient
        super().__init__(message, error_code="EMAIL_ERROR", details=details)


# Exceptions de logique métier
class BusinessLogicError(ApplicationError):
    """Erreur de logique métier"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="BUSINESS_LOGIC_ERROR", **kwargs)


class InvalidStateError(ApplicationError):
    """État invalide pour l'opération"""
    
    def __init__(self, message: str, current_state: Optional[str] = None, expected_state: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        super().__init__(message, error_code="INVALID_STATE", details=details)


# Exceptions de base de données
class DatabaseError(ApplicationError):
    """Erreur de base de données"""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class DatabaseConnectionError(DatabaseError):
    """Erreur de connexion à la base de données"""
    
    def __init__(self, message: str = "Erreur de connexion à la base de données", **kwargs):
        super().__init__(message, error_code="DATABASE_CONNECTION_ERROR", **kwargs)


# Exceptions de fichiers et documents
class FileError(ApplicationError):
    """Erreur liée aux fichiers"""
    
    def __init__(self, message: str, filename: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if filename:
            details["filename"] = filename
        super().__init__(message, error_code="FILE_ERROR", details=details)


class FileSizeError(FileError):
    """Erreur de taille de fichier"""
    
    def __init__(self, message: str, max_size: Optional[int] = None, actual_size: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if max_size:
            details["max_size"] = max_size
        if actual_size:
            details["actual_size"] = actual_size
        super().__init__(message, error_code="FILE_SIZE_ERROR", details=details)


class FileTypeError(FileError):
    """Erreur de type de fichier"""
    
    def __init__(self, message: str, allowed_types: Optional[list] = None, actual_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if allowed_types:
            details["allowed_types"] = allowed_types
        if actual_type:
            details["actual_type"] = actual_type
        super().__init__(message, error_code="FILE_TYPE_ERROR", details=details)


# Exceptions de services externes
class ExternalServiceError(ApplicationError):
    """Erreur de service externe"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", details=details)


# Exceptions de configuration
class ConfigurationError(ApplicationError):
    """Erreur de configuration"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


# Mapping des exceptions vers les codes HTTP
EXCEPTION_HTTP_STATUS_MAP = {
    ValidationError: 400,
    DataIntegrityError: 400,
    NotFoundError: 404,
    AlreadyExistsError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    BusinessLogicError: 422,
    InvalidStateError: 422,
    DatabaseError: 500,
    DatabaseConnectionError: 503,
    FileError: 400,
    FileSizeError: 413,
    FileTypeError: 415,
    ExternalServiceError: 502,
    ConfigurationError: 500,
    ApplicationError: 500,
}


def get_http_status_code(exception: ApplicationError) -> int:
    """
    Obtenir le code HTTP approprié pour une exception
    
    Args:
        exception: Exception de l'application
        
    Returns:
        Code HTTP approprié
    """
    return EXCEPTION_HTTP_STATUS_MAP.get(type(exception), 500)
