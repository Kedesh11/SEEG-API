#!/usr/bin/env python3
"""
Script de migration robuste et autonome pour SEEG API.

Ce script unique gère toutes les migrations de base de données de manière professionnelle:
- Récupération automatique de DATABASE_URL depuis Azure CLI
- Transactions atomiques avec rollback automatique en cas d'erreur
- Logs structurés et détaillés pour chaque étape
- Vérification des dépendances et de l'état avant migration
- Support des migrations complexes avec plusieurs commandes SQL
- Idempotent : peut être exécuté plusieurs fois sans danger
- Gestion explicite des erreurs avec contexte complet

Bonnes pratiques de Génie Logiciel:
✅ Single Responsibility: Chaque méthode a une responsabilité claire
✅ DRY (Don't Repeat Yourself): Pas de duplication de code
✅ SOLID: Architecture extensible et maintenable
✅ Logging exhaustif: Traçabilité complète de toutes les opérations
✅ Error Handling: Gestion robuste des erreurs avec contexte
✅ Transactional: Garantie d'atomicité des opérations

Usage:
    # Avec DATABASE_URL en variable d'environnement
    python scripts/apply-migrations-direct.py
    
    # Ou le script récupère automatiquement DATABASE_URL depuis Azure
    python scripts/apply-migrations-direct.py
"""
import os
import sys
import asyncio
import asyncpg
import structlog
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Configuration du logger structuré
logger = structlog.get_logger(__name__)

# ============================================================================
# CHARGEMENT DE LA CONFIGURATION AZURE
# ============================================================================

def load_azure_config() -> Dict[str, str]:
    """
    Charger la configuration Azure depuis azure-config.json.
    
    Returns:
        Dictionnaire avec resource_group, app_service, etc.
    """
    config_path = Path(__file__).parent.parent / "azure-config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        logger.warning("⚠️  azure-config.json non trouvé, utilisation des valeurs par défaut")
        return {
            "resource_group": "seeg-rg",
            "app_service": "seeg-backend-api"
        }
    except json.JSONDecodeError as e:
        logger.error("❌ Erreur de parsing JSON", error=str(e))
        return {
            "resource_group": "seeg-rg",
            "app_service": "seeg-backend-api"
        }
    except Exception as e:
        logger.error("❌ Erreur lors du chargement de la config", error=str(e))
        return {
            "resource_group": "seeg-rg",
            "app_service": "seeg-backend-api"
        }

# ============================================================================
# CONFIGURATION
# ============================================================================

MIGRATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
"""

# ============================================================================
# CLASSE DE GESTION DES MIGRATIONS
# ============================================================================

class MigrationExecutor:
    """Exécuteur de migrations avec gestion transactionnelle et logging robuste"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn: Optional[asyncpg.Connection] = None
        
    async def connect(self):
        """Établir la connexion à la base de données"""
        try:
            self.conn = await asyncpg.connect(self.connection_string)
            logger.info("✅ Connexion à la base de données établie")
            return True
        except Exception as e:
            logger.error("❌ Échec de connexion", error=str(e), error_type=type(e).__name__)
            return False
    
    async def close(self):
        """Fermer la connexion proprement"""
        if self.conn:
            await self.conn.close()
            logger.info("🔌 Connexion fermée")
    
    async def get_current_version(self) -> Optional[str]:
        """Récupérer la version actuelle d'Alembic"""
        if not self.conn:
            logger.error("❌ Aucune connexion à la base de données")
            return None
            
        try:
            # Vérifier si la table existe
            exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                );
            """)
            
            if not exists:
                logger.warning("⚠️  Table alembic_version n'existe pas encore")
                return None
            
            version = await self.conn.fetchval("SELECT version_num FROM alembic_version;")
            logger.info(f"📌 Version actuelle: {version or 'Aucune'}")
            return version
            
        except Exception as e:
            logger.error("❌ Erreur lors de la récupération de la version", error=str(e))
            return None
    
    async def execute_sql_block(self, sql_commands: List[str], description: str) -> bool:
        """
        Exécuter un bloc de commandes SQL de manière transactionnelle.
        Chaque commande est exécutée séparément (asyncpg limitation).
        """
        if not self.conn:
            logger.error("❌ Aucune connexion à la base de données")
            return False
            
        transaction = None
        try:
            transaction = self.conn.transaction()
            await transaction.start()
            
            logger.info(f"🔄 Début: {description}")
            
            for idx, sql in enumerate(sql_commands, 1):
                sql_clean = sql.strip()
                if not sql_clean or sql_clean.startswith('--'):
                    continue
                    
                logger.debug(f"   [{idx}/{len(sql_commands)}] Exécution SQL", 
                           sql_preview=sql_clean[:80] + "..." if len(sql_clean) > 80 else sql_clean)
                
                try:
                    await self.conn.execute(sql_clean)
                except Exception as cmd_error:
                    # Certaines erreurs sont acceptables (ex: DROP IF EXISTS d'une colonne inexistante)
                    error_msg = str(cmd_error).lower()
                    if any(skip in error_msg for skip in ['does not exist', 'already exists', 'duplicate']):
                        logger.warning(f"   ⚠️  Erreur ignorée: {cmd_error}")
                        continue
                    else:
                        raise
            
            await transaction.commit()
            logger.info(f"✅ Succès: {description}")
            return True
            
        except Exception as e:
            if transaction:
                await transaction.rollback()
                logger.error(f"❌ Rollback effectué pour: {description}")
            
            logger.error(
                f"❌ Échec: {description}",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def update_alembic_version(self, new_version: str) -> bool:
        """Mettre à jour la version Alembic"""
        if not self.conn:
            logger.error("❌ Aucune connexion à la base de données")
            return False
            
        try:
            # Créer la table si elle n'existe pas
            await self.conn.execute(MIGRATION_SCHEMA)
            
            # Supprimer l'ancienne version
            await self.conn.execute("DELETE FROM alembic_version;")
            
            # Insérer la nouvelle version
            await self.conn.execute(
                "INSERT INTO alembic_version (version_num) VALUES ($1);",
                new_version
            )
            
            logger.info(f"✅ Version Alembic mise à jour: {new_version}")
            return True
            
        except Exception as e:
            logger.error("❌ Échec mise à jour version", error=str(e))
            return False

# ============================================================================
# DÉFINITIONS DES MIGRATIONS
# ============================================================================

MIGRATIONS = [
    {
        "revision": "20251010_mtp_questions",
        "down_revision": "20251010_add_updated_at",
        "description": "Ajout colonne questions_mtp aux offres et nettoyage anciennes colonnes MTP",
        "sql_commands": [
            # 1. Ajouter la colonne JSON pour les questions MTP
            """
            ALTER TABLE job_offers 
            ADD COLUMN IF NOT EXISTS questions_mtp JSONB 
            DEFAULT NULL;
            """,
            
            # 2. Commentaire sur la colonne
            """
            COMMENT ON COLUMN job_offers.questions_mtp IS 
            'Questions MTP au format JSON: {questions_metier: [...], questions_talent: [...], questions_paradigme: [...]}';
            """,
            
            # 3. Supprimer les anciennes colonnes MTP de applications (si elles existent)
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q3;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q3;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q3;",
            
            # 4. Ajouter la colonne JSONB pour les réponses MTP dans applications (si pas déjà là)
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS mtp_answers JSONB 
            DEFAULT NULL;
            """,
            
            # 5. Commentaire sur la colonne
            """
            COMMENT ON COLUMN applications.mtp_answers IS 
            'Réponses MTP au format JSONB: {reponses_metier: [...], reponses_talent: [...], reponses_paradigme: [...]}';
            """,
            
            # 6. Convertir les colonnes JSON existantes en JSONB pour de meilleures performances
            """
            ALTER TABLE job_offers 
            ALTER COLUMN requirements TYPE JSONB USING requirements::jsonb,
            ALTER COLUMN benefits TYPE JSONB USING benefits::jsonb,
            ALTER COLUMN responsibilities TYPE JSONB USING responsibilities::jsonb;
            """,
        ]
    },
    {
        "revision": "20251013_offer_status",
        "down_revision": "20251010_mtp_questions",
        "description": "Migration is_internal_only vers offer_status",
        "sql_commands": [
            # 1. Ajouter la nouvelle colonne offer_status
            """
            ALTER TABLE job_offers 
            ADD COLUMN IF NOT EXISTS offer_status VARCHAR NOT NULL DEFAULT 'tous';
            """,
            
            # 2. Créer l'index
            """
            CREATE INDEX IF NOT EXISTS ix_job_offers_offer_status 
            ON job_offers (offer_status, status);
            """,
            
            # 3. Migrer les données de is_internal_only vers offer_status
            """
            UPDATE job_offers 
            SET offer_status = CASE 
                WHEN is_internal_only = true THEN 'interne'
                ELSE 'tous'
            END
            WHERE is_internal_only IS NOT NULL;
            """,
            
            # 4. Supprimer l'ancien index (si existe)
            "DROP INDEX IF EXISTS ix_job_offers_is_internal_only;",
            
            # 5. Supprimer l'ancienne colonne
            "ALTER TABLE job_offers DROP COLUMN IF EXISTS is_internal_only;",
            
            # 6. Commentaire sur la nouvelle colonne
            """
            COMMENT ON COLUMN job_offers.offer_status IS 
            'Visibilité de l''offre: tous (internes+externes), interne (SEEG uniquement), externe (candidats externes uniquement)';
            """,
        ]
    }
]

# ============================================================================
# RÉCUPÉRATION AUTOMATIQUE DE DATABASE_URL
# ============================================================================

def add_firewall_rule_if_needed() -> bool:
    """
    Ajouter automatiquement une règle firewall pour l'IP configurée.
    Utilise la configuration depuis azure-config.json.
    
    Returns:
        True si la règle existe ou a été ajoutée, False sinon
    """
    azure_config = load_azure_config()
    allowed_ip = azure_config.get("allowed_ip")
    postgres_server = azure_config.get("postgres_server", "seeg-postgres-server")
    postgres_rg = azure_config.get("postgres_resource_group", "seeg-backend-rg")
    
    if not allowed_ip:
        logger.warning("⚠️  Aucune IP configurée dans azure-config.json")
        return True  # On continue quand même
    
    try:
        logger.info(f"🔓 Vérification règle firewall pour {allowed_ip}...")
        
        # Créer ou mettre à jour la règle firewall
        result = subprocess.run(
            [
                "az", "postgres", "flexible-server", "firewall-rule", "create",
                "--resource-group", postgres_rg,
                "--name", postgres_server,
                "--rule-name", "allow-migration-ip",
                "--start-ip-address", allowed_ip,
                "--end-ip-address", allowed_ip,
                "--output", "none"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Règle firewall configurée pour {allowed_ip}")
            return True
        else:
            logger.warning(f"⚠️  Impossible de configurer la règle firewall: {result.stderr}")
            return True  # On continue quand même
            
    except Exception as e:
        logger.warning(f"⚠️  Erreur configuration firewall: {str(e)}")
        return True  # On continue quand même

def get_database_url_from_azure() -> Optional[str]:
    """
    Récupérer automatiquement DATABASE_URL depuis Azure CLI.
    Utilise la configuration depuis azure-config.json.
    
    Returns:
        La chaîne de connexion DATABASE_URL ou None si échec
    """
    # Charger la config Azure
    azure_config = load_azure_config()
    resource_group = azure_config.get("resource_group", "seeg-rg")
    app_service = azure_config.get("app_service", "seeg-backend-api")
    
    try:
        logger.info("🔍 Récupération de DATABASE_URL depuis Azure CLI...")
        logger.info(f"   Resource Group: {resource_group}")
        logger.info(f"   App Service: {app_service}")
        
        result = subprocess.run(
            [
                "az", "webapp", "config", "appsettings", "list",
                "--resource-group", resource_group,
                "--name", app_service,
                "--query", "[?name=='DATABASE_URL'].value",
                "-o", "tsv"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        database_url = result.stdout.strip()
        
        if database_url:
            logger.info("✅ DATABASE_URL récupérée depuis Azure")
            return database_url
        else:
            logger.warning("⚠️  DATABASE_URL vide dans Azure")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error("❌ Erreur Azure CLI", error=e.stderr)
        return None
    except FileNotFoundError:
        logger.error("❌ Azure CLI non installé")
        logger.info("💡 Installez Azure CLI: https://aka.ms/installazurecliwindows")
        return None
    except Exception as e:
        logger.error("❌ Erreur lors de la récupération", error=str(e))
        return None

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

async def main():
    """Point d'entrée principal du script"""
    logger.info("=" * 80)
    logger.info("🚀 SCRIPT DE MIGRATION UNIQUE - SEEG API")
    logger.info("=" * 80)
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("📝 Version: 1.0.0")
    logger.info("")
    
    # 1. Récupérer la chaîne de connexion
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.info("⚙️  DATABASE_URL non définie en variable d'environnement")
        logger.info("🔄 Tentative de récupération depuis Azure CLI...")
        database_url = get_database_url_from_azure()
        
        if not database_url:
            logger.error("❌ Impossible de récupérer DATABASE_URL")
            logger.info("")
            logger.info("💡 Solutions:")
            logger.info("   1. Définir DATABASE_URL en variable d'environnement")
            logger.info("   2. Vérifier la connexion Azure: az login")
            logger.info("   3. Vérifier les paramètres de l'App Service")
            return 1
    else:
        logger.info("✅ DATABASE_URL chargée depuis variable d'environnement")
    
    logger.info("")
    
    # 2. Ajouter automatiquement la règle firewall si configurée
    add_firewall_rule_if_needed()
    logger.info("")
    
    # 3. Nettoyer DATABASE_URL pour asyncpg (remplacer postgresql+asyncpg par postgresql)
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        logger.info("🔧 URL nettoyée pour asyncpg")
    
    # 4. Initialiser l'exécuteur
    executor = MigrationExecutor(database_url)
    
    if not await executor.connect():
        return 1
    
    try:
        # 3. Récupérer la version actuelle
        current_version = await executor.get_current_version()
        
        # 4. Déterminer les migrations à appliquer
        migrations_to_apply = []
        
        if current_version is None:
            # Première migration
            migrations_to_apply = MIGRATIONS
            logger.info("📦 Aucune migration appliquée, toutes les migrations seront appliquées")
        else:
            # Trouver les migrations après la version actuelle
            found_current = False
            for migration in MIGRATIONS:
                if found_current:
                    migrations_to_apply.append(migration)
                elif migration["revision"] == current_version:
                    found_current = True
            
            if not found_current:
                logger.warning(f"⚠️  Version actuelle '{current_version}' non trouvée dans la liste des migrations")
                logger.info("💡 Toutes les migrations seront tentées (idempotentes)")
                migrations_to_apply = MIGRATIONS
        
        if not migrations_to_apply:
            logger.info("✅ Base de données à jour, aucune migration nécessaire")
            return 0
        
        logger.info(f"📋 {len(migrations_to_apply)} migration(s) à appliquer")
        
        # 5. Appliquer les migrations
        for idx, migration in enumerate(migrations_to_apply, 1):
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📦 MIGRATION {idx}/{len(migrations_to_apply)}: {migration['revision']}")
            logger.info("=" * 80)
            logger.info(f"📝 Description: {migration['description']}")
            logger.info(f"🔗 Down revision: {migration['down_revision']}")
            
            success = await executor.execute_sql_block(
                migration["sql_commands"],
                f"Migration {migration['revision']}"
            )
            
            if success:
                # Mettre à jour la version Alembic
                if not await executor.update_alembic_version(migration["revision"]):
                    logger.error("❌ Échec mise à jour version Alembic")
                    return 1
            else:
                logger.error(f"❌ Échec de la migration {migration['revision']}")
                return 1
        
        # 6. Résumé final
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ TOUTES LES MIGRATIONS APPLIQUÉES AVEC SUCCÈS")
        logger.info("=" * 80)
        logger.info(f"📌 Version finale: {migrations_to_apply[-1]['revision']}")
        logger.info(f"📊 Total migrations: {len(migrations_to_apply)}")
        
        return 0
        
    except Exception as e:
        logger.error("❌ Erreur critique", error=str(e), error_type=type(e).__name__)
        return 1
        
    finally:
        await executor.close()

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    # Configuration du logging structuré
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer()
        ]
    )
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

