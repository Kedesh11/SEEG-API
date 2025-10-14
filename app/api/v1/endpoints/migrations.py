"""
Endpoint de migration pour SEEG API
Permet d'exécuter les migrations de base de données via l'API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog
from typing import List, Dict, Any
from datetime import datetime

from app.db.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.core.exceptions import BusinessLogicError

logger = structlog.get_logger(__name__)
router = APIRouter()

def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur"""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")

# ============================================================================
# DÉFINITIONS DES MIGRATIONS
# ============================================================================

MIGRATIONS = [
    {
        "revision": "20251010_mtp_questions",
        "down_revision": "20251010_add_updated_at",
        "description": "Ajout colonne questions_mtp aux offres et nettoyage anciennes colonnes MTP",
        "sql_commands": [
            """
            ALTER TABLE job_offers 
            ADD COLUMN IF NOT EXISTS questions_mtp JSONB DEFAULT NULL;
            """,
            """
            COMMENT ON COLUMN job_offers.questions_mtp IS 
            'Questions MTP au format JSON: {questions_metier: [...], questions_talent: [...], questions_paradigme: [...]}';
            """,
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_metier_q3;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_talent_q3;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q1;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q2;",
            "ALTER TABLE applications DROP COLUMN IF EXISTS mtp_paradigme_q3;",
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS mtp_answers JSONB DEFAULT NULL;
            """,
            """
            COMMENT ON COLUMN applications.mtp_answers IS 
            'Réponses MTP au format JSONB: {reponses_metier: [...], reponses_talent: [...], reponses_paradigme: [...]}';
            """,
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = 'requirements' AND data_type = 'json'
                ) THEN
                    ALTER TABLE job_offers ALTER COLUMN requirements TYPE JSONB USING requirements::jsonb;
                END IF;
                
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = 'benefits' AND data_type = 'json'
                ) THEN
                    ALTER TABLE job_offers ALTER COLUMN benefits TYPE JSONB USING benefits::jsonb;
                END IF;
                
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = 'responsibilities' AND data_type = 'json'
                ) THEN
                    ALTER TABLE job_offers ALTER COLUMN responsibilities TYPE JSONB USING responsibilities::jsonb;
                END IF;
            END $$;
            """,
        ]
    },
    {
        "revision": "20251013_offer_status",
        "down_revision": "20251010_mtp_questions",
        "description": "Migration is_internal_only vers offer_status",
        "sql_commands": [
            """
            ALTER TABLE job_offers 
            ADD COLUMN IF NOT EXISTS offer_status VARCHAR NOT NULL DEFAULT 'tous';
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_job_offers_offer_status 
            ON job_offers (offer_status, status);
            """,
            """
            DO $$
            BEGIN
                -- Vérifier si is_internal_only existe avant de migrer les données
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = 'is_internal_only'
                ) THEN
                    UPDATE job_offers 
                    SET offer_status = CASE 
                        WHEN is_internal_only = true THEN 'interne'
                        ELSE 'tous'
                    END
                    WHERE is_internal_only IS NOT NULL;
                END IF;
            END $$;
            """,
            "DROP INDEX IF EXISTS ix_job_offers_is_internal_only;",
            "ALTER TABLE job_offers DROP COLUMN IF EXISTS is_internal_only;",
            """
            COMMENT ON COLUMN job_offers.offer_status IS 
            'Visibilité de l''offre: tous (internes+externes), interne (SEEG uniquement), externe (candidats externes uniquement)';
            """,
        ]
    },
    {
        "revision": "20251013_app_fields",
        "down_revision": "20251013_offer_status",
        "description": "Ajout colonnes manquantes à la table applications",
        "sql_commands": [
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS has_been_manager BOOLEAN NOT NULL DEFAULT FALSE;
            """,
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS ref_entreprise VARCHAR(255);
            """,
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS ref_fullname VARCHAR(255);
            """,
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS ref_mail VARCHAR(255);
            """,
            """
            ALTER TABLE applications 
            ADD COLUMN IF NOT EXISTS ref_contact VARCHAR(50);
            """,
            """
            COMMENT ON COLUMN applications.has_been_manager IS 
            'Indique si le candidat interne a déjà occupé un poste de chef/manager';
            """,
            """
            COMMENT ON COLUMN applications.ref_entreprise IS 
            'Nom entreprise/organisation recommandante (obligatoire candidats externes)';
            """,
            """
            COMMENT ON COLUMN applications.ref_fullname IS 
            'Nom complet du référent (obligatoire candidats externes)';
            """,
            """
            COMMENT ON COLUMN applications.ref_mail IS 
            'Email du référent (obligatoire candidats externes)';
            """,
            """
            COMMENT ON COLUMN applications.ref_contact IS 
            'Téléphone du référent (obligatoire candidats externes)';
            """,
        ]
    }
]

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/status",
    summary="Statut des migrations",
    description="Vérifier l'état actuel des migrations"
)
async def get_migration_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer le statut des migrations.
    Accessible uniquement aux administrateurs.
    """
    try:
        # Vérifier que l'utilisateur est admin
        user_role = getattr(current_user, 'role', None)
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les administrateurs peuvent accéder au statut des migrations"
            )
        
        safe_log("info", "🔍 Vérification statut migrations", user_id=str(current_user.id))
        
        # Vérifier si la table alembic_version existe
        check_table_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            );
        """)
        
        result = await db.execute(check_table_query)
        table_exists = result.scalar()
        
        if not table_exists:
            safe_log("warning", "⚠️  Table alembic_version n'existe pas")
            return {
                "status": "not_initialized",
                "current_version": None,
                "message": "Aucune migration appliquée",
                "migrations_available": len(MIGRATIONS)
            }
        
        # Récupérer la version actuelle
        version_query = text("SELECT version_num FROM alembic_version;")
        result = await db.execute(version_query)
        current_version = result.scalar_one_or_none()
        
        safe_log("info", "✅ Version actuelle récupérée", version=current_version)
        
        # Déterminer les migrations en attente
        pending_migrations = []
        if current_version is None:
            pending_migrations = MIGRATIONS
        else:
            found_current = False
            for migration in MIGRATIONS:
                if found_current:
                    pending_migrations.append(migration)
                elif migration["revision"] == current_version:
                    found_current = True
        
        return {
            "status": "ready" if len(pending_migrations) > 0 else "up_to_date",
            "current_version": current_version,
            "total_migrations": len(MIGRATIONS),
            "pending_migrations": len(pending_migrations),
            "pending_details": [
                {
                    "revision": m["revision"],
                    "description": m["description"]
                } for m in pending_migrations
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "❌ Erreur vérification statut migrations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification du statut: {str(e)}"
        )

@router.post(
    "/apply",
    summary="Appliquer les migrations",
    description="Exécuter toutes les migrations en attente"
)
async def apply_migrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Appliquer toutes les migrations en attente.
    Accessible uniquement aux administrateurs.
    
    ATTENTION : Cette opération modifie la structure de la base de données.
    """
    try:
        # Vérifier que l'utilisateur est admin
        user_role = getattr(current_user, 'role', None)
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les administrateurs peuvent appliquer les migrations"
            )
        
        safe_log("info", "🚀 DÉBUT application migrations", 
                user_id=str(current_user.id),
                user_email=current_user.email)
        
        # Créer la table alembic_version si elle n'existe pas
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
        """)
        await db.execute(create_table_query)
        await db.commit()
        
        # Récupérer la version actuelle
        version_query = text("SELECT version_num FROM alembic_version;")
        result = await db.execute(version_query)
        current_version = result.scalar_one_or_none()
        
        safe_log("info", "📌 Version actuelle", version=current_version or "Aucune")
        
        # Déterminer les migrations à appliquer
        migrations_to_apply = []
        
        if current_version is None:
            migrations_to_apply = MIGRATIONS
            safe_log("info", "📦 Aucune migration appliquée, toutes seront appliquées")
        else:
            found_current = False
            for migration in MIGRATIONS:
                if found_current:
                    migrations_to_apply.append(migration)
                elif migration["revision"] == current_version:
                    found_current = True
            
            if not found_current:
                safe_log("warning", f"⚠️  Version '{current_version}' non trouvée, toutes seront tentées")
                migrations_to_apply = MIGRATIONS
        
        if not migrations_to_apply:
            safe_log("info", "✅ Base de données à jour")
            return {
                "status": "success",
                "message": "Base de données déjà à jour",
                "current_version": current_version,
                "applied_migrations": 0
            }
        
        safe_log("info", f"📋 {len(migrations_to_apply)} migration(s) à appliquer")
        
        # Appliquer les migrations
        results = []
        success_count = 0
        
        for idx, migration in enumerate(migrations_to_apply, 1):
            safe_log("info", "=" * 80)
            safe_log("info", f"📦 MIGRATION {idx}/{len(migrations_to_apply)}: {migration['revision']}")
            safe_log("info", f"📝 {migration['description']}")
            
            try:
                # Exécuter chaque commande SQL
                executed_commands = 0
                skipped_commands = 0
                
                for sql_idx, sql in enumerate(migration["sql_commands"], 1):
                    sql_clean = sql.strip()
                    if not sql_clean or sql_clean.startswith('--'):
                        continue
                    
                    try:
                        await db.execute(text(sql_clean))
                        executed_commands += 1
                        safe_log("debug", f"   ✅ Commande {sql_idx} exécutée")
                    except Exception as cmd_error:
                        error_msg = str(cmd_error).lower()
                        
                        # Erreurs acceptables (idempotence)
                        if any(skip in error_msg for skip in ['does not exist', 'already exists', 'duplicate']):
                            safe_log("debug", f"   ⚠️  Commande {sql_idx} ignorée (idempotent)")
                            skipped_commands += 1
                        else:
                            raise
                
                # Mettre à jour la version
                await db.execute(text("DELETE FROM alembic_version;"))
                await db.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:version);"),
                    {"version": migration["revision"]}
                )
                
                # Commit la migration
                await db.commit()
                
                safe_log("info", f"✅ Migration {migration['revision']} appliquée avec succès")
                safe_log("info", f"   Commandes exécutées: {executed_commands}, ignorées: {skipped_commands}")
                
                results.append({
                    "revision": migration["revision"],
                    "status": "success",
                    "executed": executed_commands,
                    "skipped": skipped_commands,
                    "message": migration["description"]
                })
                
                success_count += 1
                
            except Exception as e:
                # Rollback en cas d'erreur
                await db.rollback()
                
                error_msg = str(e)
                safe_log("error", f"❌ Échec migration {migration['revision']}", 
                        error=error_msg,
                        error_type=type(e).__name__)
                
                results.append({
                    "revision": migration["revision"],
                    "status": "failed",
                    "error": error_msg,
                    "message": migration["description"]
                })
                
                # Arrêter en cas d'échec
                break
        
        # Vérifier la version finale
        final_version_query = text("SELECT version_num FROM alembic_version;")
        result = await db.execute(final_version_query)
        final_version = result.scalar_one_or_none()
        
        safe_log("info", "=" * 80)
        if success_count == len(migrations_to_apply):
            safe_log("info", "🎉 TOUTES LES MIGRATIONS ONT RÉUSSI")
        else:
            safe_log("warning", f"⚠️  {success_count}/{len(migrations_to_apply)} migration(s) réussie(s)")
        
        safe_log("info", f"📌 Version finale: {final_version}")
        
        return {
            "status": "success" if success_count == len(migrations_to_apply) else "partial",
            "message": f"{success_count}/{len(migrations_to_apply)} migration(s) appliquée(s)",
            "current_version": final_version,
            "applied_migrations": success_count,
            "total_migrations": len(migrations_to_apply),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "🔥 ERREUR CRITIQUE - Application migrations", 
                error=str(e),
                error_type=type(e).__name__)
        
        # Rollback en cas d'erreur globale
        try:
            await db.rollback()
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'application des migrations: {str(e)}"
        )

@router.post(
    "/rollback",
    summary="Rollback de migration",
    description="Annuler la dernière migration (à implémenter)"
)
async def rollback_migration(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Rollback de la dernière migration.
    ATTENTION : Fonctionnalité avancée, à utiliser avec précaution.
    """
    user_role = getattr(current_user, 'role', None)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les administrateurs peuvent effectuer un rollback"
        )
    
    return {
        "status": "not_implemented",
        "message": "Fonctionnalité de rollback à implémenter selon les besoins"
    }

@router.get(
    "/history",
    summary="Historique des migrations",
    description="Voir l'historique complet des migrations"
)
async def get_migration_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer l'historique des migrations.
    """
    try:
        user_role = getattr(current_user, 'role', None)
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les administrateurs peuvent voir l'historique des migrations"
            )
        
        # Vérifier si la table existe
        check_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            );
        """)
        
        result = await db.execute(check_query)
        table_exists = result.scalar()
        
        if not table_exists:
            return {
                "status": "not_initialized",
                "history": [],
                "message": "Aucune migration n'a été appliquée"
            }
        
        # Version actuelle
        version_query = text("SELECT version_num FROM alembic_version;")
        result = await db.execute(version_query)
        current_version = result.scalar_one_or_none()
        
        # Liste de toutes les migrations définies
        all_migrations_info = []
        for migration in MIGRATIONS:
            is_applied = False
            if current_version:
                # Trouver l'index de la migration actuelle
                current_idx = next(
                    (i for i, m in enumerate(MIGRATIONS) if m["revision"] == current_version),
                    -1
                )
                migration_idx = next(
                    (i for i, m in enumerate(MIGRATIONS) if m["revision"] == migration["revision"]),
                    -1
                )
                is_applied = migration_idx <= current_idx
            
            all_migrations_info.append({
                "revision": migration["revision"],
                "description": migration["description"],
                "down_revision": migration["down_revision"],
                "status": "applied" if is_applied else "pending"
            })
        
        return {
            "status": "success",
            "current_version": current_version,
            "history": all_migrations_info,
            "total_migrations": len(MIGRATIONS)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "❌ Erreur récupération historique", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )

