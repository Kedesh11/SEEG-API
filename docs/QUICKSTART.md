# 🚀 Quick Start - SEEG-API

**Guide de démarrage rapide** pour mettre en production SEEG-API.

---

## ⚡ Démarrage Rapide (5 minutes)

### 1. Installation des Dépendances

```bash
# Windows
.\env\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration de Base

```bash
# Copier l'exemple
cp env.example .env

# Éditer .env avec vos valeurs
nano .env  # ou votre éditeur préféré
```

**Variables essentielles**:
```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db
SECRET_KEY=votre-cle-secrete-32-caracteres-minimum
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=votre-email
SMTP_PASSWORD=votre-mot-de-passe-app
```

### 3. Lancer l'Application

```bash
uvicorn app.main:app --reload
```

✅ API disponible sur: **http://localhost:8000**  
✅ Documentation: **http://localhost:8000/docs**

---

## 🔧 Configuration Avancée

### Application Insights (Recommandé pour Production)

#### Option A: Script Automatique (Windows)

```powershell
# Exécuter le script de configuration
.\scripts\setup-app-insights.ps1
```

#### Option B: Script Automatique (Linux/Mac)

```bash
# Rendre exécutable
chmod +x scripts/setup-app-insights.sh

# Exécuter
./scripts/setup-app-insights.sh
```

#### Option C: Configuration Manuelle

```bash
# 1. Se connecter à Azure
az login

# 2. Créer Application Insights
az monitor app-insights component create \
  --app seeg-api-insights \
  --location francecentral \
  --resource-group seeg-rg \
  --workspace seeg-logs-workspace

# 3. Récupérer la connection string
az monitor app-insights component show \
  --app seeg-api-insights \
  --resource-group seeg-rg \
  --query connectionString -o tsv

# 4. Ajouter à .env
echo "APPLICATIONINSIGHTS_CONNECTION_STRING=<votre-connection-string>" >> .env
```

---

## 🐳 Déploiement Docker

### Développement Local

```bash
# Démarrer tous les services
docker-compose -f docker-compose.dev.yml up -d

# Services disponibles:
# - API: http://localhost:8000
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
# - pgAdmin: http://localhost:5050
```

### Production

```bash
# Build l'image
docker build -t seeg-api:latest .

# Run le conteneur
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=... \
  -e APPLICATIONINSIGHTS_CONNECTION_STRING=... \
  seeg-api:latest
```

---

## 🚀 Déploiement Azure

### Via GitHub Actions (Automatique)

1. **Configurer les secrets GitHub**:
   - `Settings > Secrets > Actions`
   - Ajouter:
     - `AZURE_WEBAPP_PUBLISH_PROFILE_PROD`
     - `DATABASE_URL_PROD`

2. **Créer un tag pour déployer**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

3. **Le workflow se déclenche automatiquement** 🎉

### Via Azure CLI (Manuel)

```bash
# 1. Créer l'App Service
az webapp create \
  --name seeg-api-prod \
  --resource-group seeg-rg \
  --plan seeg-app-plan \
  --runtime "PYTHON:3.12"

# 2. Configurer les variables
az webapp config appsettings set \
  --name seeg-api-prod \
  --resource-group seeg-rg \
  --settings \
    DATABASE_URL="postgresql://..." \
    SECRET_KEY="..." \
    APPLICATIONINSIGHTS_CONNECTION_STRING="..."

# 3. Déployer
az webapp up \
  --name seeg-api-prod \
  --resource-group seeg-rg
```

---

## ✅ Vérification Post-Déploiement

### 1. Health Check

```bash
# Local
curl http://localhost:8000/health

# Production
curl https://seeg-api-prod.azurewebsites.net/health
```

**Réponse attendue**:
```json
{
  "status": "ok",
  "message": "API is healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

### 2. API Info

```bash
curl http://localhost:8000/info | jq
```

**Vérifier**:
- ✅ `monitoring.application_insights: "enabled"`
- ✅ `security.rate_limiting: "enabled"`

### 3. Tests

```bash
# Tous les tests
pytest -v

# Avec coverage
pytest --cov=app --cov-report=html
```

**Résultat attendu**: `29 passed` (100%) ✅

---

## 📊 Monitoring

### Application Insights

1. **Portail Azure** > **Application Insights** > `seeg-api-insights`
2. **Live Metrics** - Voir les requêtes en temps réel
3. **Failures** - Surveiller les erreurs
4. **Performance** - Analyser les temps de réponse

### Logs

```bash
# Logs local
tail -f logs/app.log

# Logs Azure
az webapp log tail \
  --name seeg-api-prod \
  --resource-group seeg-rg
```

---

## 🔐 Sécurité

### 1. Variables d'Environnement

**Ne JAMAIS commiter** :
- ❌ `.env`
- ❌ Mots de passe
- ❌ Clés API
- ❌ Connection strings

**À commiter** :
- ✅ `env.example` (template)
- ✅ Documentation

### 2. Rate Limiting

Configuré automatiquement :
- Login: 5 req/min
- Signup: 3 req/min
- Upload: 10 req/min

### 3. HTTPS

En production, utiliser **HTTPS uniquement** :
- Azure App Service: HTTPS activé par défaut
- Custom domain: Configurer un certificat SSL

---

## 📚 Documentation Complète

- **API**: http://localhost:8000/docs (Swagger)
- **CI/CD**: [docs/CI_CD.md](CI_CD.md)
- **App Insights**: [docs/APPLICATION_INSIGHTS.md](APPLICATION_INSIGHTS.md)
- **Rate Limiting**: [docs/RATE_LIMITING.md](RATE_LIMITING.md)
- **Session Complète**: [docs/SESSION_COMPLETE.md](SESSION_COMPLETE.md)

---

## 🆘 Troubleshooting

### Problème: Base de données inaccessible

```bash
# Vérifier la connexion
psql $DATABASE_URL -c "SELECT 1"

# Vérifier les migrations
alembic current
alembic upgrade head
```

### Problème: Tests échouent

```bash
# Vérifier l'environnement
python --version  # Doit être 3.11+

# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Problème: Application Insights ne fonctionne pas

```bash
# Vérifier la configuration
python -c "from app.core.monitoring import app_insights; print(app_insights.enabled)"

# Vérifier la connection string
echo $APPLICATIONINSIGHTS_CONNECTION_STRING
```

### Problème: Rate limiting bloque tout

```bash
# En développement, désactiver temporairement
# Commenter dans app/main.py:
# app.state.limiter = limiter
```

---

## 💡 Commandes Utiles

```bash
# Démarrer en dev
uvicorn app.main:app --reload

# Démarrer en prod
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Tests avec coverage
pytest --cov=app --cov-report=html -v

# Linting
black app/ tests/
isort app/ tests/
flake8 app/ tests/

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Docker
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f api
```

---

## 🎉 Félicitations !

Votre API SEEG est maintenant **production-ready** ! 🚀

- ✅ Tests: 100%
- ✅ Sécurité: Rate limiting
- ✅ Monitoring: Application Insights
- ✅ CI/CD: GitHub Actions
- ✅ Documentation: Complète

---

**Besoin d'aide ?** Consultez les docs ou créez une issue sur GitHub.

