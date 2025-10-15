# 📊 Guide Complet du Système de Logging SEEG-API

## 🎯 Vue d'ensemble

Le système de logging de SEEG-API est conçu selon les **meilleures pratiques de génie logiciel** pour offrir une **observabilité complète**, une **traçabilité totale** et un **debugging facilité**.

### ✨ Caractéristiques Principales

- **Logging Structuré** : Format JSON pour faciliter l'analyse et l'indexation
- **Correlation IDs** : Suivi des requêtes à travers tous les composants
- **Contextuel** : Enrichissement automatique avec user_id, request_id, etc.
- **Performance Monitoring** : Mesure automatique des temps d'exécution
- **Niveaux Multiples** : DEBUG, INFO, WARNING, ERROR avec emojis visuels
- **Business Events** : Traçabilité des événements métier importants
- **Security Audit** : Logging des événements de sécurité
- **Fail-Safe** : Les erreurs de logging ne bloquent jamais l'application

---

## 🏗️ Architecture

```
app/core/logging/
├── enhanced_logging.py      # Configuration de base avec structlog
├── decorators.py            # Décorateurs pour automatiser le logging
└── business_logger.py       # Logger spécialisé pour événements métier

app/middleware/
└── logging_middleware.py    # Middleware pour tracer toutes les requêtes HTTP
```

### Principes Appliqués

1. **DRY (Don't Repeat Yourself)** : Décorateurs pour éviter la répétition
2. **Single Responsibility** : Chaque module a un rôle précis
3. **Open/Closed** : Facilement extensible sans modification
4. **Dependency Injection** : Les loggers sont injectés, pas créés
5. **Fail-Safe** : Résilience aux erreurs de logging

---

## 🚀 Utilisation

### 1. Logging de Base

```python
import structlog

logger = structlog.get_logger(__name__)

# Logging simple
logger.info("Message informatif")
logger.warning("Attention", user_id="123")
logger.error("Erreur détectée", error=str(e), exc_info=True)

# Avec contexte structuré
logger.info(
    "Création utilisateur",
    user_id="123",
    email="user@example.com",
    role="candidate",
    ip_address="192.168.1.1"
)
```

### 2. Décorateurs pour Fonctions

#### `@log_execution` - Tracer automatiquement l'exécution

```python
from app.core.logging.decorators import log_execution

@log_execution(
    log_args=True,           # Logger les arguments
    log_result=False,        # Logger le résultat
    log_performance=True,    # Mesurer le temps d'exécution
    level="info",            # Niveau de log
    exclude_args=['password', 'token']  # Exclure les données sensibles
)
async def create_user(email: str, password: str, first_name: str):
    # Votre code ici
    pass
```

**Logs générés automatiquement :**
```
🚀 Début exécution: create_user (execution_id=abc123, args_count=3)
✅ Fin exécution: create_user (duration_ms=45.23, status=success)
```

#### `@log_database_operation` - Tracer les opérations DB

```python
from app.core.logging.decorators import log_database_operation

@log_database_operation("INSERT")
async def create_user_in_db(user_data: dict):
    # Insertion en base
    pass
```

**Logs générés :**
```
🗄️ Opération DB: INSERT (operation_id=xyz789)
✅ DB INSERT réussie (duration_ms=23.45)
⚠️ Opération DB lente: INSERT (duration_ms=523.10)  # Si > 500ms
```

#### `@log_business_event` - Tracer les événements métier

```python
from app.core.logging.decorators import log_business_event

@log_business_event("created", "user")
async def create_user(user_data: dict):
    # Création utilisateur
    return user
```

**Logs générés :**
```
📊 Événement métier: user.created (event_id=def456)
✅ Événement métier traité: user.created (entity_id=user-123)
```

#### `@log_retry` - Retry avec logging automatique

```python
from app.core.logging.decorators import log_retry

@log_retry(max_retries=3, delay=1.0, backoff=2.0)
async def unstable_external_api_call():
    # Appel API externe qui peut échouer
    pass
```

**Logs générés :**
```
🔄 Nouvelle tentative: unstable_external_api_call (attempt=2/3)
✅ Succès après retry: unstable_external_api_call (attempts=2)
```

### 3. Business Logger - Événements Métier

```python
from app.core.logging.business_logger import business_logger

# Inscription utilisateur
business_logger.log_user_registered(
    user_id="123",
    email="user@example.com",
    role="candidate"
)

# Soumission de candidature
business_logger.log_application_submitted(
    application_id="app-456",
    candidate_id="123",
    job_offer_id="job-789",
    job_title="Ingénieur DevOps"
)

# Changement de statut
business_logger.log_application_status_changed(
    application_id="app-456",
    candidate_id="123",
    old_status="pending",
    new_status="interview",
    changed_by="recruiter-001"
)

# Envoi d'email
business_logger.log_email_sent(
    recipient="user@example.com",
    subject="Bienvenue",
    email_type="welcome"
)

# Événement de sécurité
business_logger.log_access_denied(
    user_id="123",
    resource="/admin/dashboard",
    action="READ",
    reason="Insufficient permissions"
)
```

**Format des logs :**
```json
{
  "event_type": "application.submitted",
  "entity_id": "app-456",
  "user_id": "123",
  "timestamp": "2025-10-15T14:30:00Z",
  "category": "business_event",
  "details": {
    "job_offer_id": "job-789",
    "job_title": "Ingénieur DevOps"
  }
}
```

### 4. Middleware de Logging HTTP

Le middleware `EnhancedLoggingMiddleware` trace automatiquement **toutes les requêtes HTTP**.

#### Configuration dans `main.py`

```python
from app.middleware.logging_middleware import EnhancedLoggingMiddleware

app.add_middleware(
    EnhancedLoggingMiddleware,
    slow_request_threshold=1.0,    # Seuil requêtes lentes (secondes)
    log_request_body=False,         # Logger le body des requêtes
    log_response_body=False,        # Logger le body des réponses
    excluded_paths=[                # Chemins à exclure
        "/health",
        "/metrics",
        "/docs"
    ]
)
```

#### Logs Automatiques Générés

**Début de requête :**
```
🌐 ➡️  POST /api/v1/applications
{
  "request_id": "abc-123",
  "method": "POST",
  "path": "/api/v1/applications",
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "user_id": "user-456",
  "timestamp": "2025-10-15T14:30:00Z",
  "event_type": "request_started"
}
```

**Fin de requête réussie :**
```
✅ POST /api/v1/applications [201] - 45.23ms
{
  "request_id": "abc-123",
  "status_code": 201,
  "duration_seconds": 0.045,
  "duration_ms": 45.23,
  "event_type": "request_completed"
}
```

**Requête lente :**
```
⚠️ SLOW REQUEST: POST /api/v1/applications
{
  "request_id": "abc-123",
  "duration_seconds": 1.234,
  "threshold_seconds": 1.0,
  "exceeded_by_seconds": 0.234,
  "event_type": "slow_request"
}
```

**Événements de sécurité :**
```
🔐 Tentative d'accès non authentifiée: GET /api/v1/admin/users
{
  "request_id": "xyz-789",
  "path": "/api/v1/admin/users",
  "client_ip": "192.168.1.100",
  "event_type": "authentication_failed"
}

🚫 Accès refusé: DELETE /api/v1/users/123
{
  "request_id": "def-456",
  "user_id": "user-789",
  "client_ip": "192.168.1.100",
  "event_type": "authorization_failed"
}
```

### 5. Logging Contextuel avec Correlation IDs

```python
from app.core.logging.enhanced_logging import LogContext

# Utilisation avec context manager
with LogContext(request_id="abc-123", user_id="user-456"):
    logger.info("Traitement de la requête")
    # Tous les logs dans ce bloc auront automatiquement
    # request_id et user_id ajoutés
    
    await process_application(data)
    
    logger.info("Traitement terminé")
```

**Résultat :**
```json
{
  "message": "Traitement de la requête",
  "request_id": "abc-123",
  "user_id": "user-456",
  "timestamp": "2025-10-15T14:30:00Z"
}
```

---

## 🎨 Niveaux de Log et Emojis

| Niveau | Emoji | Usage |
|--------|-------|-------|
| **DEBUG** | 🔍 | Informations de débogage détaillées |
| **INFO** | ℹ️ | Événements normaux (succès, démarrage, etc.) |
| **WARNING** | ⚠️ | Situations inhabituelles mais gérées |
| **ERROR** | ❌ | Erreurs nécessitant attention |

### Emojis Spécialisés

| Emoji | Signification |
|-------|---------------|
| 🚀 | Début d'opération |
| ✅ | Succès |
| 🌐 | Requête HTTP |
| 🗄️ | Opération base de données |
| 📊 | Événement métier |
| 🔐 | Authentification |
| 🚫 | Accès refusé |
| 🔔 | Notification |
| 📧 | Email |
| 💾 | Sauvegarde |
| 📄 | Document |
| 🔄 | Retry/Mise à jour |

---

## 📈 Monitoring des Performances

### Logging Automatique des Performances

Le système mesure automatiquement :

1. **Durée des requêtes HTTP** (middleware)
2. **Durée des fonctions** (décorateur `@log_execution`)
3. **Durée des opérations DB** (décorateur `@log_database_operation`)

### Alertes Automatiques

- **Requête HTTP lente** : > 1 seconde (configurable)
- **Opération DB lente** : > 500ms (configurable)
- **Fonction lente** : > 1 seconde (configurable)

### Exemple d'Alerte

```json
{
  "level": "WARNING",
  "message": "⚠️ SLOW REQUEST: POST /api/v1/applications",
  "request_id": "abc-123",
  "duration_seconds": 1.234,
  "threshold_seconds": 1.0,
  "exceeded_by_seconds": 0.234,
  "path": "/api/v1/applications",
  "method": "POST"
}
```

---

## 🔒 Sécurité et Données Sensibles

### Exclusion Automatique

Les décorateurs excluent automatiquement les champs sensibles :

```python
# Ces champs ne seront JAMAIS loggés
SENSITIVE_FIELDS = [
    'password',
    'token',
    'secret',
    'api_key',
    'credit_card',
    'ssn'
]
```

### Sanitization Automatique

- **Chaînes longues** : Tronquées à 200 caractères
- **Listes** : Limitées à 5 éléments
- **Dictionnaires** : Limités à 10 clés
- **Objets complexes** : Remplacés par `<TypeName>`

---

## 🔍 Debugging avec les Logs

### 1. Suivre une Requête Spécifique

```bash
# Filtrer par request_id
grep "abc-123" logs/app.log | jq .

# Ou avec structlog
grep "request_id.*abc-123" logs/app.log
```

### 2. Analyser les Erreurs

```bash
# Toutes les erreurs
grep '"level":"ERROR"' logs/app.log | jq .

# Erreurs pour un utilisateur spécifique
grep '"user_id":"user-456"' logs/app.log | grep ERROR
```

### 3. Mesurer les Performances

```bash
# Requêtes lentes
grep "SLOW REQUEST" logs/app.log | jq .

# Top 10 des endpoints les plus lents
grep "request_completed" logs/app.log | \
  jq -r '"\(.duration_ms) \(.path)"' | \
  sort -rn | head -10
```

### 4. Audit de Sécurité

```bash
# Tentatives d'authentification échouées
grep "authentication_failed" logs/app.log | jq .

# Accès refusés
grep "authorization_failed" logs/app.log | jq .

# Par adresse IP
grep '"client_ip":"192.168.1.100"' logs/app.log | \
  grep -E "(authentication_failed|authorization_failed)"
```

---

## 📊 Exemples Complets

### Exemple 1 : Créer un Utilisateur

```python
from app.core.logging.decorators import log_execution, log_business_event
from app.core.logging.business_logger import business_logger
import structlog

logger = structlog.get_logger(__name__)

@log_execution(log_args=True, exclude_args=['password'])
@log_business_event("created", "user")
async def create_user(email: str, password: str, first_name: str, last_name: str):
    """
    Créer un nouvel utilisateur
    
    Logs générés automatiquement :
    - Début/fin d'exécution (décorateur @log_execution)
    - Événement métier (décorateur @log_business_event)
    - Événement métier détaillé (business_logger)
    """
    
    logger.info("Création utilisateur", email=email)
    
    try:
        # Créer l'utilisateur
        user = await user_repository.create(...)
        
        # Logger l'événement métier avec détails
        business_logger.log_user_registered(
            user_id=str(user.id),
            email=email,
            role="candidate"
        )
        
        logger.info("✅ Utilisateur créé", user_id=str(user.id))
        
        return user
        
    except Exception as e:
        logger.error("❌ Erreur création utilisateur", 
                    email=email, error=str(e), exc_info=True)
        raise
```

### Exemple 2 : Traiter une Candidature

```python
from app.core.logging.decorators import log_execution
from app.core.logging.business_logger import business_logger

@log_execution(log_performance=True)
async def process_application(application_id: str, recruiter_id: str):
    """Traiter une candidature avec logging complet"""
    
    logger.info("🔍 Traitement candidature", 
               application_id=application_id,
               recruiter_id=recruiter_id)
    
    # Charger la candidature
    application = await load_application(application_id)
    
    # Évaluer
    score = await evaluate_application(application)
    logger.info("📊 Évaluation complétée", 
               application_id=application_id, score=score)
    
    # Changer le statut
    old_status = application.status
    new_status = "interview" if score > 70 else "rejected"
    
    await update_status(application_id, new_status)
    
    # Logger l'événement métier
    business_logger.log_application_status_changed(
        application_id=application_id,
        candidate_id=str(application.candidate_id),
        old_status=old_status,
        new_status=new_status,
        changed_by=recruiter_id,
        score=score
    )
    
    logger.info("✅ Candidature traitée", 
               application_id=application_id,
               new_status=new_status)
```

---

## 🛠️ Configuration Avancée

### Variables d'Environnement

```env
# Niveau de log
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Format de sortie
LOG_FORMAT=json  # json, text

# Fichier de log
LOG_FILE=/var/log/seeg-api/app.log

# Rotation des logs
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10
```

### Configuration Programmatique

```python
from app.core.logging.enhanced_logging import setup_logging

setup_logging(
    log_level="INFO",
    json_logs=True,
    log_file="/var/log/seeg-api/app.log"
)
```

---

## ✅ Meilleures Pratiques

### ✔️ À FAIRE

1. **Utiliser les décorateurs** pour éviter la répétition
2. **Logger les événements métier importants** (inscriptions, candidatures, etc.)
3. **Inclure le contexte** (user_id, request_id, etc.)
4. **Utiliser les bons niveaux de log** (INFO pour succès, WARNING pour anormal, ERROR pour erreurs)
5. **Logger les performances** pour identifier les goulots d'étranglement
6. **Exclure les données sensibles** (passwords, tokens, etc.)

### ❌ À ÉVITER

1. **Ne pas logger dans les boucles serrées** (performance)
2. **Ne pas logger de données personnelles sensibles** (RGPD)
3. **Ne pas utiliser print()** (utiliser logger)
4. **Ne pas logger des objets entiers** (trop volumineux)
5. **Ne pas oublier exc_info=True** pour les exceptions

---

## 📚 Ressources

- [Structlog Documentation](https://www.structlog.org/)
- [12 Factor App - Logs](https://12factor.net/logs)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

---

**Créé avec ❤️ pour SEEG-API | Respecte les meilleures pratiques de Génie Logiciel**

