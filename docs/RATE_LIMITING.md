# 🛡️ Rate Limiting - Guide de configuration

## Vue d'ensemble

L'API SEEG utilise **slowapi** pour implémenter un système de rate limiting robuste qui protège l'application contre les abus et les attaques par brute force.

## Installation

```bash
pip install slowapi==0.1.9
```

ou

```bash
pip install -r requirements.txt
```

## Configuration

### Fichier de configuration: `app/core/rate_limit.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_identifier,  # Fonction personnalisée (user_id ou IP)
    default_limits=["1000/hour", "100/minute"],
    storage_uri="memory://",  # À remplacer par Redis en production
    headers_enabled=True
)
```

### Limites configurées

| Endpoint Type | Limite/minute | Limite/heure | Raison |
|---------------|---------------|--------------|---------|
| **Authentification** (`/login`) | 5 | 20 | Protection brute force |
| **Inscription** (`/signup`) | 3 | 10 | Prévention spam |
| **Upload PDF** | 10 | 50 | Limitation ressources |
| **Autres endpoints** | 60 | 500 | Usage normal |

## Utilisation

### Dans un endpoint FastAPI

```python
from fastapi import APIRouter, Request
from app.core.rate_limit import limiter, AUTH_LIMITS

router = APIRouter()

@router.post("/login")
@limiter.limit(AUTH_LIMITS)
async def login(request: Request):
    # Votre logique de connexion
    pass
```

### Identification des clients

Le système identifie les clients de manière intelligente :

1. **Utilisateurs authentifiés**: Par `user_id` extrait du JWT
2. **Utilisateurs anonymes**: Par adresse IP

```python
def get_identifier(request: Request) -> str:
    try:
        # Extraire user_id du token JWT
        auth_header = request.headers.get("authorization")
        if auth_header:
            token = auth_header.split(" ")[1]
            payload = TokenManager.verify_token(token)
            return f"user:{payload['sub']}"
    except:
        pass
    # Fallback sur IP
    return f"ip:{get_remote_address(request)}"
```

## Headers de réponse

Lorsque `headers_enabled=True`, l'API retourne les headers suivants :

- `X-RateLimit-Limit`: Limite totale
- `X-RateLimit-Remaining`: Requêtes restantes
- `X-RateLimit-Reset`: Timestamp de réinitialisation

### Exemple

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1696281600
```

## Gestion des dépassements (429)

Lorsqu'un client dépasse la limite :

```json
{
  "error": "Rate limit exceeded",
  "message": "Trop de requêtes. Veuillez réessayer plus tard.",
  "retry_after": 60
}
```

### Personnalisation de la réponse

Dans `app/main.py` :

```python
from slowapi.errors import RateLimitExceeded

app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={
        "error": "Rate limit exceeded",
        "message": "Trop de requêtes. Veuillez réessayer plus tard.",
        "retry_after": getattr(exc, "retry_after", None)
    }
))
```

## Production : Utiliser Redis

⚠️ **IMPORTANT**: En production, remplacer `storage_uri="memory://"` par Redis.

### Installation de Redis

```bash
pip install redis
```

### Configuration

```python
from app.core.config.config import settings

limiter = Limiter(
    key_func=get_identifier,
    default_limits=["1000/hour", "100/minute"],
    storage_uri=settings.REDIS_URL,  # "redis://localhost:6379/0"
    headers_enabled=True
)
```

### Avantages de Redis

✅ Partage de l'état entre instances (scaling horizontal)  
✅ Persistance des limites en cas de redémarrage  
✅ Performances optimales  

## Tests

### Tester le rate limiting

```python
# tests/unit/test_rate_limit_config.py
def test_auth_limits_are_strict():
    assert "5/minute" in AUTH_LIMITS
    assert "20/hour" in AUTH_LIMITS
```

### Test d'intégration

```bash
# Lancer 10 requêtes consécutives
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}';
done
```

Résultat attendu :
- Requêtes 1-5 : `401 Unauthorized` (credentials invalides)
- Requêtes 6-10 : `429 Too Many Requests` (rate limited)

## Monitoring

### Métriques à suivre

1. **Nombre de 429 par endpoint**: Identifier les abus
2. **Top IPs bloquées**: Détecter les attaques
3. **Taux de 429 global**: Ajuster les limites si nécessaire

### Logs

```python
logger.info("Rate limit hit", user_id=user_id, endpoint=request.url.path)
```

## Bonnes pratiques

### ✅ À faire

- Utiliser Redis en production
- Adapter les limites selon le trafic réel
- Monitorer les métriques de rate limiting
- Communiquer les limites dans la documentation API
- Utiliser des limites différentes par rôle si nécessaire

### ❌ À éviter

- Limites trop basses (mauvaise UX)
- Limites trop hautes (pas de protection)
- Utiliser `memory://` avec plusieurs instances
- Ignorer les headers X-RateLimit-*

## FAQ

### Q: Que se passe-t-il si je redémarre le serveur?

**R**: Avec `memory://`, les compteurs sont réinitialisés. Avec Redis, ils persistent.

### Q: Comment whitelister une IP?

**R**: Modifier la fonction `get_identifier` :

```python
WHITELIST_IPS = ["192.168.1.100"]

def get_identifier(request: Request) -> str:
    ip = get_remote_address(request)
    if ip in WHITELIST_IPS:
        return f"whitelist:{ip}"  # Pas de limite
    # ... logique normale
```

### Q: Comment augmenter la limite pour les admins?

**R**: Utiliser un décorateur conditionnel :

```python
@router.get("/admin/stats")
@limiter.limit("1000/minute" if user.role == "admin" else "60/minute")
async def get_stats(request: Request, user: User = Depends(get_current_user)):
    pass
```

### Q: Les limites sont-elles globales ou par utilisateur?

**R**: Par identifiant (user_id ou IP), grâce à `key_func=get_identifier`.

## Support

Pour toute question ou problème :
- Documentation slowapi: https://slowapi.readthedocs.io/
- Issues GitHub du projet: https://github.com/laurents/slowapi

---

**Dernière mise à jour**: 2 Octobre 2025  
**Version**: 1.0.0

