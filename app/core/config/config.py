"""
Configuration de l'application
"""
from typing import List, Optional, Union
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
    
    # Base de données - Utilisation des variables d'environnement
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres",
        description="URL de connexion à la base de données PostgreSQL"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres",
        description="URL de connexion synchrone à la base de données PostgreSQL"
    )
    
    # Configuration de sécurité - Variables d'environnement obligatoires
    SECRET_KEY: str = Field(
        default="your-super-secret-key-here-change-in-production-123456789",
        min_length=32,
        description="Clé secrète pour la signature des tokens JWT"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Configuration CORS - Peut être une liste ou une chaîne séparée par des virgules
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173", "https://www.seeg-talentsource.com"]
    ALLOWED_CREDENTIALS: bool = True
    
    # Configuration email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "support@seeg-talentsource.com"
    SMTP_PASSWORD: str = "njev urja zsbc spfn"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    MAIL_FROM_NAME: str = "One HCM - SEEG Talent Source"
    MAIL_FROM_EMAIL: str = "support@seeg-talentsource.com"
    
    # Configuration application
    PUBLIC_APP_URL: str = "http://localhost:3000"
    
    # Configuration Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Configuration de logging
    LOG_LEVEL: str = "INFO"
    
    # Configuration des workers
    WORKERS: int = 4
    MAX_REQUESTS: int = 1000
    MAX_REQUESTS_JITTER: int = 100
    TIMEOUT_KEEP_ALIVE: int = 5
    TIMEOUT_GRACEFUL_SHUTDOWN: int = 30
    
    # Configuration Azure
    WEBSITES_PORT: int = 8000
    
    @field_validator('ALLOWED_ORIGINS')
    @classmethod
    def validate_allowed_origins(cls, v):
        """Valider et convertir ALLOWED_ORIGINS en liste"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        """Valider la clé secrète"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY doit contenir au moins 32 caractères")
        if v == "your-super-secret-key-here-change-in-production-123456789":
            import warnings
            warnings.warn("SECRET_KEY par défaut détectée. Changez-la en production !")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instance globale des paramètres
settings = Settings()
