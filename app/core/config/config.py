"""
Configuration de l'application
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Configuration de base
    APP_NAME: str = "One HCM SEEG Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Base de données
    DATABASE_URL: str = "postgresql+asyncpg://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
    DATABASE_URL_SYNC: str = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
    
    # Configuration de sécurité
    SECRET_KEY: str = "your-super-secret-key-here-change-in-production-123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Configuration CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://www.seeg-talentsource.com"]
    ALLOWED_CREDENTIALS: bool = True
    
    # Configuration email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    MAIL_FROM_NAME: str = "One HCM - SEEG"
    MAIL_FROM_EMAIL: str = "noreply@seeg.ga"
    
    # Configuration Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Configuration de monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    
    # Configuration de stockage de fichiers
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "doc", "docx", "jpg", "jpeg", "png"]
    
    # Configuration Azure Storage (optionnel)
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "documents"
    
    # Configuration de rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Configuration de maintenance
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "Le système est en maintenance. Veuillez réessayer plus tard."
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


# Instance globale des paramètres
settings = Settings()
