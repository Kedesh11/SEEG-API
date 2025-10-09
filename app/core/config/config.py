"""
Configuration de l'application One HCM SEEG
============================================================================
Architecture: Clean Configuration avec principes SOLID
- Single Responsibility: Chaque setting a un rôle précis
- Open/Closed: Extensible via variables d'environnement
- Dependency Inversion: Configuration injectée, pas hardcodée
============================================================================
"""
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import warnings


def detect_environment() -> str:
    """
    Détecte automatiquement l'environnement d'exécution.
    
    Priorité de détection:
    1. Variable WEBSITE_SITE_NAME (Azure App Service)
    2. Variable ENVIRONMENT explicite
    3. Défaut: development
    
    Returns:
        'production' si Azure ou ENVIRONMENT=production
        'development' sinon
    """
    # Détection Azure App Service
    website_name = os.getenv('WEBSITE_SITE_NAME', '')
    website_instance = os.getenv('WEBSITE_INSTANCE_ID', '')
    
    if website_name == 'seeg-backend-api' or website_instance:
        print(f"✅ Détection: Azure App Service ({website_name})")
        return 'production'
    
    # Détection variable explicite
    env = os.getenv('ENVIRONMENT', '').lower()
    if env in ['production', 'prod']:
        print(f"✅ Détection: ENVIRONMENT={env}")
        return 'production'
    
    # Défaut: développement
    print(f"✅ Détection: Développement LOCAL")
    return 'development'


def get_env_file() -> str:
    """
    Retourne le fichier .env approprié selon l'environnement.
    
    Returns:
        Chemin vers .env.production en prod, .env.local en dev, sinon .env
    """
    env = detect_environment()
    
    if env == 'production':
        if os.path.exists('.env.production'):
            print(f"📄 Chargement: .env.production")
            return '.env.production'
    else:
        if os.path.exists('.env.local'):
            print(f"📄 Chargement: .env.local")
            return '.env.local'
    
    print(f"📄 Chargement: .env (défaut)")
    return '.env'


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application.
    Suit le principe de Separation of Concerns.
    """
    
    # Configuration Pydantic v2
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True
    )
    
    # ========================================================================
    # APPLICATION - Configuration de base
    # ========================================================================
    
    APP_NAME: str = Field(
        default="One HCM SEEG Backend",
        description="Nom de l'application"
    )
    
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Version de l'application"
    )
    
    DEBUG: bool = Field(
        default_factory=lambda: detect_environment() == 'development',
        description="Mode debug (auto-détecté)"
    )
    
    ENVIRONMENT: str = Field(
        default_factory=detect_environment,
        description="Environnement d'exécution"
    )
    
    # ========================================================================
    # DATABASE - Configuration dynamique selon environnement
    # ========================================================================
    
    DATABASE_URL: str = Field(
        default_factory=lambda: (
            "postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres"
            if detect_environment() == 'production'
            else "postgresql+asyncpg://postgres:postgres@localhost:5432/recruteur"
        ),
        description="URL asynchrone PostgreSQL"
    )
    
    DATABASE_URL_SYNC: str = Field(
        default_factory=lambda: (
            "postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres"
            if detect_environment() == 'production'
            else "postgresql://postgres:postgres@localhost:5432/recruteur"
        ),
        description="URL synchrone PostgreSQL (pour Alembic)"
    )
    
    # ========================================================================
    # SECURITY - JWT & Encryption
    # ========================================================================
    
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv(
            'SECRET_KEY',
            'DEV_KEY_CHANGE_IN_PROD_32CHARS_MINIMUM_1234567890'
        ),
        min_length=32,
        description="Clé secrète JWT (minimum 32 caractères)"
    )
    
    ALGORITHM: str = Field(default="HS256", description="Algorithme JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    JWT_ISSUER: str = Field(default="seeg-api")
    JWT_AUDIENCE: str = Field(default="seeg-clients")
    
    # ========================================================================
    # MONITORING - Logs, Tracing, Metrics
    # ========================================================================
    
    ENABLE_TRACING: bool = Field(default=True)
    METRICS_ENABLED: bool = Field(default=True)
    LOG_FORMAT: str = Field(default="json", pattern="^(json|text)$")
    LOG_LEVEL: str = Field(
        default_factory=lambda: "DEBUG" if detect_environment() == 'development' else "INFO"
    )
    
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = Field(
        default=None,
        description="Azure Application Insights"
    )
    
    # ========================================================================
    # CORS - Configuration adaptative
    # ========================================================================
    
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default_factory=lambda: (
            ["https://www.seeg-talentsource.com", "https://seeg-hcm.vercel.app"]
            if detect_environment() == 'production'
            else ["http://localhost:3000", "http://localhost:5173", "https://www.seeg-talentsource.com"]
        ),
        description="Origines CORS autorisées"
    )
    
    ALLOWED_CREDENTIALS: bool = Field(default=True)
    
    # ========================================================================
    # EMAIL - SMTP Configuration
    # ========================================================================
    
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_TLS: bool = Field(default=True)
    SMTP_SSL: bool = Field(default=False)
    SMTP_USERNAME: str = Field(default="support@seeg-talentsource.com")
    SMTP_PASSWORD: str = Field(default="njev urja zsbc spfn")
    MAIL_FROM_EMAIL: str = Field(default="support@seeg-talentsource.com")
    MAIL_FROM_NAME: str = Field(default="One HCM - SEEG Talent Source")
    
    # ========================================================================
    # FRONTEND - URL publique
    # ========================================================================
    
    PUBLIC_APP_URL: str = Field(
        default_factory=lambda: (
            "https://www.seeg-talentsource.com"
            if detect_environment() == 'production'
            else "http://localhost:3000"
        )
    )
    
    # ========================================================================
    # CACHE - Redis (optionnel en production)
    # ========================================================================
    
    REDIS_URL: str = Field(
        default_factory=lambda: (
            os.getenv('REDIS_URL', '')  # Vide par défaut en prod
            if detect_environment() == 'production'
            else 'redis://localhost:6379/0'
        ),
        description="URL Redis pour cache (optionnel)"
    )
    
    CELERY_BROKER_URL: str = Field(
        default_factory=lambda: os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    
    CELERY_RESULT_BACKEND: str = Field(
        default_factory=lambda: os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    # ========================================================================
    # WORKERS & PERFORMANCE
    # ========================================================================
    
    WORKERS: int = Field(default=4, ge=1, le=32)
    MAX_REQUESTS: int = Field(default=1000, ge=100)
    MAX_REQUESTS_JITTER: int = Field(default=100, ge=0)
    TIMEOUT_KEEP_ALIVE: int = Field(default=5, ge=1)
    TIMEOUT_GRACEFUL_SHUTDOWN: int = Field(default=30, ge=5)
    
    # ========================================================================
    # AZURE - App Service Configuration
    # ========================================================================
    
    WEBSITES_PORT: int = Field(default=8000, ge=1, le=65535)
    
    # ========================================================================
    # VALIDATORS - Validation stricte pour production
    # ========================================================================
    
    @field_validator('ALLOWED_ORIGINS')
    @classmethod
    def validate_allowed_origins(cls, v):
        """Convertir ALLOWED_ORIGINS en liste si string."""
        if isinstance(v, str):
            # Support pour "*" ou liste séparée par virgules
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        """Valider la sécurité de SECRET_KEY."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY doit contenir au moins 32 caractères")
        
        # Clés faibles interdites
        weak_keys = [
            "your-super-secret-key-here-change-in-production-123456789",
            "CHANGE_ME_SECRET_KEY_32CHARS_MINIMUM_1234567890",
            "DEV_KEY_CHANGE_IN_PROD_32CHARS_MINIMUM_1234567890"
        ]
        
        if v in weak_keys and detect_environment() == 'production':
            raise ValueError("SECRET_KEY par défaut détectée en production! Changez-la immédiatement.")
        
        if v in weak_keys:
            warnings.warn("⚠️  SECRET_KEY par défaut utilisée. Changez-la en production!")
        
        return v
    
    @model_validator(mode='after')
    def validate_cors_credentials(self):
        """Valider la cohérence CORS: si origins='*', credentials doit être False."""
        if isinstance(self.ALLOWED_ORIGINS, list) and "*" in self.ALLOWED_ORIGINS:
            if self.ALLOWED_CREDENTIALS:
                warnings.warn(
                    "CORS: ALLOWED_ORIGINS='*' avec ALLOWED_CREDENTIALS=True peut causer des erreurs. "
                    "Forcé à False automatiquement."
                )
                self.ALLOWED_CREDENTIALS = False
        return self
    
    @model_validator(mode='after')
    def validate_production_security(self):
        """Validations de sécurité supplémentaires en production."""
        if self.ENVIRONMENT != 'production':
            return self
        
        # Vérifier que la DB n'est pas localhost
        if "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL ne doit pas pointer vers localhost en production!"
            )
        
        # Recommandation DEBUG
        if self.DEBUG:
            warnings.warn(
                "⚠️  DEBUG=True en production peut exposer des informations sensibles!"
            )
        
        return self


# ============================================================================
# INSTANCE GLOBALE - Singleton Pattern
# ============================================================================

settings = Settings()

# Afficher un résumé au démarrage
print(f"✅ Configuration chargée: {settings.ENVIRONMENT}")
print(f"   - App: {settings.APP_NAME} v{settings.APP_VERSION}")
print(f"   - Debug: {settings.DEBUG}")
print(f"   - Database: {settings.DATABASE_URL[:50]}...")
print(f"   - CORS Origins: {len(settings.ALLOWED_ORIGINS) if isinstance(settings.ALLOWED_ORIGINS, list) else settings.ALLOWED_ORIGINS}")
