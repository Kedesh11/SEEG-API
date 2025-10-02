# 🚀 CI/CD - Guide Complet

**Date**: 2 Octobre 2025  
**Statut**: ✅ Configuré et Opérationnel

---

## 📋 Vue d'ensemble

Le pipeline CI/CD de SEEG-API est composé de 4 workflows GitHub Actions :

1. **CI** - Tests et qualité du code
2. **PR Checks** - Validation des pull requests
3. **Deploy Azure** - Déploiement automatique
4. **Release** - Gestion des versions

---

## 🔄 Workflow CI (Intégration Continue)

### Déclenchement
- Push sur `main` ou `develop`
- Pull request vers `main` ou `develop`

### Jobs

#### 1. Tests (`test`)
- **Matrix**: Python 3.11, 3.12, 3.13
- **Services**: PostgreSQL 15
- **Étapes**:
  - Installation des dépendances
  - Exécution des tests avec coverage
  - Upload du rapport de coverage vers Codecov
  
```bash
# Commande locale équivalente
pytest --cov=app --cov-report=xml --cov-report=html -v
```

#### 2. Linting (`lint`)
- **Outils**: Black, isort, flake8, mypy, pylint
- **Étapes**:
  - Vérification du formatage (Black)
  - Vérification des imports (isort)
  - Analyse statique (flake8)

```bash
# Commandes locales
black --check app/ tests/
isort --check-only app/ tests/
flake8 app/ --max-line-length=127
```

#### 3. Sécurité (`security`)
- **Outils**: Safety, Bandit
- **Étapes**:
  - Scan des vulnérabilités connues
  - Analyse de sécurité du code
  - Génération de rapports

```bash
# Commandes locales
safety check
bandit -r app/
```

---

## 🔍 Workflow PR Checks

### Déclenchement
- Ouverture d'une PR
- Push sur une branche de PR
- Réouverture d'une PR

### Validations

#### 1. Format du Titre
Format requis: `type(scope): description`

Types valides:
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Maintenance
- `perf`: Performance

**Exemples**:
```
✅ feat(auth): ajouter rate limiting
✅ fix(api): corriger validation PDF
✅ docs(readme): mettre à jour installation
❌ Update code
❌ Fixed bug
```

#### 2. Labels Automatiques
Les PRs sont automatiquement labellisées selon les fichiers modifiés:
- `documentation`: `docs/**, *.md`
- `tests`: `tests/**`
- `api`: `app/api/**`
- `models`: `app/models/**`
- etc.

#### 3. Taille de la PR
- ⚠️ Warning si > 50 fichiers
- ⚠️ Warning si > 1000 lignes

#### 4. Coverage Comment
Un commentaire est automatiquement ajouté avec:
- % de coverage total
- Fichiers non couverts
- Comparaison avec la branche de base

---

## 🚢 Workflow Deploy Azure

### Déclenchement
- Push sur `main` → Staging
- Tag `v*.*.*` → Production

### Environnements

#### Staging
- **URL**: https://seeg-api-staging.azurewebsites.net
- **Déploiement**: Automatique sur push `main`
- **Health check**: 30s après déploiement

#### Production
- **URL**: https://www.seeg-api.com
- **Déploiement**: Automatique sur tag
- **Approbation**: Requise
- **Health check**: 60s après déploiement
- **Rollback**: Automatique en cas d'échec

### Migration Base de Données
```yaml
# Exécution automatique avec Alembic
alembic upgrade head
```

---

## 📦 Workflow Release

### Déclenchement
- Push d'un tag `v*.*.*`

### Processus

1. **Génération du Changelog**
   - Extraction des commits depuis la dernière release
   - Formatage automatique

2. **Création de la Release GitHub**
   - Draft: Non
   - Prerelease: Si tag contient `alpha`, `beta`, `rc`
   - Notes générées automatiquement

3. **Build Docker Image**
   - Tags créés:
     - `v1.2.3`
     - `1.2`
     - `1`
     - `latest` (si branche par défaut)
   - Push vers Docker Hub

### Créer une Release

```bash
# 1. Tag la version
git tag -a v1.2.3 -m "Release v1.2.3"

# 2. Push le tag
git push origin v1.2.3

# 3. Le workflow se déclenche automatiquement
```

---

## 🐳 Docker

### Build Local

```bash
# Build
docker build -t seeg-api:local .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=... \
  seeg-api:local
```

### Docker Compose (Développement)

```bash
# Démarrer tous les services
docker-compose -f docker-compose.dev.yml up -d

# Logs
docker-compose -f docker-compose.dev.yml logs -f api

# Arrêter
docker-compose -f docker-compose.dev.yml down
```

**Services inclus**:
- API (port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- pgAdmin (port 5050)

---

## 🔐 Secrets GitHub

### Requis pour le CI/CD

| Secret | Description | Exemple |
|--------|-------------|---------|
| `AZURE_WEBAPP_PUBLISH_PROFILE_STAGING` | Profil de publication Azure (Staging) | XML de profil |
| `AZURE_WEBAPP_PUBLISH_PROFILE_PROD` | Profil de publication Azure (Production) | XML de profil |
| `DATABASE_URL_PROD` | URL de connexion BD production | `postgresql://...` |
| `DOCKER_USERNAME` | Nom d'utilisateur Docker Hub | `cnx40` |
| `DOCKER_PASSWORD` | Token d'accès Docker Hub | Token |
| `CODECOV_TOKEN` | Token Codecov (optionnel) | UUID |

### Configuration

```bash
# Via GitHub CLI
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE_STAGING < profile.xml

# Via l'interface web
# Settings > Secrets and variables > Actions > New repository secret
```

---

## 📊 Badges

Ajoutez ces badges à votre README:

```markdown
![CI](https://github.com/cnx40/seeg-api/workflows/CI/badge.svg)
![Deploy](https://github.com/cnx40/seeg-api/workflows/CD%20-%20Déploiement%20Azure/badge.svg)
![Coverage](https://codecov.io/gh/cnx40/seeg-api/branch/main/graph/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
```

---

## 🔧 Configuration Locale

### Pre-commit Hooks

Installez les hooks pour valider avant commit:

```bash
pip install pre-commit
pre-commit install
```

Créez `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

---

## 📈 Monitoring

### Health Checks

Tous les déploiements incluent un health check:

```bash
# Staging
curl https://seeg-api-staging.azurewebsites.net/health

# Production
curl https://www.seeg-api.com/health
```

**Réponse attendue**:
```json
{
  "status": "healthy",
  "version": "1.2.3",
  "database": "connected"
}
```

### Logs Azure

```bash
# Via Azure CLI
az webapp log tail --name seeg-api-prod --resource-group seeg-rg

# Via portal
# App Service > Monitoring > Log stream
```

---

## 🚨 Troubleshooting

### Tests échouent localement mais passent en CI

**Cause**: Différences d'environnement

**Solution**:
```bash
# Utiliser la même version Python
python --version  # Doit être 3.12

# Même base de données
docker run -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:15
```

### Déploiement échoué

**Vérifications**:
1. Secrets GitHub configurés ?
2. Profil de publication valide ?
3. Tests passent ?
4. Health check endpoint fonctionne ?

**Rollback manuel**:
```bash
az webapp deployment slot swap \
  --name seeg-api-prod \
  --resource-group seeg-rg \
  --slot staging \
  --target-slot production
```

### Docker build lent

**Optimisations**:
- Utiliser le cache de layers
- Multi-stage builds (déjà implémenté)
- `.dockerignore` configuré

---

## 📚 Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure App Service](https://azure.microsoft.com/services/app-service/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Semantic Versioning](https://semver.org/)

---

**Note**: Ce pipeline est conçu pour être robuste et évolutif. N'hésitez pas à l'adapter selon vos besoins spécifiques.

