"""
Configuration de l'application One HCM SEEG
============================================================================
Architecture: Clean Configuration avec principes SOLID + 12-Factor App
- Single Responsibility: Chaque setting a un rôle précis
- Open/Closed: Extensible via variables d'environnement
- Dependency Inversion: Configuration injectée, pas hardcodée
- Environment Parity: Même code, différents environnements
============================================================================

Hiérarchie de priorité (du plus au moins prioritaire):
1. Variables d'environnement système (ex: export DATABASE_URL=...)
2. Fichiers .env spécifiques (.env.production, .env.local)
3. Fichier .env par défaut
4. Valeurs par défaut dans le code

Cette hiérarchie respecte le principe des 12-Factor Apps.
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
    1. Variable ENVIRONMENT explicite (la plus haute priorité)
    2. Variable WEBSITE_SITE_NAME (Azure App Service)
    3. Défaut: development
    
    Returns:
        'production' si Azure ou ENVIRONMENT=production
        'development' sinon
    """
    # 1. Variable explicite (priorité maximale)
    env = os.getenv('ENVIRONMENT', '').lower()
    if env in ['production', 'prod']:
        print(f"[INFO] Detection: ENVIRONMENT={env} (explicite)")
        return 'production'
    elif env == 'development' or env == 'dev':
        print(f"[INFO] Detection: ENVIRONMENT={env} (explicite)")
        return 'development'
    
    # 2. Détection Azure App Service
    website_name = os.getenv('WEBSITE_SITE_NAME', '')
    website_instance = os.getenv('WEBSITE_INSTANCE_ID', '')
    
    if website_name == 'seeg-backend-api' or website_instance:
        print(f"[INFO] Detection: Azure App Service ({website_name})")
        return 'production'
    
    # 3. Défaut: développement
    print(f"[INFO] Detection: Developpement LOCAL")
    return 'development'


def get_env_files() -> tuple[Optional[str], Optional[str]]:
    """
    Retourne les fichiers .env à charger selon l'environnement.
    
    Pydantic Settings charge les fichiers dans l'ordre : le dernier a priorité.
    Les variables d'environnement système ont TOUJOURS priorité sur les fichiers.
    
    Returns:
        Tuple (fichier_base, fichier_specifique)
        - fichier_base: .env (toujours)
        - fichier_specifique: .env.production ou .env.local (selon environnement)
    """
    env = detect_environment()
    env_file_base = '.env' if os.path.exists('.env') else None
    env_file_specific = None
    
    if env == 'production':
        if os.path.exists('.env.production'):
            env_file_specific = '.env.production'
            print(f"[INFO] Chargement: .env + .env.production")
        else:
            print(f"[INFO] Chargement: .env (defaut)")
    else:
        if os.path.exists('.env.local'):
            env_file_specific = '.env.local'
            print(f"[INFO] Chargement: .env + .env.local")
        else:
            print(f"[INFO] Chargement: .env (defaut)")
    
    return (env_file_base, env_file_specific)


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application.
    Suit le principe de Separation of Concerns et 12-Factor App.
    
    ORDRE DE PRIORITÉ (du plus au moins prioritaire):
    1. Variables d'environnement système
    2. Fichier .env.{environment} (.env.production ou .env.local)
    3. Fichier .env
    4. Valeurs par défaut ci-dessous
    """
    
    # Configuration Pydantic v2
    # Note: env_file charge plusieurs fichiers, le dernier écrase le premier
    # MAIS les variables d'environnement système ont toujours priorité
    model_config = SettingsConfigDict(
        # Ne pas spécifier env_file ici, on le gère manuellement via env_file dans __init__
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
        # env_nested_delimiter="__",  # Pour support de variables imbriquées
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
    # SKIP_MIGRATIONS - Pour déploiements séparés
    # ========================================================================
    
    SKIP_MIGRATIONS: bool = Field(
        default=True,
        description="Si True, ne pas exécuter les migrations au démarrage"
    )
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    
    RATE_LIMIT_ENABLED: bool = Field(default=False)
    CREATE_INITIAL_USERS: bool = Field(default=False)
    
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
            warnings.warn("[WARNING] SECRET_KEY par defaut utilisee. Changez-la en production!")
        
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
                "[WARNING] DEBUG=True en production peut exposer des informations sensibles!"
            )
        
        return self


# ============================================================================
# FACTORY FUNCTION - Création avec support multi-fichiers
# ============================================================================

def create_settings() -> Settings:
    """
    Factory pour créer Settings avec le bon chargement de fichiers .env.
    
    Charge les fichiers dans l'ordre suivant:
    1. .env (base, valeurs communes)
    2. .env.{environment} (.env.production ou .env.local, spécifique)
    3. Variables d'environnement système (priorité maximale, automatique)
    
    Returns:
        Instance Settings configurée
    """
    env_file_base, env_file_specific = get_env_files()
    
    # Construire la liste des fichiers à charger
    env_files = []
    if env_file_base:
        env_files.append(env_file_base)
    if env_file_specific:
        env_files.append(env_file_specific)
    
    # Créer la configuration avec les bons fichiers
    # Pydantic Settings charge dans l'ordre et les variables système ont priorité
    if env_files:
        # Pydantic v2 utilise model_config mais on peut aussi passer à __init__
        # Pour avoir le contrôle, on met à jour le model_config dynamiquement
        Settings.model_config['env_file'] = tuple(env_files)
    
    return Settings()


# ============================================================================
# INSTANCE GLOBALE - Singleton Pattern
# ============================================================================

settings = create_settings()

# Afficher un résumé au démarrage
print(f"[INFO] Configuration chargee: {settings.ENVIRONMENT}")
print(f"   - App: {settings.APP_NAME} v{settings.APP_VERSION}")
print(f"   - Debug: {settings.DEBUG}")
print(f"   - Database: {settings.DATABASE_URL[:50]}...")
print(f"   - CORS Origins: {len(settings.ALLOWED_ORIGINS) if isinstance(settings.ALLOWED_ORIGINS, list) else settings.ALLOWED_ORIGINS}")
print(f"[INFO] Variables système ont priorite sur fichiers .env")
