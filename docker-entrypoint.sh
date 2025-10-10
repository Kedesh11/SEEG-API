#!/bin/bash
# ============================================================================
# SEEG-API Docker Entrypoint - Production Ready
# ============================================================================
# Principes appliqués:
# - Single Responsibility: Chaque fonction a un rôle unique
# - Robustesse: Gestion d'erreurs complète avec fallbacks
# - Observabilité: Logging détaillé pour debugging
# - Portabilité: Compatible local et Azure App Service
# ============================================================================

set -e  # Arrêt immédiat si erreur
set -o pipefail  # Propagation des erreurs dans les pipes

# ============================================================================
# CONFIGURATION & VARIABLES
# ============================================================================

ENVIRONMENT="${ENVIRONMENT:-production}"
SKIP_WAIT_FOR_DB="${SKIP_WAIT_FOR_DB:-false}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-false}"
CREATE_INITIAL_USERS="${CREATE_INITIAL_USERS:-false}"
MAX_DB_RETRIES=30
DB_RETRY_DELAY=2

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] ✅ $1"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] ❌ $1" >&2
}

log_warn() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [WARN] ⚠️  $1"
}

log_header() {
    echo ""
    echo "========================================="
    echo "$1"
    echo "========================================="
}

# ============================================================================
# FONCTIONS MÉTIER
# ============================================================================

extract_db_host_port() {
    # Extrait host et port depuis DATABASE_URL
    # Supporte: postgresql://user:pass@host:port/db et postgresql+asyncpg://...
    local url="$1"
    
    if [[ -z "$url" ]]; then
        log_error "DATABASE_URL vide"
        return 1
    fi
    
    # Extraction avec sed (compatible Linux)
    DB_HOST=$(echo "$url" | sed -E 's/^[^:]+:\/\/[^@]+@([^:\/]+).*/\1/')
    DB_PORT=$(echo "$url" | sed -E 's/^[^:]+:\/\/[^@]+@[^:]+:([0-9]+).*/\1/')
    
    if [[ -z "$DB_HOST" ]] || [[ -z "$DB_PORT" ]]; then
        log_error "Impossible d'extraire host/port depuis DATABASE_URL"
        return 1
    fi
    
    log_info "Base de données détectée: ${DB_HOST}:${DB_PORT}"
    return 0
}

wait_for_postgres() {
    log_header "ATTENTE DE POSTGRESQL"
    
    if [[ "$SKIP_WAIT_FOR_DB" == "true" ]]; then
        log_warn "Vérification PostgreSQL désactivée (SKIP_WAIT_FOR_DB=true)"
        return 0
    fi
    
    local host=""
    local port=""
    
    # Déterminer host/port selon l'environnement
    if [[ "$ENVIRONMENT" == "production" ]] && [[ -n "$DATABASE_URL" ]]; then
        if ! extract_db_host_port "$DATABASE_URL"; then
            log_error "Échec extraction host/port, utilisation valeurs par défaut"
            host="${POSTGRES_HOST:-postgres}"
            port="${POSTGRES_PORT:-5432}"
        else
            host="$DB_HOST"
            port="$DB_PORT"
        fi
    else
        host="${POSTGRES_HOST:-postgres}"
        port="${POSTGRES_PORT:-5432}"
        log_info "Mode développement: PostgreSQL sur ${host}:${port}"
    fi
    
    # Attente avec retry
    local retry=0
    log_info "Attente de PostgreSQL sur ${host}:${port}..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        retry=$((retry + 1))
        if [[ $retry -ge $MAX_DB_RETRIES ]]; then
            log_error "PostgreSQL injoignable après ${MAX_DB_RETRIES} tentatives"
            return 1
        fi
        log_info "PostgreSQL pas encore prêt (tentative ${retry}/${MAX_DB_RETRIES})..."
        sleep $DB_RETRY_DELAY
    done
    
    log_success "PostgreSQL est prêt sur ${host}:${port}"
    return 0
}

wait_for_redis() {
    if [[ -z "$REDIS_URL" ]]; then
        log_info "Redis non configuré, skip"
        return 0
    fi
    
    local redis_host="${REDIS_HOST:-redis}"
    local redis_port="${REDIS_PORT:-6379}"
    
    log_info "Attente de Redis sur ${redis_host}:${redis_port}..."
    
    local retry=0
    while ! nc -z "$redis_host" "$redis_port" 2>/dev/null; do
        retry=$((retry + 1))
        if [[ $retry -ge 10 ]]; then
            log_warn "Redis injoignable, démarrage sans cache"
            return 0
        fi
        sleep 2
    done
    
    log_success "Redis est prêt"
    return 0
}

run_migrations() {
    log_header "APPLICATION DES MIGRATIONS ALEMBIC"
    
    if ! command -v alembic &> /dev/null; then
        log_error "Alembic non trouvé dans le PATH"
        return 1
    fi
    
    log_info "Vérification de l'état actuel des migrations..."
    alembic current || log_warn "Impossible de déterminer la révision actuelle."
    
    log_info "Exécution: alembic upgrade head"
    
    if alembic upgrade head 2>&1; then
        log_success "Migrations appliquées avec succès"
        return 0
    else
        log_error "Échec des migrations"
        
        # Test de connexion DB pour diagnostic
        log_info "Test de connexion à la base de données..."
        if python -c "
import asyncio
from app.db.database import async_engine

async def test_connection():
    try:
        async with async_engine.connect() as conn:
            print('[INFO] ✅ Connexion DB réussie')
            return 0
    except Exception as e:
        print(f'[ERROR] ❌ Connexion DB échouée: {e}')
        return 1

exit(asyncio.run(test_connection()))
" 2>&1; then
            log_info "Connexion DB OK mais migrations échouées"
        else
            log_error "Connexion DB impossible"
        fi
        
        return 1
    fi
}

bootstrap_initial_users() {
    if [[ "$CREATE_INITIAL_USERS" != "true" ]]; then
        log_info "Bootstrap utilisateurs désactivé (CREATE_INITIAL_USERS != true)"
        return 0
    fi
    
    log_header "CREATION DES UTILISATEURS INITIAUX"
    
    if [[ ! -f "scripts/create_recruiters_after_migration.py" ]]; then
        log_warn "Script create_recruiters_after_migration.py introuvable, skip"
        return 0
    fi
    
    log_info "Exécution du script de création des recruteurs/observateur..."
    
    set +e  # Continuer même si le script échoue
    python scripts/create_recruiters_after_migration.py
    local exit_code=$?
    set -e
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Bootstrap utilisateurs terminé"
    else
        log_warn "Bootstrap utilisateurs échoué (code: ${exit_code}), poursuite du démarrage"
    fi
    
    return 0
}

# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

main() {
    log_header "SEEG-API DOCKER ENTRYPOINT"
    log_info "Environnement: ${ENVIRONMENT}"
    log_info "Python: $(python --version)"
    log_info "User: $(whoami)"
    
    # Étape 1: Attente des dépendances
    if ! wait_for_postgres; then
        log_error "PostgreSQL injoignable, arrêt"
        exit 1
    fi
    
    wait_for_redis  # Non bloquant si Redis absent
    
    # Étape 2: Migrations de base de données
    if [[ "$SKIP_MIGRATIONS" == "true" ]]; then
        log_warn "Migrations ignorées (SKIP_MIGRATIONS=true)"
        log_info "Les migrations doivent être exécutées séparément avec run-migrations.ps1"
    else
        if ! run_migrations; then
            log_error "Migrations échouées, arrêt"
            exit 1
        fi
    fi
    
    # Étape 3: Bootstrap utilisateurs (optionnel)
    bootstrap_initial_users
    
    # Étape 4: Démarrage de l'application
    log_header "DEMARRAGE DE L'APPLICATION"
    log_info "Commande: $*"
    log_success "Prêt à démarrer l'API"
    
    # Exécuter la commande CMD du Dockerfile
    exec "$@"
}

# ============================================================================
# EXECUTION
# ============================================================================

main "$@"
