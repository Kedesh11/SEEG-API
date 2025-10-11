# 🏢 One HCM SEEG Backend API

> **API de gestion des ressources humaines pour la SEEG**  
> *Société d'Énergie et d'Eau du Gabon*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-00C7B7?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Azure](https://img.shields.io/badge/Azure-Deployed-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Automated-success?logo=github-actions&logoColor=white)](#cicd)
[![Monitoring](https://img.shields.io/badge/Monitoring-App%20Insights-0078D4?logo=microsoft-azure&logoColor=white)](#monitoring--performance)

### 📊 Métriques clés

| Métrique | Valeur |
|----------|--------|
| **Endpoints API** | 85+ routes |
| **Lignes de code** | ~16,500 lignes |
| **Dépendances** | 51 packages Python |
| **Tables DB** | 12+ tables |
| **Uptime cible** | 99.9% |
| **Temps réponse (P95)** | < 500ms |
| **Disponibilité** | 24/7 |

### 🔗 Liens rapides

| Service | URL | Status |
|---------|-----|--------|
| **API Production** | [seeg-backend-api.azurewebsites.net](https://seeg-backend-api.azurewebsites.net) | 🟢 |
| **Documentation** | [/docs](https://seeg-backend-api.azurewebsites.net/docs) | 📖 |
| **Frontend Production** | [seeg-talentsource.com](https://www.seeg-talentsource.com) | 🌐 |
| **Frontend Staging** | [seeg-hcm.vercel.app](https://seeg-hcm.vercel.app) | 🧪 |

---

## 📋 Table des matières

- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#️-architecture)
- [Installation](#-installation)
  - [Dépendances Python (51 packages)](#-dépendances-python-51-packages)
- [Configuration](#️-configuration)
- [Déploiement](#-déploiement)
- [CI/CD - Déploiement Continu](#-cicd---déploiement-continu-automatique)
- [Monitoring & Performance](#-monitoring--performance)
  - [Application Insights](#-application-insights-production)
  - [Alertes automatiques](#-alertes-automatiques)
  - [Logs Analytics](#-log-analytics-workspace)
- [API Documentation](#-api-documentation)
- [Développement](#-développement)
- [Tests](#-tests)
- [Sécurité](#-sécurité)
- [Support](#-support)

---

## 🚀 Démarrage rapide (Quick Start)

### Pour les développeurs

```bash
# 1. Cloner et installer
git clone <repo>
cd SEEG-API
python -m venv env
.\env\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 2. Configurer
copy env.example .env
# Éditer .env avec vos paramètres DB

# 3. Migrations
alembic upgrade head

# 4. Lancer
uvicorn app.main:app --reload
```

➡️ API disponible sur `http://localhost:8000/docs`

### Pour le déploiement Azure (DevOps)

```powershell
# 1. Déploiement complet (première fois)
.\scripts\deploy-api-v2.ps1

# 2. Tester
.\scripts\test-deployment.ps1

# 3. Déploiements suivants (automatiques via CI/CD)
docker build -t seegbackend.azurecr.io/seeg-backend-api:latest .
docker push seegbackend.azurecr.io/seeg-backend-api:latest
# → Azure redéploie automatiquement ! 🎉
```

➡️ API disponible sur `https://seeg-backend-api.azurewebsites.net`

---

## 🎯 Aperçu

**One HCM SEEG Backend** est une API RESTful complète pour gérer l'ensemble du processus de recrutement de la SEEG :

- 🔐 **Authentification** avec JWT et refresh tokens
- 👥 **Gestion des utilisateurs** (candidats internes/externes, recruteurs, admins)
- 💼 **Offres d'emploi** avec filtrage interne/externe
- 📝 **Candidatures** avec tracking complet
- 📄 **Documents PDF** (CV, lettres, diplômes)
- 📊 **Évaluations** (protocoles MTP)
- 📅 **Entretiens** avec planification
- 🔔 **Notifications** en temps réel

### Frontend
- **Production** : [https://www.seeg-talentsource.com](https://www.seeg-talentsource.com)
- **Staging** : [https://seeg-hcm.vercel.app](https://seeg-hcm.vercel.app)

---

## ✨ Fonctionnalités

### 🔐 Authentification & Autorisation

**Système d'authentification multi-niveaux avec gestion des demandes d'accès**

#### Types de candidats
- **Candidats EXTERNES** : Accès immédiat après inscription
  - `candidate_status = 'externe'`
  - Aucun matricule requis
  - `statut = 'actif'` dès l'inscription
  
- **Candidats INTERNES avec email @seeg-gabon.com** : Accès immédiat
  - `candidate_status = 'interne'`
  - Matricule SEEG obligatoire et vérifié
  - Email professionnel @seeg-gabon.com requis
  - `statut = 'actif'` dès l'inscription
  
- **Candidats INTERNES sans email @seeg-gabon.com** : Validation requise
  - `candidate_status = 'interne'`
  - Matricule SEEG obligatoire et vérifié
  - Email personnel (gmail, yahoo, etc.)
  - `statut = 'en_attente'` → demande d'accès créée automatiquement
  - Validation par un recruteur nécessaire avant connexion

#### Statuts utilisateur
| Statut | Description | Connexion autorisée |
|--------|-------------|---------------------|
| `actif` | Compte actif et validé | ✅ OUI |
| `en_attente` | En attente de validation recruteur | ❌ NON |
| `inactif` | Compte désactivé temporairement | ❌ NON |
| `bloqué` | Compte bloqué (demande refusée) | ❌ NON |
| `archivé` | Compte archivé | ❌ NON |

#### Fonctionnalités
- Inscription avec validation métier complète
- Connexion multi-format (JSON, form-urlencoded)
- JWT avec access & refresh tokens (durées configurables)
- Gestion des rôles (candidate, recruiter, admin, observer)
- Réinitialisation de mot de passe par email
- Vérification de matricule SEEG en temps réel
- **Système de demandes d'accès** pour candidats internes sans email SEEG
- Messages d'erreur personnalisés selon le statut du compte
- Emails automatiques (bienvenue, validation, approbation, refus)

### 👥 Gestion des candidats
- **Candidats INTERNES** : Employés SEEG avec matricule
  - `is_internal_candidate = true`
  - Accès à TOUTES les offres d'emploi
  - Inscription avec matricule obligatoire
- **Candidats EXTERNES** : Candidatures externes sans matricule
  - `is_internal_candidate = false`
  - Accès uniquement aux offres non-internes
  - Inscription sans matricule
- Profils enrichis avec compétences et expérience
- Upload de documents (CV, lettres, diplômes)
- Historique complet des candidatures

### 💼 Offres d'emploi
- Création et gestion par les recruteurs
- **Filtrage automatique INTERNE/EXTERNE** :
  - Recruteur définit `is_internal_only` (true/false)
  - Candidats internes voient TOUTES les offres
  - Candidats externes voient UNIQUEMENT les offres accessibles
- Statuts multiples (draft, active, closed, cancelled)
- Statistiques par recruteur
- Recherche et filtrage avancés

### 📊 Évaluations
- Protocoles MTP (Méthode de Travail Personnalisé)
- Scoring automatisé
- Recommandations de recrutement
- Suivi de l'évolution des candidats

### 📄 Gestion documentaire
- Upload PDF sécurisé (10MB max)
- Stockage en base de données (BYTEA)
- Validation stricte (magic number + extension)
- Types : CV, lettre motivation, diplômes, certificats

---

## 🏗️ Architecture

### Principes appliqués
- ✅ **Clean Architecture** - Séparation claire des couches
- ✅ **SOLID Principles** - Code maintenable et extensible
- ✅ **Dependency Injection** - Testabilité maximale
- ✅ **Unit of Work Pattern** - Gestion des transactions

### Structure en couches

```
┌─────────────────────────────────────┐
│   PRESENTATION LAYER                │
│   (Endpoints FastAPI)               │
│   - Validation entrées              │
│   - Transactions explicites         │
│   - Gestion erreurs HTTP            │
└──────────────┬──────────────────────┘
               │ Depends(get_db)
               ↓
┌─────────────────────────────────────┐
│   SERVICE LAYER                     │
│   (Business Logic)                  │
│   - Logique métier pure             │
│   - PAS de commit/rollback          │
│   - Retourne objets métier          │
└──────────────┬──────────────────────┘
               │ utilise
               ↓
┌─────────────────────────────────────┐
│   DATA ACCESS LAYER                 │
│   (SQLAlchemy + PostgreSQL)         │
│   - Accès base de données           │
│   - Rollback automatique si erreur  │
│   - Session gérée par get_db()      │
└─────────────────────────────────────┘
```

### Stack technique

**Backend**
- FastAPI 0.109+ (async/await)
- SQLAlchemy 2.0+ (ORM async)
- PostgreSQL 16 (base de données)
- Redis (cache & rate limiting)
- Alembic (migrations)

**Sécurité**
- JWT (python-jose)
- Bcrypt (hashing passwords)
- CORS configuré
- Rate limiting (slowapi - désactivé temporairement)

**Monitoring**
- Structlog (logging JSON)
- OpenTelemetry (tracing)
- Prometheus (métriques)
- Application Insights (Azure)

---

## 🚀 Installation

### Prérequis

- **Python 3.12+**
- **PostgreSQL 16+**
- **Redis 7+** (optionnel, pour cache)
- **Docker** (optionnel, pour déploiement)
- **Azure CLI** (pour déploiement Azure)
- **Git**

### 📦 Dépendances Python (51 packages)

Organisées par catégorie dans `requirements.txt` :

#### 🎯 Core Framework
- `fastapi==0.104.1` - Framework web moderne
- `uvicorn[standard]==0.24.0.post1` - Serveur ASGI
- `pydantic==2.5.2` / `pydantic-settings==2.1.0` - Validation

#### 💾 Base de données
- `SQLAlchemy==2.0.23` - ORM async/sync
- `alembic==1.12.1` - Migrations
- `asyncpg==0.29.0` + `psycopg2-binary==2.9.9` - Drivers PostgreSQL

#### 🔐 Sécurité
- `python-jose[cryptography]==3.3.0` - JWT
- `passlib[bcrypt]==1.7.4` + `bcrypt==4.1.1` - Hachage

#### 📧 Email
- `fastapi-mail==1.4.1` + `aiosmtplib==2.0.2` - Service email

#### 📄 Fichiers & PDF
- `aiofiles==23.2.1` - Fichiers async
- `reportlab==4.0.7` - **Génération PDF** 🔥
- `python-magic==0.4.27` - Détection MIME

#### 📊 Monitoring
- `structlog==24.1.0` - Logs structurés
- `prometheus-client==0.19.0` - Métriques
- `opencensus-ext-azure==1.1.13` - App Insights
- `opentelemetry-*` (8 packages) - Tracing distribué

#### ⚡ Performance
- `redis==5.0.1` - Cache
- `slowapi==0.1.9` - Rate limiting
- `httpx==0.25.1` - HTTP async

> ⚠️ **Packages critiques** : `reportlab`, `fastapi-mail`, `slowapi`  
> Sans ces packages, l'API ne démarrera pas correctement.

### Installation locale

```bash
# 1. Cloner le repository
git clone <votre-repo>
cd SEEG-API

# 2. Créer l'environnement virtuel
python -m venv env

# 3. Activer l'environnement (Windows)
.\env\Scripts\Activate.ps1

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Copier et configurer .env
copy env.example .env
# Editer .env avec vos paramètres

# 6. Créer la base de données
psql -U postgres -c "CREATE DATABASE recruteur;"

# 7. Appliquer les migrations
alembic upgrade head

# 8. Créer le premier administrateur
python -c "
import asyncio
from app.db.database import AsyncSessionLocal
from app.services.auth import AuthService
from app.schemas.auth import CreateUserRequest

async def create_admin():
    async with AsyncSessionLocal() as db:
        service = AuthService(db)
        admin_data = CreateUserRequest(
            email='admin@seeg.ga',
            password='AdminSecure123!',
            first_name='Admin',
            last_name='SEEG',
            role='admin'
        )
        user = await service.create_user(admin_data)
        await db.commit()
        print(f'✅ Admin créé: {user.email}')

asyncio.run(create_admin())
"

# 9. Démarrer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera accessible sur : **http://localhost:8000**  
Documentation Swagger : **http://localhost:8000/docs**

---

## ⚙️ Configuration

### Fichier .env

Variables essentielles :

```bash
# Environnement
ENVIRONMENT=development
DEBUG=true

# Base de données
DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5432/recruteur
DATABASE_URL_SYNC=postgresql://postgres:<password>@localhost:5432/recruteur

# Sécurité (CHANGEZ EN PRODUCTION)
SECRET_KEY=<minimum-32-caracteres-aleatoires>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
ALLOWED_CREDENTIALS=true

# Email (optionnel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<votre-email>
SMTP_PASSWORD=<app-password>
```

### Générer une SECRET_KEY sécurisée

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 🐳 Déploiement

### Docker Compose (Local/Staging)

```bash
# Démarrer tous les services
docker-compose up -d

# Services inclus :
# - seeg-api (API FastAPI)
# - postgres (PostgreSQL 16)
# - redis (Cache)
# - jaeger (Tracing)
# - prometheus (Métriques)
# - grafana (Visualisation)
# - nginx (Reverse proxy)

# Vérifier les logs
docker-compose logs -f seeg-api

# Arrêter
docker-compose down
```

### Azure App Service (Production)

#### Architecture de déploiement séparé

Le système utilise une architecture moderne avec **séparation des responsabilités** :

- **`deploy-api.ps1`** : Déploie uniquement l'application (sans migrations)
- **`run-migrations.ps1`** : Exécute les migrations de base de données séparément

**Avantages** :
- ✅ L'API ne peut plus être bloquée par des erreurs de migration
- ✅ Meilleur contrôle sur chaque étape
- ✅ Logs séparés et plus clairs
- ✅ Rollback granulaire possible

#### Prérequis Azure
- Azure CLI installé
- Connexion Azure active (`az login`)
- App Service créé
- Azure PostgreSQL configuré
- Container Registry configuré

#### Configuration Azure

**Variables d'environnement** (App Service → Configuration) :

```bash
# Environnement
ENVIRONMENT=production
DEBUG=false
SKIP_MIGRATIONS=true  # ← IMPORTANT: Ignorer les migrations au démarrage

# Sécurité
SECRET_KEY=<generer-une-cle-securisee>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Base de données
DATABASE_URL=postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres

# CORS
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
ALLOWED_CREDENTIALS=true

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=<votre-connection-string>
```

#### Workflow de déploiement complet

**1. Déployer l'application**

```powershell
# Build dans le cloud (recommandé - pas besoin de Docker local)
.\scripts\deploy-api.ps1

# Ou avec build local si Docker disponible
.\scripts\deploy-api.ps1 -BuildMode local

# Avec un tag spécifique
.\scripts\deploy-api.ps1 -ImageTag "v1.2.3"
```

**Ce que fait ce script** :
- ✅ Vérifie les prérequis (Azure CLI, Docker si build local)
- ✅ Génère un tag de déploiement basé sur le timestamp
- ✅ Construit l'image Docker (localement ou dans Azure)
- ✅ Configure l'App Service avec `SKIP_MIGRATIONS=true`
- ✅ Déploie l'image sur Azure
- ✅ Redémarre l'application
- ✅ Effectue un health check

**2. Exécuter les migrations**

```powershell
# Appliquer toutes les migrations en attente
.\scripts\run-migrations.ps1

# Voir l'état actuel des migrations
.\scripts\run-migrations.ps1 -Action current

# Voir l'historique complet
.\scripts\run-migrations.ps1 -Action history

# Revenir à la version précédente
.\scripts\run-migrations.ps1 -Action downgrade -Target "-1"
```

**Ce que fait ce script** :
- ✅ Vérifie les prérequis (Azure CLI, Python, Alembic)
- ✅ Récupère la chaîne de connexion depuis Azure
- ✅ Ajoute automatiquement votre IP au firewall PostgreSQL
- ✅ Affiche l'état actuel des migrations
- ✅ Exécute les migrations
- ✅ Propose de nettoyer la règle de firewall temporaire

**3. Vérifier le déploiement**

```bash
# Health check
curl https://seeg-backend-api.azurewebsites.net/health

# Documentation Swagger
https://seeg-backend-api.azurewebsites.net/docs

# Logs en temps réel
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg
```

#### Commandes avancées

**Paramètres du script deploy-api.ps1** :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `BuildMode` | `cloud` | `cloud` (build Azure) ou `local` (build local) |
| `ResourceGroup` | `seeg-backend-rg` | Groupe de ressources Azure |
| `AppName` | `seeg-backend-api` | Nom de l'App Service |
| `ContainerRegistry` | `seegbackend` | Nom du Container Registry |
| `ImageTag` | `latest` | Tag de l'image Docker |

**Paramètres du script run-migrations.ps1** :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `Action` | `upgrade` | `upgrade`, `downgrade`, `current`, `history` |
| `Target` | `head` | Cible de la migration (ex: `head`, `-1`, ID) |
| `ResourceGroup` | `seeg-backend-rg` | Groupe de ressources Azure |
| `AppName` | `seeg-backend-api` | Nom de l'App Service |
| `PostgresServer` | `seeg-postgres-server` | Nom du serveur PostgreSQL |

**Exemples d'utilisation** :

```powershell
# Déploiement complet standard
.\scripts\deploy-api.ps1
.\scripts\run-migrations.ps1

# Build local avec tag spécifique
.\scripts\deploy-api.ps1 -BuildMode local -ImageTag "v1.5.0"

# Rollback d'une migration
.\scripts\run-migrations.ps1 -Action downgrade -Target "-1"

# Voir les migrations sans les appliquer
.\scripts\run-migrations.ps1 -Action history
```

#### Dépannage

**Problème : L'API ne démarre pas**

```powershell
# Vérifier les logs
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg

# Vérifier l'état
az webapp show --name seeg-backend-api --resource-group seeg-backend-rg --query state

# Redémarrer
az webapp restart --name seeg-backend-api --resource-group seeg-backend-rg
```

**Problème : Les migrations échouent**

```powershell
# Vérifier l'état de la base
.\scripts\run-migrations.ps1 -Action current

# Vérifier que votre IP est autorisée
az postgres flexible-server firewall-rule list `
  --resource-group seeg-backend-rg `
  --name seeg-postgres-server

# Ajouter votre IP manuellement
az postgres flexible-server firewall-rule create `
  --resource-group seeg-backend-rg `
  --name seeg-postgres-server `
  --rule-name "mon-ip" `
  --start-ip-address <votre-ip> `
  --end-ip-address <votre-ip>
```

**Problème : Erreur de réseau Docker (build local)**

Solution : Utiliser le build cloud
```powershell
.\scripts\deploy-api.ps1 -BuildMode cloud
```

#### Bonnes pratiques

**Avant le déploiement** :
- ✅ Tester localement avec Docker Compose
- ✅ Vérifier que tous les tests passent
- ✅ Sauvegarder la base de données si changements critiques

**Pendant le déploiement** :
- ✅ Utiliser le build cloud pour plus de fiabilité
- ✅ Surveiller les logs pendant le démarrage
- ✅ Vérifier le health check après déploiement

**Après le déploiement** :
- ✅ Tester les endpoints critiques
- ✅ Vérifier les métriques Azure
- ✅ Surveiller les erreurs dans Application Insights

**Pour les migrations** :
- ⚠️ **TOUJOURS** tester sur un environnement de staging d'abord
- ⚠️ **TOUJOURS** avoir un plan de rollback
- ⚠️ **JAMAIS** supprimer une colonne sans migration en plusieurs étapes
- ✅ Faire des backups avant les migrations importantes

---

## 🔄 CI/CD - Déploiement Continu Automatique

### 🎯 Vue d'ensemble

L'API SEEG dispose d'un système de **CI/CD automatique** configuré avec Azure :

```
┌──────────────────────────────────────────────────────────────┐
│                    WORKFLOW CI/CD                            │
├──────────────────────────────────────────────────────────────┤
│  1. Build image Docker (local ou cloud)                     │
│  2. Push vers Azure Container Registry                      │
│  3. Webhook ACR déclenché automatiquement                   │
│  4. App Service détecte la nouvelle image                   │
│  5. Redéploiement automatique sans intervention             │
│  6. Health check vérifie que tout fonctionne                │
└──────────────────────────────────────────────────────────────┘
```

### 🚀 Déploiement initial (première fois)

#### Étape 1 : Déploiement complet avec monitoring

```powershell
# Déploiement complet avec logs détaillés
.\scripts\deploy-api-v2.ps1

# Avec logs de debug
.\scripts\deploy-api-v2.ps1 -LogLevel DEBUG

# Build dans le cloud (recommandé)
.\scripts\deploy-api-v2.ps1 -BuildMode cloud

# Simulation (dry-run)
.\scripts\deploy-api-v2.ps1 -DryRun
```

**Ce script fait TOUT automatiquement** :
1. ✅ Valide les prérequis (Azure CLI, Docker)
2. ✅ Vérifie les ressources Azure
3. ✅ Build l'image Docker avec tous les packages
4. ✅ Push vers Azure Container Registry
5. ✅ Crée/Met à jour l'App Service
6. ✅ Configure toutes les variables d'environnement
7. ✅ Redémarre l'application
8. ✅ **Active le CI/CD automatique** 🔥
9. ✅ **Configure Application Insights** 🔥
10. ✅ **Configure toutes les alertes** 🔥
11. ✅ Vérifie le health check
12. ✅ Génère un rapport détaillé

#### Étape 2 : Vérifier le déploiement

```powershell
# Tests automatisés complets
.\scripts\test-deployment.ps1

# Voir les logs
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg
```

### 🔄 Déploiements suivants (CI/CD automatique)

Une fois le CI/CD configuré, **chaque push d'image déclenche automatiquement un redéploiement** :

```powershell
# Méthode 1 : Build + Push (déclenchera automatiquement le redéploiement)
docker build -t seegbackend.azurecr.io/seeg-backend-api:latest .
docker push seegbackend.azurecr.io/seeg-backend-api:latest
# → Azure détecte et redéploie automatiquement ! 🎉

# Méthode 2 : Utiliser le script (build + push + attendre le redéploiement)
.\scripts\deploy-api-v2.ps1
# → Build, push, configure CI/CD, surveille le redéploiement
```

### 📊 Logs détaillés du déploiement

Chaque déploiement génère des logs ultra-détaillés :

```
logs/
├── deploy_20251010_153045.log          # Log complet du déploiement
├── deploy_20251010_153045_errors.log   # Uniquement les erreurs
└── deploy_20251010_153045_report.json  # Rapport JSON pour automatisation
```

**Contenu du log** :
```
[2025-10-10 15:30:45.123] [INFO] Démarrage de l'étape: Validation des prérequis
[2025-10-10 15:30:45.234] [INFO] Azure CLI détecté | Version=2.54.0
[2025-10-10 15:30:45.345] [INFO] Docker détecté | Version=Docker version 24.0.6
[2025-10-10 15:30:45.456] [INFO] Connecté à Azure | Subscription=Azure subscription 1
[2025-10-10 15:30:46.567] [INFO] ✅ Étape 'Validation des prérequis' terminée: Success (1.44s)
```

### 🎯 Surveillance du CI/CD

#### Vérifier les webhooks

```powershell
# Liste des webhooks ACR
az acr webhook list --registry seegbackend --output table

# Événements récents du webhook
az acr webhook list-events `
    --name seeg-backend-apiWebhook `
    --registry seegbackend `
    --output table

# Pinger le webhook manuellement
az acr webhook ping --name seeg-backend-apiWebhook --registry seegbackend
```

#### Vérifier l'état du déploiement

```powershell
# Statut de l'App Service
az webapp show `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --query "{State:state,Image:siteConfig.linuxFxVersion}" `
    --output table

# Historique des déploiements
az webapp deployment list `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --output table
```

### 🛠️ Configuration avancée du CI/CD

#### Modifier le webhook

```powershell
# Désactiver temporairement le CI/CD
az webapp deployment container config `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --enable-cd false

# Réactiver
az webapp deployment container config `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --enable-cd true
```

#### Filtrer les déploiements par tag

Le webhook est configuré pour réagir aux images avec le pattern :
- `seeg-backend-api:*` → Tous les tags
- `seeg-backend-api:latest` → Uniquement latest
- `seeg-backend-api:deploy-*` → Uniquement les tags de déploiement

Pour modifier :
```powershell
az acr webhook update `
    --name seeg-backend-apiWebhook `
    --registry seegbackend `
    --scope "seeg-backend-api:latest"  # Réagir uniquement à :latest
```

### 📈 Métriques de déploiement

Chaque déploiement génère un rapport JSON :

```json
{
  "StartTime": "2025-10-10T15:30:45",
  "EndTime": "2025-10-10T15:35:12",
  "Duration": 267.45,
  "Steps": [
    {
      "Name": "Validation des prérequis",
      "Duration": 1.44,
      "Status": "Success"
    },
    {
      "Name": "Build Docker Image",
      "Duration": 180.23,
      "Status": "Success"
    }
  ],
  "Warnings": 2,
  "Errors": 0,
  "Success": true
}
```

Utilisez ce JSON pour :
- Tracking des performances de build
- Détection de régressions (durée qui augmente)
- Alertes si déploiement > 10 minutes
- Métriques DevOps

### 🔧 Scripts disponibles

| Script | Description | Usage |
|--------|-------------|-------|
| `deploy-api-v2.ps1` | Déploiement complet avec monitoring | Production |
| `setup-cicd.ps1` | Configuration CI/CD uniquement | Configuration |
| `setup-monitoring.ps1` | Configuration monitoring seul | Configuration |
| `test-deployment.ps1` | Tests automatisés du déploiement | Validation |
| `run-migrations.ps1` | Migrations base de données | Maintenance |

---

## 📚 API Documentation

### Endpoints principaux

#### 🔐 Authentification (`/api/v1/auth`)

| Méthode | Endpoint | Description | Auth | Détails |
|---------|----------|-------------|------|---------|
| POST | `/login` | Connexion utilisateur | Non | Vérifie le statut du compte. Refuse si `statut != 'actif'` |
| POST | `/signup` | Inscription candidat (interne/externe) | Non | Crée automatiquement une demande d'accès si interne sans email SEEG |
| POST | `/verify-matricule` | Vérifier un matricule SEEG | Non | Endpoint public pour validation en temps réel lors de l'inscription |
| POST | `/create-user` | Créer utilisateur (admin/recruteur) | Admin | Réservé aux administrateurs |
| GET | `/me` | Profil utilisateur connecté | Oui | Informations complètes du compte |
| POST | `/refresh` | Rafraîchir le token JWT | Non | Avec refresh_token |
| POST | `/logout` | Déconnexion | Oui | Invalide le token |
| POST | `/forgot-password` | Demander réinitialisation MdP | Non | Envoie un email avec lien |
| POST | `/reset-password` | Confirmer réinitialisation MdP | Non | Avec token reçu par email |
| POST | `/change-password` | Changer le mot de passe | Oui | Nécessite l'ancien MdP |
| GET | `/verify-user-matricule` | Vérifier matricule de l'utilisateur connecté | Candidat | Vérifie contre `seeg_agents` |

#### 👥 Gestion des Demandes d'Accès (`/api/v1/access-requests`)

**Nouveaux endpoints pour gérer les demandes d'accès des candidats internes sans email @seeg-gabon.com**

| Méthode | Endpoint | Description | Auth | Permissions |
|---------|----------|-------------|------|-------------|
| GET | `/` | Lister toutes les demandes d'accès | Oui | Recruteur, Admin, Observateur |
| POST | `/approve` | Approuver une demande | Oui | Recruteur, Admin |
| POST | `/reject` | Refuser une demande (avec motif) | Oui | Recruteur, Admin |
| POST | `/mark-all-viewed` | Marquer toutes comme vues | Oui | Recruteur, Admin, Observateur |
| GET | `/unviewed-count` | Nombre de demandes non vues | Oui | Recruteur, Admin, Observateur |

**Workflow des demandes d'accès :**
1. Candidat interne s'inscrit sans email @seeg-gabon.com
2. Compte créé avec `statut='en_attente'`
3. Demande d'accès créée automatiquement avec `status='pending'`
4. Emails envoyés (candidat + support@seeg-talentsource.com)
5. Recruteur voit la demande dans son dashboard avec badge de notification
6. Recruteur approuve → `statut='actif'`, email de confirmation
7. OU Recruteur refuse (motif ≥ 20 caractères) → `statut='bloqué'`, email avec motif

#### 👥 Utilisateurs (`/api/v1/users`)
- GET `/` - Liste des utilisateurs
- GET `/{id}` - Détails utilisateur
- PUT `/{id}` - Modifier utilisateur
- DELETE `/{id}` - Supprimer utilisateur

#### 💼 Offres d'emploi (`/api/v1/jobs`)
- GET `/` - Liste des offres **(filtrées automatiquement selon type candidat)**
  - Candidat INTERNE → Toutes les offres
  - Candidat EXTERNE → Uniquement offres is_internal_only=false
  - Recruteur/Admin → Toutes les offres
- POST `/` - Créer offre (avec champ `is_internal_only`)
- GET `/{id}` - Détails offre
- PUT `/{id}` - Modifier offre (peut changer `is_internal_only`)
- DELETE `/{id}` - Supprimer offre

#### 📝 Candidatures (`/api/v1/applications`)
- POST `/` - Soumettre candidature
- GET `/` - Lister candidatures
- GET `/{id}` - Détails candidature
- PUT `/{id}/status` - Changer statut
- POST `/{id}/documents` - Upload PDF

### Exemples d'utilisation

#### 📋 SCÉNARIO 1 : Inscription candidat EXTERNE

**Caractéristiques** : Accès immédiat, aucun matricule requis

```json
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "jean.externe@gmail.com",
  "password": "SecurePass#2025!Strong",
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone": "+24106223344",
  "date_of_birth": "1990-05-15",
  "sexe": "M",
  "candidate_status": "externe",
  "matricule": null,
  "no_seeg_email": false,
  "adresse": "123 Rue de la Liberté, Libreville",
  "poste_actuel": null,
  "annees_experience": 5
}
```

**Résultat** :
- ✅ Compte créé avec `statut='actif'`
- ✅ Connexion immédiate possible
- ✅ Email de bienvenue envoyé
- ❌ Aucune demande d'accès créée

---

#### 📋 SCÉNARIO 2 : Inscription candidat INTERNE avec email @seeg-gabon.com

**Caractéristiques** : Accès immédiat, matricule vérifié, email professionnel

```json
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "jean.dupont@seeg-gabon.com",
  "password": "SecurePass#2025!Strong",
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone": "+24106223344",
  "date_of_birth": "1990-05-15",
  "sexe": "M",
  "candidate_status": "interne",
  "matricule": 123456,
  "no_seeg_email": false,
  "adresse": "456 Avenue Omar Bongo, Libreville",
  "poste_actuel": "Technicien Réseau Eau",
  "annees_experience": 8
}
```

**Résultat** :
- ✅ Matricule vérifié dans `seeg_agents`
- ✅ Email @seeg-gabon.com validé
- ✅ Compte créé avec `statut='actif'`
- ✅ Connexion immédiate possible
- ✅ Email de bienvenue envoyé
- ❌ Aucune demande d'accès créée

---

#### 📋 SCÉNARIO 3 : Inscription candidat INTERNE sans email @seeg-gabon.com

**Caractéristiques** : Validation recruteur requise, matricule vérifié, email personnel

```json
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "jean.perso@gmail.com",
  "password": "SecurePass#2025!Strong",
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone": "+24106223344",
  "date_of_birth": "1990-05-15",
  "sexe": "M",
  "candidate_status": "interne",
  "matricule": 123456,
  "no_seeg_email": true,
  "adresse": "789 Quartier Montagne, Libreville",
  "poste_actuel": "Agent Commercial",
  "annees_experience": 3
}
```

**Résultat** :
- ✅ Matricule vérifié dans `seeg_agents`
- ✅ Compte créé avec `statut='en_attente'`
- ✅ Demande d'accès créée automatiquement (`status='pending'`)
- ✅ Email "Demande en attente" envoyé au candidat
- ✅ Email notification envoyé à support@seeg-talentsource.com
- ❌ Connexion IMPOSSIBLE tant que non approuvé
- ⏳ Recruteur doit approuver/refuser

**Approbation par recruteur :**
```json
POST /api/v1/access-requests/approve

{
  "request_id": "uuid-de-la-demande"
}
```
→ `users.statut = 'actif'`, `access_requests.status = 'approved'`, email envoyé

**Refus par recruteur :**
```json
POST /api/v1/access-requests/reject

{
  "request_id": "uuid-de-la-demande",
  "rejection_reason": "Matricule invalide ou informations non vérifiables. Veuillez contacter le service RH."
}
```
→ `users.statut = 'bloqué'`, `access_requests.status = 'rejected'`, email avec motif envoyé

#### Créer une offre réservée aux internes

```bash
POST /api/v1/jobs
Authorization: Bearer <recruteur_token>
Content-Type: application/json

{
  "title": "Technicien Réseau Senior",
  "description": "Poste réservé aux employés SEEG",
  "location": "Libreville",
  "contract_type": "CDI",
  "is_internal_only": true,    # ← Réservée aux INTERNES uniquement
  ...
}
```

#### Lister les offres (filtrage automatique)

```bash
GET /api/v1/jobs
Authorization: Bearer <candidat_externe_token>

# Réponse: Uniquement les offres avec is_internal_only = false
# Les offres internes ne sont PAS visibles pour ce candidat externe
```

---

### 🔐 Règles métier du système d'authentification

#### Validation lors de l'inscription

**1. Candidat EXTERNE (`candidate_status = 'externe'`)**
- ✅ Matricule = NULL (non requis)
- ✅ Email quelconque accepté
- ✅ Résultat : `statut = 'actif'` → Connexion immédiate

**2. Candidat INTERNE avec email SEEG (`candidate_status = 'interne'`, `no_seeg_email = false`)**
- ✅ Matricule OBLIGATOIRE et vérifié dans `seeg_agents`
- ✅ Email DOIT se terminer par `@seeg-gabon.com`
- ✅ Résultat : `statut = 'actif'` → Connexion immédiate

**3. Candidat INTERNE sans email SEEG (`candidate_status = 'interne'`, `no_seeg_email = true`)**
- ✅ Matricule OBLIGATOIRE et vérifié dans `seeg_agents`
- ✅ Email quelconque accepté (gmail, yahoo, etc.)
- ⏳ Résultat : `statut = 'en_attente'` → **Validation recruteur requise**
- 📧 Emails envoyés :
  - Candidat : "Demande en attente de validation"
  - Support : "Nouvelle demande d'accès"

#### Validation lors de la connexion

**Messages d'erreur personnalisés selon le statut :**

| Statut | Message | Code HTTP |
|--------|---------|-----------|
| `en_attente` | "Votre compte est en attente de validation par notre équipe. Vous recevrez un email de confirmation une fois votre accès validé." | 403 |
| `bloqué` | "Votre compte a été bloqué. Veuillez contacter l'administrateur à support@seeg-talentsource.com" | 403 |
| `inactif` | "Votre compte a été désactivé. Veuillez contacter l'administrateur à support@seeg-talentsource.com" | 403 |
| `archivé` | "Votre compte a été archivé. Veuillez contacter l'administrateur à support@seeg-talentsource.com" | 403 |
| `actif` | ✅ Connexion autorisée | 200 |

#### Workflow d'approbation/refus

**Approbation par recruteur** :
1. Vérifier permissions (recruteur ou admin)
2. Mettre à jour `users.statut = 'actif'`
3. Mettre à jour `access_requests.status = 'approved'`
4. Enregistrer `reviewed_at` et `reviewed_by`
5. Envoyer email de confirmation au candidat

**Refus par recruteur** :
1. Vérifier permissions (recruteur ou admin)
2. Valider le motif (≥ 20 caractères)
3. Mettre à jour `users.statut = 'bloqué'`
4. Mettre à jour `access_requests.status = 'rejected'`
5. Enregistrer `rejection_reason`, `reviewed_at` et `reviewed_by`
6. Envoyer email avec motif au candidat

#### Badge de notification (pour recruteurs)

**Comptage des demandes non vues** :
```sql
SELECT COUNT(*) FROM access_requests 
WHERE status = 'pending' AND viewed = false;
```

**Marquage automatique comme vues** :
- Appelé automatiquement quand un recruteur visite `/api/v1/access-requests`
- `UPDATE access_requests SET viewed = true WHERE status = 'pending' AND viewed = false`
- Badge passe à (0)
- Nouvelles demandes futures réafficheront le badge

---

#### Connexion

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@seeg.ga",
  "password": "SecurePass123!"
}

# Réponse:
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Requête authentifiée

```bash
GET /api/v1/auth/me
Authorization: Bearer <access_token>

# Réponse: Profil utilisateur complet
```

---

## 💻 Développement

### Structure du projet

```
SEEG-API/
├── app/
│   ├── api/v1/endpoints/      # Endpoints FastAPI
│   ├── core/                  # Configuration, sécurité, logging
│   ├── db/                    # Database, migrations, UoW
│   ├── models/                # Models SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   ├── services/              # Business logic (PURE)
│   ├── middleware/            # Middlewares custom
│   └── main.py                # Point d'entrée
├── tests/                     # Tests pytest
├── scripts/                   # Scripts utilitaires
├── monitoring/                # Config Prometheus/Grafana
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Stack complète
├── alembic.ini                # Config migrations
├── requirements.txt           # Dépendances Python
└── README.md                  # Ce fichier
```

### Principes de développement

#### 1. Architecture en couches

**Endpoints** (Presentation Layer)
- Gestion des requêtes HTTP
- Validation des entrées (Pydantic)
- **Gestion des transactions** (commit/rollback)
- Conversion des réponses

```python
@router.post("/signup")
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Service fait la logique
    user = await auth_service.create_candidate(data)
    
    # Endpoint gère la transaction
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)
```

**Services** (Business Logic Layer)
- Logique métier pure
- **NE FAIT PAS** de commit/rollback
- Retourne des objets métier

```python
class AuthService:
    async def create_candidate(self, data) -> User:
        # Validations métier
        # Création de l'objet
        user = User(...)
        self.db.add(user)
        # ✅ PAS de commit ici
        return user
```

**Database** (Data Access Layer)
- Gestion du lifecycle des sessions
- Rollback automatique en cas d'erreur

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

#### 2. Gestion des erreurs

```python
# Exceptions personnalisées
class ValidationError(Exception): pass
class NotFoundError(Exception): pass
class UnauthorizedError(Exception): pass
class BusinessLogicError(Exception): pass

# Dans les services
raise ValidationError("Email déjà utilisé")

# Dans les endpoints
except ValidationError as e:
    raise HTTPException(400, detail=str(e))
```

#### 3. Logging structuré

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("User created", user_id=user.id, email=user.email)
```

### Créer une nouvelle migration

```bash
# 1. Modifier le modèle dans app/models/
# 2. Générer la migration
alembic revision --autogenerate -m "description"

# 3. Vérifier le fichier généré
# app/db/migrations/versions/<date>_<description>.py

# 4. Appliquer la migration
alembic upgrade head
```

### Ajouter un nouveau endpoint

1. **Créer le schema** (`app/schemas/`)
2. **Ajouter la méthode au service** (`app/services/`) - SANS commit
3. **Créer l'endpoint** (`app/api/v1/endpoints/`) - AVEC commit
4. **Ajouter les tests** (`tests/`)

---

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_auth_endpoints.py -v
pytest tests/test_auth_endpoints.py::test_login_success -v
```

### Tests manuels avec Postman

Une collection Postman complète est fournie :
- Import `SEEG_API.postman_collection.json`
- Variables automatiques (tokens sauvegardés)
- 8+ requêtes préconfigurées

### Tests avec curl

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@seeg.ga","password":"Admin123!"}'

# Avec token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## 📊 Monitoring & Performance

### 🎯 Vue d'ensemble

L'API SEEG dispose d'un système de monitoring complet à plusieurs niveaux :

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                         │
├─────────────────────────────────────────────────────────────┤
│  Application Insights  →  Traces + Métriques + Exceptions  │
│  Log Analytics         →  Requêtes KQL + Corrélations      │
│  Azure Monitor         →  Métriques système + Alertes      │
│  Prometheus            →  Métriques custom applicatives    │
│  Logs structurés       →  JSON + Console (dev)             │
└─────────────────────────────────────────────────────────────┘
```

### 🔍 Application Insights (Production)

**Configuration automatique lors du déploiement.**

#### Fonctionnalités activées

| Fonctionnalité | Description | Status |
|----------------|-------------|--------|
| **Distributed Tracing** | Traçage end-to-end des requêtes | ✅ Activé |
| **Dependency Tracking** | Suivi PostgreSQL, Redis, HTTP | ✅ Activé |
| **Exception Tracking** | Capture automatique des exceptions | ✅ Activé |
| **Performance Metrics** | CPU, RAM, requêtes/sec, latence | ✅ Activé |
| **Live Metrics** | Métriques temps réel | ✅ Activé |
| **Profiler** | Profiling des performances | ✅ Activé |
| **Snapshot Debugger** | Capture de l'état lors d'exceptions | ✅ Activé |
| **Custom Events** | Événements métier custom | ✅ Activé |

#### Accès

Portail Azure → Application Insights → `seeg-api-insights`

#### Requêtes KQL utiles

```kql
// Erreurs des dernières 24h
exceptions
| where timestamp > ago(24h)
| summarize count() by type, outerMessage
| order by count_ desc

// Top 10 requêtes les plus lentes
requests
| where timestamp > ago(1h)
| top 10 by duration desc
| project timestamp, name, duration, resultCode

// Taux d'erreur par endpoint
requests
| where timestamp > ago(1h)
| summarize total=count(), errors=countif(success == false) by name
| extend error_rate = (errors * 100.0) / total
| order by error_rate desc

// Dépendances PostgreSQL
dependencies
| where type == "SQL"
| where timestamp > ago(1h)
| summarize avg(duration), count() by name
| order by avg_duration desc
```

### 📊 Azure Monitor - Métriques système

Métriques collectées automatiquement (toutes les 1 minute) :

| Métrique | Description | Seuil d'alerte |
|----------|-------------|----------------|
| `CpuPercentage` | Utilisation CPU | > 80% |
| `MemoryPercentage` | Utilisation RAM | > 80% |
| `ResponseTime` | Temps de réponse moyen | > 3s |
| `Http5xx` | Erreurs serveur | > 10 en 5min |
| `Http4xx` | Erreurs client | > 50 en 5min |
| `Requests` | Requêtes/seconde | - |
| `BytesReceived` | Bande passante entrante | - |
| `BytesSent` | Bande passante sortante | - |

#### Voir les métriques

```powershell
# Métriques des dernières 24h
az monitor metrics list `
    --resource /subscriptions/.../resourceGroups/seeg-backend-rg/providers/Microsoft.Web/sites/seeg-backend-api `
    --metric-names CpuPercentage MemoryPercentage ResponseTime `
    --start-time (Get-Date).AddHours(-24) `
    --interval PT1M

# Export en CSV
az monitor metrics list ... --output table > metrics.csv
```

### 🔔 Alertes automatiques

5 alertes sont configurées automatiquement :

#### 1. CPU Élevé (Sévérité: 2 - Warning)
- **Condition**: CPU > 80% pendant 5 minutes
- **Action**: Email à `support@cnx4-0.com`
- **Recommandation**: Scale up le plan

#### 2. Mémoire Élevée (Sévérité: 2 - Warning)
- **Condition**: RAM > 80% pendant 5 minutes
- **Action**: Email + investigation
- **Recommandation**: Vérifier fuites mémoire

#### 3. Erreurs HTTP 5xx (Sévérité: 1 - Error)
- **Condition**: > 10 erreurs 5xx en 5 minutes
- **Action**: Email urgent
- **Recommandation**: Vérifier les logs

#### 4. Temps de réponse lent (Sévérité: 2 - Warning)
- **Condition**: Temps moyen > 3s pendant 5 minutes
- **Action**: Email
- **Recommandation**: Optimiser les requêtes DB

#### 5. Application Down (Sévérité: 0 - Critical)
- **Condition**: Health check échoué
- **Action**: Email critique + SMS
- **Recommandation**: Redémarrage immédiat

#### Gérer les alertes

```powershell
# Lister toutes les alertes
az monitor metrics alert list --resource-group seeg-backend-rg

# Activer/Désactiver une alerte
az monitor metrics alert update --name seeg-api-high-cpu --enabled false

# Voir les alertes déclenchées
az monitor metrics alert show --name seeg-api-high-cpu --output table
```

### 📝 Log Analytics Workspace

**Workspace**: `seeg-api-logs`

#### Catégories de logs

| Catégorie | Rétention | Description |
|-----------|-----------|-------------|
| `AppServiceHTTPLogs` | 30 jours | Logs HTTP (accès, codes status) |
| `AppServiceConsoleLogs` | 30 jours | Logs de la console Docker |
| `AppServiceAppLogs` | 30 jours | Logs de l'application Python |
| `AppServiceAuditLogs` | 90 jours | Logs d'audit (sécurité) |
| `AppServicePlatformLogs` | 30 jours | Logs de la plateforme Azure |

#### Requêtes KQL utiles

```kql
// Logs HTTP des dernières 24h
AppServiceHTTPLogs
| where TimeGenerated > ago(24h)
| project TimeGenerated, CsMethod, CsUriStem, ScStatus, TimeTaken
| order by TimeGenerated desc

// Erreurs dans les logs console
AppServiceConsoleLogs
| where TimeGenerated > ago(1h)
| where ResultDescription contains "error" or ResultDescription contains "exception"
| project TimeGenerated, ResultDescription

// Top 10 endpoints les plus appelés
AppServiceHTTPLogs
| where TimeGenerated > ago(24h)
| summarize count() by CsUriStem
| top 10 by count_
| order by count_ desc

// Analyse des temps de réponse
AppServiceHTTPLogs
| where TimeGenerated > ago(1h)
| summarize avg(TimeTaken), max(TimeTaken), min(TimeTaken) by bin(TimeGenerated, 5m)
| render timechart
```

### ⚡ Performance & Optimisations

#### Optimisations activées

- ✅ **Always On**: Application toujours active (pas de cold start)
- ✅ **HTTP 2.0**: Multiplexage des requêtes
- ✅ **Worker 64-bit**: Meilleure utilisation mémoire
- ✅ **Health Check**: Monitoring continu sur `/docs`
- ✅ **TLS 1.2+**: Sécurité renforcée
- ✅ **Compression**: Réduction de la bande passante

#### Métriques de performance attendues

| Métrique | Cible | Limite |
|----------|-------|--------|
| Temps de réponse (P50) | < 200ms | < 1s |
| Temps de réponse (P95) | < 500ms | < 2s |
| Temps de réponse (P99) | < 1s | < 3s |
| Disponibilité | > 99.9% | > 99% |
| Erreurs | < 0.1% | < 1% |
| CPU moyen | < 40% | < 70% |
| RAM moyenne | < 60% | < 80% |

### 📈 Dashboards et visualisation

#### Accès rapide

```powershell
# Ouvrir Application Insights dans le portail
az webapp show --name seeg-backend-api --resource-group seeg-backend-rg --query "id" -o tsv | % { 
    Start-Process "https://portal.azure.com/#@/resource$_/appInsights"
}

# Ouvrir les métriques
Start-Process "https://portal.azure.com/#blade/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade/metrics"
```

#### Dashboards recommandés

1. **Dashboard Vue d'ensemble**
   - Requêtes/sec
   - Taux d'erreur
   - Temps de réponse (P50, P95, P99)
   - Disponibilité

2. **Dashboard Performance**
   - CPU et RAM
   - Latence base de données
   - Latence Redis
   - Temps de réponse par endpoint

3. **Dashboard Erreurs**
   - Exceptions par type
   - Erreurs 5xx par endpoint
   - Taux d'échec des dépendances
   - Stack traces des erreurs critiques

### 🔧 Commandes de monitoring

```powershell
# Logs en temps réel
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg

# Télécharger les logs
az webapp log download --name seeg-backend-api --resource-group seeg-backend-rg --log-file logs.zip

# Métriques en temps réel
az monitor metrics list-definitions --resource <resource-id>

# Voir les alertes actives
az monitor metrics alert list --resource-group seeg-backend-rg --output table

# Query Log Analytics
az monitor log-analytics query `
    --workspace <workspace-id> `
    --analytics-query "AppServiceHTTPLogs | where TimeGenerated > ago(1h) | take 100"
```

### 📊 Métriques Prometheus (Custom)

Endpoints exposés pour scraping :

| Endpoint | Description |
|----------|-------------|
| `/monitoring/metrics` | Métriques Prometheus (admin requis) |
| `/monitoring/health` | Health check détaillé |
| `/monitoring/stats` | Statistiques applicatives |

#### Métriques custom disponibles

```python
# Compteurs
- http_requests_total{method, endpoint, status}
- applications_created_total
- documents_uploaded_total
- auth_attempts_total{result}
- cache_hits_total
- cache_misses_total
- errors_total{type}

# Gauges
- active_users_count
- database_connections_active
- redis_connections_active

# Histogrammes
- http_request_duration_seconds{endpoint}
- db_query_duration_seconds{query_type}
```

---

## 🔒 Sécurité

### Authentification

- **JWT** avec signature HS256
- **Access tokens** : 30 minutes
- **Refresh tokens** : 7 jours
- **Bcrypt** pour les mots de passe (cost=12)

### Validation

- **Pydantic** pour toutes les entrées
- **Email** : Format validé
- **Mot de passe** : Minimum 12 caractères (signup), 8 (login)
- **Date de naissance** : Âge minimum 18 ans

### CORS

Configuration par environnement :
- **Dev** : localhost:3000, localhost:8080
- **Prod** : seeg-talentsource.com, seeg-hcm.vercel.app

### Rate Limiting

⚠️ **Temporairement désactivé** (problème compatibilité slowapi)

Configuration cible :
- Auth : 5/minute, 20/heure
- Signup : 3/minute, 10/heure
- Upload : 10/minute, 50/heure
- Autres : 60/minute, 500/heure

---

## 🛡️ Contrôle d'Accès par Rôles (RBAC)

### Hiérarchie des Rôles

```
1. ADMIN (Administrateur)
   └── Toutes les permissions système

2. RECRUITER (Recruteur)
   └── Gestion complète du recrutement

3. OBSERVER (Observateur)
   └── Lecture seule (monitoring)

4. CANDIDATE (Candidat)
   └── Actions limitées à ses propres données
```

### Permissions par Rôle

#### 👤 CANDIDATE (Candidat)

**Autorisé :**
- Voir et modifier son propre profil
- Voir les offres (filtrées selon interne/externe)
- Soumettre des candidatures
- Voir ses propres candidatures
- Upload de documents (CV, lettres, diplômes)

**Interdit :**
- Voir le profil d'autres candidats
- Voir toutes les candidatures
- Créer/modifier des offres d'emploi
- Changer le statut de candidatures

#### 👁️ OBSERVER (Observateur)

**Autorisé (LECTURE SEULE) :**
- Voir toutes les offres d'emploi
- Voir toutes les candidatures
- Voir tous les entretiens
- Voir toutes les évaluations
- Voir les statistiques

**Interdit (AUCUNE ACTION) :**
- Créer/modifier/supprimer quoi que ce soit
- Toute action de modification

#### 💼 RECRUITER (Recruteur)

**Autorisé (TOUT FAIRE) :**
- **Offres** : Créer, modifier, supprimer, publier
- **Candidatures** : Voir toutes, changer statuts
- **Candidats** : Voir tous les profils
- **Entretiens** : Créer, modifier, annuler
- **Évaluations** : Créer, modifier (protocoles MTP)
- **Notifications** : Envoyer aux candidats
- **Statistiques** : Voir et exporter

**Interdit :**
- Modifier les offres d'autres recruteurs (sauf admin)
- Gérer les utilisateurs (admin uniquement)

#### 🔑 ADMIN (Administrateur)

**Autorisé (TOUT) :**
- Toutes les permissions RECRUITER
- Créer/modifier/supprimer des utilisateurs
- Changer les rôles
- Modifier les offres de tous les recruteurs
- Accès aux logs système
- Configuration de l'application

### Dependencies FastAPI

```python
# Tous les utilisateurs authentifiés
Depends(get_current_active_user)

# Candidats uniquement
Depends(get_current_candidate_user)

# Observateurs, Recruteurs et Admin (lecture)
Depends(get_current_observer_user)

# Recruteurs et Admin (actions)
Depends(get_current_recruiter_user)

# Admin uniquement
Depends(get_current_admin_user)
```

### Matrice de Permissions

| Action | Candidate | Observer | Recruiter | Admin |
|--------|-----------|----------|-----------|-------|
| Voir offres (filtrées) | ✅ | ✅ | ✅ | ✅ |
| Créer offre | ❌ | ❌ | ✅ | ✅ |
| Modifier offre | ❌ | ❌ | ✅ (propre) | ✅ (toutes) |
| Candidater | ✅ | ❌ | ❌ | ❌ |
| Voir candidatures | ✅ (propres) | ✅ (toutes) | ✅ (toutes) | ✅ (toutes) |
| Changer statut | ❌ | ❌ | ✅ | ✅ |
| Planifier entretien | ❌ | ❌ | ✅ | ✅ |
| Voir statistiques | ❌ | ✅ | ✅ | ✅ |
| Gérer utilisateurs | ❌ | ❌ | ❌ | ✅ |

---

## 🗄️ Base de données

### Modèle principal

#### Table `users` - Système d'authentification enrichi

**Nouveaux champs ajoutés (version 2.0)** :
- `adresse` : Adresse complète du candidat
- `candidate_status` : Type de candidat ('interne' ou 'externe')
- `statut` : Statut du compte (actif, en_attente, inactif, bloqué, archivé)
- `poste_actuel` : Poste actuel (optionnel)
- `annees_experience` : Années d'expérience (optionnel)
- `no_seeg_email` : Candidat interne sans email @seeg-gabon.com

```sql
CREATE TABLE users (
    -- Identifiant et authentification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    
    -- Informations personnelles
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    phone VARCHAR,
    date_of_birth DATE,  -- Modifié: DATE au lieu de TIMESTAMP
    sexe VARCHAR(1) CHECK (sexe IS NULL OR sexe IN ('M', 'F')),
    adresse TEXT,  -- NOUVEAU
    
    -- Profil professionnel
    matricule INTEGER UNIQUE,  -- NULL pour candidats externes (modifié: nullable)
    poste_actuel TEXT,  -- NOUVEAU
    annees_experience INTEGER,  -- NOUVEAU
    
    -- Type et statut
    role VARCHAR NOT NULL,  -- candidate, recruiter, admin, observer
    candidate_status VARCHAR(10) CHECK (candidate_status IS NULL OR candidate_status IN ('interne', 'externe')),  -- NOUVEAU
    statut VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'en_attente', 'inactif', 'bloqué', 'archivé')),  -- NOUVEAU
    no_seeg_email BOOLEAN NOT NULL DEFAULT false,  -- NOUVEAU
    
    -- Champs legacy
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    is_internal_candidate BOOLEAN DEFAULT false,
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index existants
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_matricule ON users(matricule);
CREATE INDEX ix_users_is_internal_candidate ON users(is_internal_candidate, role);

-- Nouveaux index pour performance
CREATE INDEX idx_users_statut ON users(statut);
CREATE INDEX idx_users_candidate_status ON users(candidate_status);
CREATE INDEX idx_users_matricule_not_null ON users(matricule) WHERE matricule IS NOT NULL;
```

#### Table `access_requests` - Gestion des demandes d'accès (NOUVEAU)

**Table pour gérer les demandes d'accès des candidats internes sans email @seeg-gabon.com**

```sql
CREATE TABLE access_requests (
    -- Identifiant
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Référence utilisateur
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Informations du demandeur (copiées de users pour faciliter l'affichage)
    email VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    phone VARCHAR,
    matricule VARCHAR,
    
    -- Type et statut de la demande
    request_type VARCHAR NOT NULL DEFAULT 'internal_no_seeg_email',
    status VARCHAR NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    
    -- Système de notification (badge)
    viewed BOOLEAN NOT NULL DEFAULT false,
    
    -- Dates et traçabilité
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Index pour performance
CREATE INDEX idx_access_requests_status ON access_requests(status);
CREATE INDEX idx_access_requests_user_id ON access_requests(user_id);
CREATE INDEX idx_access_requests_viewed ON access_requests(viewed);
CREATE INDEX idx_access_requests_status_viewed ON access_requests(status, viewed);
CREATE INDEX idx_access_requests_created_at ON access_requests(created_at DESC);
```

**Workflow** :
1. Candidat interne s'inscrit sans email @seeg-gabon.com
2. `users.statut = 'en_attente'`
3. `access_requests` créée avec `status='pending'`, `viewed=false`
4. Recruteur voit la demande (badge de notification)
5. Recruteur approuve → `users.statut='actif'`, `access_requests.status='approved'`
6. OU Recruteur refuse → `users.statut='bloqué'`, `access_requests.status='rejected'`

#### Table `job_offers`

```sql
CREATE TABLE job_offers (
    id UUID PRIMARY KEY,
    recruiter_id UUID REFERENCES users(id),
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR NOT NULL,
    contract_type VARCHAR NOT NULL,
    is_internal_only BOOLEAN DEFAULT false,  -- NEW: true = Réservée internes uniquement
    status VARCHAR DEFAULT 'active',
    -- ... autres champs ...
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_job_offers_is_internal_only ON job_offers(is_internal_only, status);
```

#### Système INTERNES/EXTERNES

**Sur le candidat** (`is_internal_candidate`) :
- **Avec matricule** → `is_internal_candidate = true` (Employé SEEG)
- **Sans matricule** → `is_internal_candidate = false` (Externe)

**Sur l'offre** (`is_internal_only`) :
- **true** → Réservée aux employés SEEG uniquement
- **false** → Accessible à tous (internes + externes)

**Filtrage automatique** (GET /api/v1/jobs) :
```python
# Dans le service JobOfferService
if current_user.role == "candidate":
    if not current_user.is_internal_candidate:
        # Candidat EXTERNE: uniquement offres non-internes
        query = query.where(JobOffer.is_internal_only == False)
# Candidat INTERNE ou Recruteur: toutes les offres
```

### Migrations

```bash
# Appliquer toutes les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1

# Historique
alembic history

# Migration spécifique
alembic upgrade <revision_id>
```

---

## 📖 Guide des bonnes pratiques

### ✅ À FAIRE

- ✅ Utiliser `Depends(get_db)` pour la session
- ✅ Faire les commits dans les endpoints
- ✅ Laisser les services purs (pas de commit)
- ✅ Gérer les exceptions spécifiques
- ✅ Logger les actions importantes
- ✅ Valider les entrées avec Pydantic
- ✅ Utiliser les types hints partout

### ❌ À NE PAS FAIRE

- ❌ Commits dans les services
- ❌ Rollbacks manuels (get_db() le fait)
- ❌ Ignorer les exceptions
- ❌ Hardcoder des secrets
- ❌ Retourner des mots de passe
- ❌ Exposer les stack traces en production

### Exemple complet

```python
# SERVICE (logique pure)
class MyService:
    async def create_something(self, data) -> Something:
        obj = Something(**data.dict())
        self.db.add(obj)
        # ✅ PAS de commit
        return obj

# ENDPOINT (gestion transaction)
@router.post("/something")
async def create(data: CreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        service = MyService(db)
        obj = await service.create_something(data)
        
        # ✅ Commit explicite
        await db.commit()
        await db.refresh(obj)
        
        return Response.from_orm(obj)
    except ValidationError as e:
        # Rollback automatique par get_db()
        raise HTTPException(400, detail=str(e))
```

---

## 🔧 Scripts utilitaires

### `scripts/deploy-api.ps1`
Déploiement de l'API sur Azure (sans migrations)

### `scripts/run-migrations.ps1`
Exécution des migrations de base de données

### `scripts/create_recruiters_after_migration.py`
Création des utilisateurs initiaux (recruteurs, admin, observateur)

---

## 📝 Changelog

### Version 2.0.0 (2025-10-10)

**🎉 Système d'Authentification Multi-Niveaux**

**Nouvelles fonctionnalités** :
- ✅ **Gestion des demandes d'accès** pour candidats internes sans email @seeg-gabon.com
- ✅ **3 types d'inscription** : Externe, Interne avec email SEEG, Interne sans email SEEG
- ✅ **Système de statuts** : actif, en_attente, inactif, bloqué, archivé
- ✅ **Validation matricule en temps réel** lors de l'inscription
- ✅ **Workflow d'approbation/refus** avec emails automatiques
- ✅ **Badge de notification** pour les demandes non vues
- ✅ **Messages d'erreur personnalisés** selon le statut du compte

**Nouvelles tables** :
- ✅ `access_requests` : Gestion des demandes d'accès avec traçabilité complète

**Nouveaux champs `users`** :
- ✅ `adresse` : Adresse complète
- ✅ `candidate_status` : Type de candidat ('interne' ou 'externe')
- ✅ `statut` : Statut du compte (actif, en_attente, etc.)
- ✅ `poste_actuel` : Poste actuel (optionnel)
- ✅ `annees_experience` : Années d'expérience (optionnel)
- ✅ `no_seeg_email` : Indicateur email non-SEEG
- ✅ `date_of_birth` : Modifié de TIMESTAMP vers DATE
- ✅ `matricule` : Modifié pour être nullable (candidats externes)

**Nouveaux endpoints** :
- ✅ `POST /api/v1/auth/verify-matricule` : Vérification matricule publique
- ✅ `GET /api/v1/access-requests/` : Lister les demandes
- ✅ `POST /api/v1/access-requests/approve` : Approuver une demande
- ✅ `POST /api/v1/access-requests/reject` : Refuser une demande (avec motif ≥ 20 caractères)
- ✅ `POST /api/v1/access-requests/mark-all-viewed` : Marquer comme vues
- ✅ `GET /api/v1/access-requests/unviewed-count` : Badge de notification

**Améliorations** :
- ✅ Validation métier complète dans `AuthService`
- ✅ Création automatique de `AccessRequest` si `statut='en_attente'`
- ✅ Messages d'erreur détaillés selon le statut lors du login
- ✅ Permissions granulaires (recruteur, admin, observateur)
- ✅ Traçabilité complète (reviewed_by, reviewed_at)

**Migrations** :
- ✅ `20251010_add_user_auth_fields.py` : Nouveaux champs users
- ✅ `20251010_create_access_requests.py` : Table access_requests avec index

**Services** :
- ✅ `AccessRequestService` : Gestion complète des demandes d'accès
- ✅ `AuthService` : Enrichi avec `determine_user_status()` et `verify_matricule_exists()`

**Schémas** :
- ✅ `CandidateSignupRequest` : Enrichi avec tous les nouveaux champs
- ✅ `AccessRequestCreate`, `AccessRequestUpdate`, `AccessRequestApprove`, `AccessRequestReject`
- ✅ `AccessRequestListResponse` avec `pending_count` et `unviewed_count`

**🔧 Corrections** :
- ✅ Toutes les erreurs de typage Pyright corrigées
- ✅ Encodage UTF-8 vérifié sur tous les fichiers
- ✅ Respect des meilleures pratiques du Génie Logiciel

---

### Version 1.0.0 (2025-10-08)

**🎉 Features**
- ✅ Système d'authentification complet
- ✅ Distinction candidats INTERNES/EXTERNES
- ✅ Upload de documents PDF
- ✅ Évaluations MTP
- ✅ Monitoring complet (Prometheus, Jaeger, App Insights)

**🏗️ Architecture**
- ✅ Refactorisation complète avec best practices
- ✅ SOLID principles appliqués
- ✅ Unit of Work Pattern implémenté
- ✅ 8 services refactorisés (46 commits retirés)
- ✅ Transactions explicites dans tous les endpoints

**🔧 Fixes**
- ✅ Gestion robuste des sessions DB
- ✅ Architecture propre avec séparation des couches
- ✅ Rollback automatique en cas d'erreur
- ✅ Logging structuré partout

---

## 🤝 Contribution

### Workflow Git

```bash
# 1. Créer une branche
git checkout -b feature/ma-fonctionnalite

# 2. Faire vos modifications

# 3. Tests
pytest

# 4. Commit
git add .
git commit -m "feat: description"

# 5. Push
git push origin feature/ma-fonctionnalite

# 6. Créer une Pull Request
```

### Standards de code

- **PEP 8** pour Python
- **Type hints** obligatoires
- **Docstrings** pour toutes les fonctions publiques
- **Tests** pour les nouvelles fonctionnalités

---

## 📞 Support

### Problèmes courants

#### 1. Erreur de connexion DB

```bash
# Vérifier que PostgreSQL est démarré
psql -U postgres -c "SELECT 1"

# Vérifier la base existe
psql -U postgres -l | grep recruteur
```

#### 2. Erreur 401 Unauthorized

- Vérifier que le token n'est pas expiré
- Vérifier le format : `Authorization: Bearer <token>`

#### 3. Erreur CORS

- Vérifier `ALLOWED_ORIGINS` dans .env
- Vérifier que le frontend utilise le bon domaine

#### 4. Import errors

- Vérifier que l'environnement virtuel est activé
- Vérifier `pip install -r requirements.txt`

### Logs & Debugging

```bash
# Activer le mode DEBUG
DEBUG=true

# Niveau de logs détaillé
LOG_LEVEL=DEBUG

# Voir les requêtes SQL
echo=True  # Dans database.py
```

---

## 📄 Licence

Propriété de CNX 4.0

---

## 👨‍💻 Développeurs

**Lead Developer** : Sevan Kedesh IKISSA PENDY  
**Email** : sevankedesh11@gmail.com

---

## 🚀 Statut

**Version actuelle** : 1.0.0  
**Environnement** : Production Ready ✅  
**Tests** : 8/8 endpoints auth (100%) ✅  
**Architecture** : Clean Code ✅  
**Déploiement** : Azure + Docker ✅

---

**Construit avec ❤️ pour la SEEG**

# Rechercher le serveur PostgreSQL (Single Server)
az postgres server list --resource-group seeg-rg --output table

# Ajouter votre IP au firewall
az postgres server firewall-rule create \
  --resource-group seeg-rg \
  --server-name seeg-postgres-server \
  --name "Allow-Local-IP" \
  --start-ip-address 154.116.31.161 \
  --end-ip-address 154.116.31.161