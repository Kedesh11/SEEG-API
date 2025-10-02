# 🤖 GitHub Actions - SEEG API

Ce dossier contient l'ensemble des workflows CI/CD pour l'automatisation du projet SEEG-API.

---

## 📁 Structure

```
.github/
├── workflows/
│   ├── ci.yml              # Tests et qualité du code
│   ├── pr-checks.yml       # Validation des pull requests
│   ├── deploy-azure.yml    # Déploiement sur Azure
│   └── release.yml         # Gestion des releases
├── labeler.yml             # Configuration labels automatiques
└── README.md               # Ce fichier
```

---

## 🔄 Workflows

### 1. CI (Intégration Continue)
**Fichier**: `ci.yml`  
**Déclenchement**: Push sur `main`/`develop` ou PR

**Jobs**:
- ✅ Tests (Python 3.11, 3.12, 3.13)
- ✅ Linting (Black, isort, flake8)
- ✅ Sécurité (Safety, Bandit)
- ✅ Coverage (Upload vers Codecov)

### 2. PR Checks
**Fichier**: `pr-checks.yml`  
**Déclenchement**: Ouverture/mise à jour de PR

**Jobs**:
- ✅ Validation format titre
- ✅ Tests avec coverage
- ✅ Revue de code automatique
- ✅ Vérification taille PR
- ✅ Scan de sécurité

### 3. Deploy Azure
**Fichier**: `deploy-azure.yml`  
**Déclenchement**: Push sur `main` (staging) ou tag `v*.*.*` (prod)

**Environnements**:
- 🟡 **Staging**: https://seeg-api-staging.azurewebsites.net
- 🟢 **Production**: https://www.seeg-api.com

### 4. Release
**Fichier**: `release.yml`  
**Déclenchement**: Push d'un tag `v*.*.*`

**Actions**:
- 📝 Génération changelog
- 🎉 Création release GitHub
- 🐳 Build & push image Docker

---

## 🚀 Usage

### Créer une Pull Request

```bash
# 1. Créer une branche
git checkout -b feat/nouvelle-fonctionnalite

# 2. Faire vos modifications
git add .
git commit -m "feat(api): ajouter nouvelle fonctionnalité"

# 3. Push et créer PR
git push origin feat/nouvelle-fonctionnalite
```

**Format du titre de PR requis**:
```
type(scope): description

Exemples:
✅ feat(auth): ajouter rate limiting
✅ fix(api): corriger validation PDF
✅ docs: mettre à jour README
```

### Déployer en Staging

```bash
# Simple push sur main
git push origin main

# Le déploiement se fait automatiquement
```

### Déployer en Production

```bash
# 1. Créer et pousser un tag
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# 2. Le workflow se déclenche:
#    - Tests complets
#    - Build Docker
#    - Déploiement prod (avec approbation)
#    - Migration BD
```

---

## 🔐 Secrets Requis

Configurez ces secrets dans: `Settings > Secrets and variables > Actions`

| Secret | Description |
|--------|-------------|
| `AZURE_WEBAPP_PUBLISH_PROFILE_STAGING` | Profil Azure (Staging) |
| `AZURE_WEBAPP_PUBLISH_PROFILE_PROD` | Profil Azure (Production) |
| `DATABASE_URL_PROD` | URL BD Production |
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub token |
| `CODECOV_TOKEN` | Token Codecov (optionnel) |

---

## 📊 Status Badges

```markdown
![CI](https://github.com/cnx40/seeg-api/workflows/CI/badge.svg)
![Deploy](https://github.com/cnx40/seeg-api/workflows/CD%20-%20Déploiement%20Azure/badge.svg)
![Coverage](https://codecov.io/gh/cnx40/seeg-api/branch/main/graph/badge.svg)
```

---

## 🔧 Développement Local

### Pre-commit Hooks

```bash
# Installer pre-commit
pip install pre-commit
pre-commit install

# Tester manuellement
pre-commit run --all-files
```

### Tester les workflows localement

```bash
# Installer act
brew install act  # macOS
choco install act  # Windows

# Exécuter un workflow
act -j test
```

---

## 📚 Documentation Complète

Consultez [docs/CI_CD.md](../docs/CI_CD.md) pour la documentation détaillée.

---

## 🆘 Support

Pour toute question sur les workflows:
1. Consulter la documentation
2. Vérifier les logs des actions
3. Ouvrir une issue avec le label `ci/cd`

---

**Dernière mise à jour**: 2 Octobre 2025

