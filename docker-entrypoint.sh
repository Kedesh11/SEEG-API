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
    # Extrait host et port depuis MONGODB_URL
    # Supporte: mongodb://user:pass@host:port/db ou mongodb://host:port
    local url="$1"
    
    if [[ -z "$url" ]]; then
        log_error "MONGODB_URL vide"
        return 1
    fi
    
    # Extraction simplifiée (non-srv)
    DB_HOST=$(echo "$url" | sed -E 's/mongodb:\/\/(.*@)?([^:\/]+).*/\2/')
    DB_PORT=$(echo "$url" | sed -E 's/mongodb:\/\/(.*@)?[^:]+:([0-9]+).*/\2/')
    
    if [[ -z "$DB_HOST" ]] || [[ -z "$DB_PORT" ]]; then
        log_warn "Impossible d'extraire host/port depuis MONGODB_URL. Format peut-être SRV."
        DB_HOST=$(echo "$url" | sed -E 's/mongodb\+srv:\/\/(.*@)?([^\/]+).*/\2/')
        DB_PORT="27017" # Default for SRV
    fi
    
    log_info "Base de données détectée: ${DB_HOST}:${DB_PORT}"
    return 0
}

wait_for_mongodb() {
    log_header "ATTENTE DE MONGODB"
    
    if [[ "$SKIP_WAIT_FOR_DB" == "true" ]]; then
        log_warn "Vérification MongoDB désactivée (SKIP_WAIT_FOR_DB=true)"
        return 0
    fi

    # Atlas (mongodb+srv) n'expose pas forcément un host:port joignable en TCP direct
    # (résolution SRV + équilibrage), donc un test nc -z est souvent trompeur.
    if [[ -n "$MONGODB_URL" ]] && [[ "$MONGODB_URL" == mongodb+srv://* ]]; then
        log_warn "MONGODB_URL en mongodb+srv détecté: skip du test TCP (nc)"
        return 0
    fi
    
    local host=""
    local port=""
    
    # Déterminer host/port selon l'environnement
    if [[ "$ENVIRONMENT" == "production" ]] && [[ -n "$MONGODB_URL" ]]; then
        if ! extract_db_host_port "$MONGODB_URL"; then
            log_error "Échec extraction host/port, utilisation valeurs par défaut"
            host="${MONGODB_HOST:-mongodb}"
            port="${MONGODB_PORT:-27017}"
        else
            host="$DB_HOST"
            port="$DB_PORT"
        fi
    else
        host="${MONGODB_HOST:-mongodb}"
        port="${MONGODB_PORT:-27017}"
        log_info "Mode développement: MongoDB sur ${host}:${port}"
    fi
    
    # Attente avec retry
    local retry=0
    log_info "Attente de MongoDB sur ${host}:${port}..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        retry=$((retry + 1))
        if [[ $retry -ge $MAX_DB_RETRIES ]]; then
            log_error "MongoDB injoignable après ${MAX_DB_RETRIES} tentatives"
            return 1
        fi
        log_info "MongoDB pas encore prêt (tentative ${retry}/${MAX_DB_RETRIES})..."
        sleep $DB_RETRY_DELAY
    done
    
    log_success "MongoDB est prêt sur ${host}:${port}"
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
    if ! wait_for_mongodb; then
        log_error "MongoDB injoignable, arrêt"
        exit 1
    fi
    
    wait_for_redis  # Non bloquant si Redis absent
    
    # Étape 3: Bootstrap utilisateurs (optionnel)
    bootstrap_initial_users
    
    # Étape 4: Démarrage de l'application
    log_header "DEMARRAGE DE L'APPLICATION"
    
    # Render injecte $PORT; fallback to 8000 sinon
    APP_PORT="${PORT:-8000}"
    log_info "Port: ${APP_PORT}"
    log_info "Commande: $*"
    log_success "Prêt à démarrer l'API"
    
    # Si le premier argument est 'uvicorn', injecter le port dynamique
    if [[ "$1" == "uvicorn" ]]; then
        # Remplacer le port fixe par le port dynamique
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "${APP_PORT}" \
            --workers "${WORKERS:-2}" \
            --access-log \
            --log-config logging.yaml \
            --proxy-headers \
            --forwarded-allow-ips "*"
    else
        exec "$@"
    fi
}

# ============================================================================
# EXECUTION
# ============================================================================

main "$@"
