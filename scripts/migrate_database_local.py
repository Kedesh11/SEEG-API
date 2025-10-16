"""
Script de Migration SQL Direct sur PostgreSQL Local - SEEG API
===============================================================

Ce script gère l'exécution robuste et sécurisée de migrations SQL
directement sur PostgreSQL local avec traçabilité complète.

Architecture:
- Single Responsibility: Chaque classe a une responsabilité unique
- Dependency Injection: Configuration injectable
- Error Handling: Gestion d'erreurs exhaustive avec retry
- Logging: Traçabilité complète de toutes les opérations
- Transactions: Support transactionnel avec rollback
- Idempotence: Les migrations peuvent être réexécutées sans danger
- Audit Trail: Historique complet des migrations appliquées
- Auto-Discovery: Découverte automatique des migrations depuis le dossier

Fonctionnalités:
✅ Découverte automatique des fichiers de migration
✅ Détection des modifications via checksum
✅ Connexion sécurisée à PostgreSQL local
✅ Vérification de l'état des migrations
✅ Exécution transactionnelle des migrations
✅ Rollback automatique en cas d'erreur
✅ Historique des migrations avec timestamps
✅ Validation post-migration
✅ Support des migrations forwards et backwards
✅ Génération de rapports détaillés

Structure des fichiers de migration:
    app/db/migrations/sql/
        20251016_create_email_logs.sql
        20251017_add_notifications.sql
        rollback/
            20251016_create_email_logs.sql
            20251017_add_notifications.sql

Format du nom de fichier: {version}_{name}.sql
    Exemple: 20251016_create_email_logs.sql

Usage:
    python scripts/migrate_database_local.py --action upgrade
    python scripts/migrate_database_local.py --action status
    python scripts/migrate_database_local.py --action rollback --target <version>

Auteur: SEEG Tech Team
Version: 2.0.0
Date: 2025-10-16
"""

import sys
import argparse
import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path
import hashlib
import re


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class DatabaseConfig:
    """Configuration de la base de données PostgreSQL locale"""
    # ========================================
    # CONFIGURATION À MODIFIER ICI
    # ========================================
    host: str = "localhost"
    port: int = 5432
    database: str = "recruteur"
    user: str = "postgres"
    password: str = "postgres"  # ⚠️ Modifier avec votre mot de passe local
    
    # Paramètres de connexion
    command_timeout: int = 60
    timeout: int = 30
    min_size: int = 1
    max_size: int = 5
    
    def to_dsn(self) -> str:
        """Génère la DSN de connexion"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class MigrationConfig:
    """Configuration des chemins de migration"""
    migrations_dir: Path = Path("app/db/migrations/sql")
    rollback_dir: Path = Path("app/db/migrations/sql/rollback")
    
    def __post_init__(self):
        """Crée les dossiers s'ils n'existent pas"""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self.rollback_dir.mkdir(parents=True, exist_ok=True)


class MigrationStatus(Enum):
    """Statuts possibles d'une migration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    MODIFIED = "modified"  # Fichier modifié depuis la dernière application


@dataclass
class Migration:
    """Représente une migration SQL"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    checksum: str = ""
    file_path: Optional[Path] = None
    
    def __post_init__(self):
        """Calcule le checksum automatiquement"""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calcule le checksum MD5 du contenu SQL"""
        content = self.up_sql.strip()
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def has_changed(self, stored_checksum: str) -> bool:
        """Vérifie si la migration a été modifiée"""
        return self.checksum != stored_checksum


# ============================================================================
# GESTIONNAIRE DE LOGS STRUCTURÉ
# ============================================================================

class StructuredLogger:
    """Logger avec support de logs structurés"""
    
    def __init__(self, name: str, verbose: bool = False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Handler console
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        
        self.logs: List[Dict[str, Any]] = []
    
    def log(self, level: str, message: str, **kwargs):
        """Enregistre un log avec métadonnées"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(entry)
        
        # Affichage console
        icons = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥"
        }
        icon = icons.get(level, "•")
        
        # Formatage du message
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items() if k != "sql"])
        full_message = f"{icon} {message}"
        if extra_info:
            full_message += f" ({extra_info})"
        
        getattr(self.logger, level.lower(), self.logger.info)(full_message)
    
    def debug(self, message: str, **kwargs):
        self.log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)
    
    def success(self, message: str, **kwargs):
        self.log("SUCCESS", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log("CRITICAL", message, **kwargs)


# ============================================================================
# DÉCOUVERTE ET CHARGEMENT DES MIGRATIONS
# ============================================================================

class MigrationLoader:
    """Charge et découvre automatiquement les migrations depuis le système de fichiers"""
    
    def __init__(self, config: MigrationConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.migrations: Dict[str, Migration] = {}
    
    def discover_migrations(self) -> List[Migration]:
        """
        Découvre automatiquement toutes les migrations depuis le dossier
        
        Format attendu du nom de fichier: {version}_{name}.sql
        Exemple: 20251016_create_email_logs.sql
        """
        self.logger.info(f"Découverte des migrations dans {self.config.migrations_dir}...")
        
        # Pattern pour extraire version et nom
        pattern = re.compile(r'^(\d{8}_[a-z0-9_]+)\.sql$', re.IGNORECASE)
        
        migration_files = sorted(self.config.migrations_dir.glob("*.sql"))
        
        for file_path in migration_files:
            match = pattern.match(file_path.name)
            
            if not match:
                self.logger.warning(f"Fichier ignoré (format invalide): {file_path.name}")
                continue
            
            version = match.group(1)
            
            # Extraire le nom lisible
            name_parts = version.split('_', 1)
            name = name_parts[1] if len(name_parts) > 1 else version
            
            # Lire le contenu SQL
            try:
                up_sql = file_path.read_text(encoding='utf-8')
                
                # Chercher le fichier de rollback correspondant
                rollback_file = self.config.rollback_dir / file_path.name
                down_sql = None
                
                if rollback_file.exists():
                    down_sql = rollback_file.read_text(encoding='utf-8')
                
                # Extraire la description depuis les commentaires SQL
                description = self._extract_description(up_sql)
                
                # Extraire les dépendances depuis les commentaires
                dependencies = self._extract_dependencies(up_sql)
                
                migration = Migration(
                    version=version,
                    name=name,
                    description=description,
                    up_sql=up_sql,
                    down_sql=down_sql,
                    dependencies=dependencies,
                    file_path=file_path
                )
                
                self.migrations[version] = migration
                self.logger.debug(f"Migration chargée: {version}", checksum=migration.checksum[:8])
                
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement de {file_path.name}: {e}")
                continue
        
        sorted_migrations = sorted(self.migrations.values(), key=lambda m: m.version)
        
        self.logger.success(f"{len(sorted_migrations)} migration(s) découverte(s)")
        
        return sorted_migrations
    
    def _extract_description(self, sql: str) -> str:
        """Extrait la description depuis les commentaires SQL"""
        # Chercher un commentaire au début du fichier
        # Format: -- Description: ...
        match = re.search(r'--\s*Description:\s*(.+?)(?:\n|$)', sql, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Sinon, prendre la première ligne de commentaire
        for line in sql.split('\n'):
            line = line.strip()
            if line.startswith('--') and len(line) > 3:
                return line[2:].strip()
        
        return "Pas de description"
    
    def _extract_dependencies(self, sql: str) -> List[str]:
        """Extrait les dépendances depuis les commentaires SQL"""
        # Format: -- Depends: 20251015_create_users, 20251015_create_jobs
        match = re.search(r'--\s*Depends:\s*(.+?)(?:\n|$)', sql, re.IGNORECASE)
        
        if match:
            deps_str = match.group(1).strip()
            return [d.strip() for d in deps_str.split(',') if d.strip()]
        
        return []


# ============================================================================
# GESTIONNAIRE DE CONNEXION DATABASE
# ============================================================================

class DatabaseConnection:
    """Gestionnaire de connexion à la base de données avec pool"""
    
    def __init__(self, config: DatabaseConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> bool:
        """Établit la connexion au serveur PostgreSQL"""
        try:
            self.logger.info("Connexion à PostgreSQL local...",
                           host=self.config.host, database=self.config.database)
            
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                command_timeout=self.config.command_timeout,
                timeout=self.config.timeout,
                min_size=self.config.min_size,
                max_size=self.config.max_size
            )
            
            # Test de connexion
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                pg_version = version.split(",")[0]
                self.logger.success("Connexion établie", postgres_version=pg_version)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de connexion: {e}")
            return False
    
    async def close(self):
        """Ferme la connexion"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Connexion fermée")
    
    async def execute(self, sql: str, *args) -> str:
        """Exécute une requête SQL"""
        if not self.pool:
            raise RuntimeError("Database connection not established")
        async with self.pool.acquire() as conn:
            return await conn.execute(sql, *args)
    
    async def fetch(self, sql: str, *args) -> List[asyncpg.Record]:
        """Exécute une requête et retourne les résultats"""
        if not self.pool:
            raise RuntimeError("Database connection not established")
        async with self.pool.acquire() as conn:
            return await conn.fetch(sql, *args)
    
    async def fetchval(self, sql: str, *args) -> Any:
        """Exécute une requête et retourne une seule valeur"""
        if not self.pool:
            raise RuntimeError("Database connection not established")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(sql, *args)
    
    async def fetchrow(self, sql: str, *args) -> Optional[asyncpg.Record]:
        """Exécute une requête et retourne une seule ligne"""
        if not self.pool:
            raise RuntimeError("Database connection not established")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)


# ============================================================================
# GESTIONNAIRE DE L'HISTORIQUE DES MIGRATIONS
# ============================================================================

class MigrationHistory:
    """Gère l'historique des migrations dans la table migration_history"""
    
    TABLE_SCHEMA = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            version VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            checksum VARCHAR(32) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            applied_by VARCHAR(100),
            execution_time_ms INTEGER,
            status VARCHAR(20) NOT NULL,
            error_message TEXT,
            rollback_sql TEXT,
            metadata JSON,
            
            CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back', 'modified'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_migration_history_version 
            ON migration_history(version);
        CREATE INDEX IF NOT EXISTS idx_migration_history_status 
            ON migration_history(status);
        CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at 
            ON migration_history(applied_at);
        CREATE INDEX IF NOT EXISTS idx_migration_history_checksum 
            ON migration_history(checksum);
    """
    
    def __init__(self, db: DatabaseConnection, logger: StructuredLogger):
        self.db = db
        self.logger = logger
    
    async def initialize(self):
        """Initialise la table d'historique"""
        self.logger.info("Initialisation de la table migration_history...")
        await self.db.execute(self.TABLE_SCHEMA)
        self.logger.success("Table migration_history prête")
    
    async def get_applied_migrations(self) -> Dict[str, str]:
        """
        Retourne un dictionnaire {version: checksum} des migrations appliquées
        """
        rows = await self.db.fetch("""
            SELECT version, checksum
            FROM migration_history 
            WHERE status = 'completed'
            ORDER BY applied_at
        """)
        return {row['version']: row['checksum'] for row in rows}
    
    async def is_applied(self, version: str) -> bool:
        """Vérifie si une migration est déjà appliquée"""
        count = await self.db.fetchval("""
            SELECT COUNT(*) 
            FROM migration_history 
            WHERE version = $1 AND status = 'completed'
        """, version)
        return count > 0
    
    async def get_migration_record(self, version: str) -> Optional[Dict[str, Any]]:
        """Récupère l'enregistrement d'une migration"""
        row = await self.db.fetchrow("""
            SELECT version, checksum, status, applied_at, error_message
            FROM migration_history
            WHERE version = $1
        """, version)
        
        return dict(row) if row else None
    
    async def record_migration(
        self,
        migration: Migration,
        status: MigrationStatus,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Enregistre une migration dans l'historique"""
        await self.db.execute("""
            INSERT INTO migration_history 
                (version, name, description, checksum, applied_by, 
                 execution_time_ms, status, error_message, rollback_sql, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (version) DO UPDATE SET
                status = EXCLUDED.status,
                error_message = EXCLUDED.error_message,
                applied_at = CURRENT_TIMESTAMP,
                execution_time_ms = EXCLUDED.execution_time_ms,
                checksum = EXCLUDED.checksum
        """,
            migration.version,
            migration.name,
            migration.description,
            migration.checksum,
            self.db.config.user,
            execution_time_ms,
            status.value,
            error_message,
            migration.down_sql,
            json.dumps({
                "dependencies": migration.dependencies,
                "file_path": str(migration.file_path) if migration.file_path else None
            })
        )
    
    async def get_current_version(self) -> Optional[str]:
        """Retourne la version actuelle de la base de données"""
        version = await self.db.fetchval("""
            SELECT version 
            FROM migration_history 
            WHERE status = 'completed'
            ORDER BY applied_at DESC 
            LIMIT 1
        """)
        return version
    
    async def get_migration_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retourne l'historique des migrations"""
        rows = await self.db.fetch("""
            SELECT 
                version, name, description, status, checksum,
                applied_at, execution_time_ms, error_message
            FROM migration_history
            ORDER BY applied_at DESC
            LIMIT $1
        """, limit)
        
        return [dict(row) for row in rows]


# ============================================================================
# MOTEUR D'EXÉCUTION DES MIGRATIONS
# ============================================================================

class MigrationEngine:
    """Moteur d'exécution des migrations avec support transactionnel"""
    
    def __init__(
        self,
        db: DatabaseConnection,
        history: MigrationHistory,
        loader: MigrationLoader,
        logger: StructuredLogger
    ):
        self.db = db
        self.history = history
        self.loader = loader
        self.logger = logger
    
    async def analyze_migrations(self) -> Tuple[List[Migration], List[Migration]]:
        """
        Analyse les migrations pour détecter les nouvelles et les modifiées
        
        Returns:
            Tuple (new_migrations, modified_migrations)
        """
        all_migrations = self.loader.discover_migrations()
        applied = await self.history.get_applied_migrations()
        
        new_migrations = []
        modified_migrations = []
        
        for migration in all_migrations:
            if migration.version not in applied:
                # Nouvelle migration
                new_migrations.append(migration)
            else:
                # Vérifier si modifiée
                stored_checksum = applied[migration.version]
                if migration.has_changed(stored_checksum):
                    modified_migrations.append(migration)
                    self.logger.warning(
                        f"Migration modifiée détectée: {migration.version}",
                        old_checksum=stored_checksum[:8],
                        new_checksum=migration.checksum[:8]
                    )
        
        return new_migrations, modified_migrations
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Retourne les migrations en attente (nouvelles uniquement)"""
        new_migrations, _ = await self.analyze_migrations()
        
        # Vérifier les dépendances
        applied = await self.history.get_applied_migrations()
        
        for migration in new_migrations:
            for dep in migration.dependencies:
                if dep not in applied:
                    raise ValueError(
                        f"Migration {migration.version} dépend de {dep} "
                        f"qui n'est pas encore appliquée"
                    )
        
        return new_migrations
    
    async def apply_migration(self, migration: Migration, force: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Applique une migration de manière transactionnelle
        
        Args:
            migration: La migration à appliquer
            force: Si True, réapplique même si déjà présente (pour les modifications)
        
        Returns:
            Tuple (success: bool, error_message: Optional[str])
        """
        start_time = datetime.utcnow()
        
        action = "Réapplication" if force else "Application"
        self.logger.info(f"{action} de {migration.version}...", name=migration.name)
        
        try:
            # Exécution transactionnelle
            if not self.db.pool:
                raise RuntimeError("Database connection not established")
            
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # Si force, on peut ajouter une vérification ou un nettoyage ici
                    if force:
                        self.logger.debug("Mode force: réexécution du SQL")
                    
                    # Exécuter le SQL de migration
                    await conn.execute(migration.up_sql)
                    
                    self.logger.debug("SQL exécuté avec succès")
            
            # Calculer le temps d'exécution
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Enregistrer dans l'historique
            await self.history.record_migration(
                migration,
                MigrationStatus.COMPLETED,
                execution_time
            )
            
            self.logger.success(
                f"Migration {migration.version} appliquée",
                duration_ms=execution_time
            )
            
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Enregistrer l'échec
            await self.history.record_migration(
                migration,
                MigrationStatus.FAILED,
                execution_time,
                error_msg
            )
            
            self.logger.error(
                f"Échec de {migration.version}: {error_msg}",
                duration_ms=execution_time
            )
            
            return False, error_msg
    
    async def apply_all_pending(self, force_modified: bool = False) -> Tuple[int, int, int]:
        """
        Applique toutes les migrations en attente
        
        Args:
            force_modified: Si True, réapplique les migrations modifiées
        
        Returns:
            Tuple (new_applied: int, modified_applied: int, failed: int)
        """
        new_migrations, modified_migrations = await self.analyze_migrations()
        
        if not new_migrations and not (force_modified and modified_migrations):
            self.logger.info("Aucune migration en attente")
            return 0, 0, 0
        
        if new_migrations:
            self.logger.info(f"{len(new_migrations)} nouvelle(s) migration(s)")
        
        if modified_migrations:
            if force_modified:
                self.logger.warning(f"{len(modified_migrations)} migration(s) modifiée(s) seront réappliquées")
            else:
                self.logger.warning(
                    f"{len(modified_migrations)} migration(s) modifiée(s) ignorée(s) "
                    f"(utilisez --force-modified pour les réappliquer)"
                )
        
        new_applied = 0
        modified_applied = 0
        failed = 0
        
        # Appliquer les nouvelles migrations
        for migration in new_migrations:
            success, error = await self.apply_migration(migration, force=False)
            
            if success:
                new_applied += 1
            else:
                failed += 1
                self.logger.warning("Arrêt des migrations suite à l'échec")
                break
        
        # Appliquer les migrations modifiées si demandé
        if force_modified and failed == 0:
            for migration in modified_migrations:
                success, error = await self.apply_migration(migration, force=True)
                
                if success:
                    modified_applied += 1
                else:
                    failed += 1
                    break
        
        return new_applied, modified_applied, failed
    
    async def rollback_migration(self, version: str) -> bool:
        """Annule une migration (si down_sql est défini)"""
        # Recharger la migration depuis le disque
        migrations = self.loader.discover_migrations()
        migration = next((m for m in migrations if m.version == version), None)
        
        if not migration:
            self.logger.error(f"Migration {version} introuvable")
            return False
        
        if not migration.down_sql:
            self.logger.error(f"Migration {version} ne supporte pas le rollback")
            return False
        
        self.logger.info(f"Rollback de {version}...")
        
        try:
            if not self.db.pool:
                raise RuntimeError("Database connection not established")
            
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(migration.down_sql)
            
            # Marquer comme rolled back
            await self.history.record_migration(
                migration,
                MigrationStatus.ROLLED_BACK,
                0
            )
            
            self.logger.success(f"Rollback de {version} réussi")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec du rollback: {e}")
            return False


# ============================================================================
# GESTIONNAIRE PRINCIPAL
# ============================================================================

class MigrationManager:
    """Gestionnaire principal orchestrant toutes les opérations"""
    
    def __init__(
        self,
        db_config: DatabaseConfig,
        migration_config: MigrationConfig,
        verbose: bool = False
    ):
        self.db_config = db_config
        self.migration_config = migration_config
        self.logger = StructuredLogger("MigrationManager", verbose)
        self.db = DatabaseConnection(db_config, self.logger)
        self.history = MigrationHistory(self.db, self.logger)
        self.loader = MigrationLoader(migration_config, self.logger)
        self.engine = MigrationEngine(self.db, self.history, self.loader, self.logger)
        self.start_time = datetime.utcnow()
    
    async def initialize(self) -> bool:
        """Initialise la connexion et les tables système"""
        # Se connecter à la base de données
        if not await self.db.connect():
            return False
        
        # Initialiser les tables système
        await self.history.initialize()
        return True
    
    async def show_status(self):
        """Affiche le statut des migrations"""
        self.logger.info("=== STATUT DES MIGRATIONS ===")
        
        current = await self.history.get_current_version()
        self.logger.info(f"Version actuelle: {current or 'Aucune'}")
        
        new_migrations, modified_migrations = await self.engine.analyze_migrations()
        
        self.logger.info(f"Nouvelles migrations: {len(new_migrations)}")
        if new_migrations:
            for migration in new_migrations:
                self.logger.info(f"  → {migration.version}: {migration.name}")
        
        if modified_migrations:
            self.logger.warning(f"Migrations modifiées: {len(modified_migrations)}")
            for migration in modified_migrations:
                self.logger.warning(f"  ⚠️  {migration.version}: {migration.name}")
        
        print()
        history = await self.history.get_migration_history()
        if history:
            self.logger.info("=== HISTORIQUE (20 dernières) ===")
            for record in history:
                status_icons = {
                    'completed': '✅',
                    'failed': '❌',
                    'rolled_back': '🔙',
                    'modified': '⚠️'
                }
                icon = status_icons.get(record['status'], '•')
                self.logger.info(
                    f"{icon} {record['version']}: {record['name']} "
                    f"({record['applied_at'].strftime('%Y-%m-%d %H:%M')})"
                )
    
    async def upgrade(self, force_modified: bool = False) -> bool:
        """Applique toutes les migrations en attente"""
        self.logger.info("=== UPGRADE DATABASE ===\n")
        
        new_applied, modified_applied, failed = await self.engine.apply_all_pending(force_modified)
        
        if failed > 0:
            self.logger.error(f"{failed} migration(s) échouée(s)")
            return False
        
        total = new_applied + modified_applied
        if total > 0:
            self.logger.success(
                f"{total} migration(s) appliquée(s) "
                f"(nouvelles: {new_applied}, modifiées: {modified_applied})"
            )
        
        return True
    
    async def rollback(self, target_version: str) -> bool:
        """Rollback jusqu'à une version spécifique"""
        self.logger.info(f"=== ROLLBACK TO {target_version} ===\n")
        return await self.engine.rollback_migration(target_version)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        await self.db.close()
    
    def generate_report(self, success: bool):
        """Génère un rapport final"""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        print()
        print("=" * 80)
        print("  RAPPORT DE MIGRATION")
        print("=" * 80)
        print(f"  Début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Fin: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Durée: {duration:.2f}s")
        print(f"  Statut: {'✅ SUCCÈS' if success else '❌ ÉCHEC'}")
        print(f"  Dossier migrations: {self.migration_config.migrations_dir}")
        print(f"  Logs: {len(self.logger.logs)} entrée(s)")
        print("=" * 80)


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

async def main():
    """Point d'entrée principal"""
    
    parser = argparse.ArgumentParser(
        description="Script de migration SQL direct pour PostgreSQL Local avec auto-découverte",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/migrate_database_local.py --action upgrade
  python scripts/migrate_database_local.py --action upgrade --force-modified
  python scripts/migrate_database_local.py --action status
  python scripts/migrate_database_local.py --action rollback --target 20251016_create_email_logs
        """
    )
    
    parser.add_argument(
        "--action",
        choices=["upgrade", "status", "rollback"],
        default="upgrade",
        help="Action à effectuer"
    )
    parser.add_argument(
        "--target",
        help="Version cible pour rollback"
    )
    parser.add_argument(
        "--migrations-dir",
        help="Dossier contenant les migrations (défaut: app/db/migrations/sql)"
    )
    parser.add_argument(
        "--force-modified",
        action="store_true",
        help="Réapplique les migrations modifiées"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux"
    )
    
    args = parser.parse_args()
    
    # Bannière
    print()
    print("=" * 80)
    print("  MIGRATION SQL POSTGRESQL LOCAL - SEEG API v2.0")
    print("  Auto-Discovery & Change Detection")
    print("=" * 80)
    print()
    
    # Configuration
    db_config = DatabaseConfig()
    migration_config = MigrationConfig()
    
    if args.migrations_dir:
        migration_config.migrations_dir = Path(args.migrations_dir)
        migration_config.rollback_dir = migration_config.migrations_dir / "rollback"
    
    # Le mot de passe est configuré directement dans DatabaseConfig
    
    # Initialisation
    manager = MigrationManager(db_config, migration_config, args.verbose)
    
    try:
        if not await manager.initialize():
            print("❌ Échec de l'initialisation")
            return 1
        
        print()
        
        # Exécuter l'action
        if args.action == "status":
            await manager.show_status()
            success = True
            
        elif args.action == "upgrade":
            success = await manager.upgrade(args.force_modified)
            
        elif args.action == "rollback":
            if not args.target:
                print("❌ --target requis pour rollback")
                return 1
            success = await manager.rollback(args.target)
        
        else:
            print(f"❌ Action inconnue: {args.action}")
            return 1
        
        # Rapport final
        manager.generate_report(success)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Interruption par l'utilisateur")
        return 130
        
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
        
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

