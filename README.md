# 🏢 One HCM SEEG Backend API

> **API de gestion des ressources humaines pour la SEEG**  
> *Société d'Énergie et d'Eau du Gabon*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-00C7B7?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Azure](https://img.shields.io/badge/Azure-Deployed-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

## 🔗 Liens Rapides

| Service | URL | Status |
|---------|-----|--------|
| **API Production** | [seeg-backend-api.azurewebsites.net](https://seeg-backend-api.azurewebsites.net) | 🟢 |
| **Documentation** | [/docs](https://seeg-backend-api.azurewebsites.net/docs) | 📖 |
| **Frontend Production** | [seeg-talentsource.com](https://www.seeg-talentsource.com) | 🌐 |
| **Frontend Staging** | [seeg-hcm.vercel.app](https://seeg-hcm.vercel.app) | 🧪 |

---

## 📑 Table des Matières

1. [🎯 Aperçu](#-aperçu)
2. [🚀 Démarrage Rapide](#-démarrage-rapide)
3. [⚙️ Configuration](#%EF%B8%8F-configuration)
4. [🗄️ Base de Données & Migrations](#%EF%B8%8F-base-de-données--migrations)
5. [🏗️ Architecture](#%EF%B8%8F-architecture)
6. [🔐 Authentification & Autorisation](#-authentification--autorisation)
7. [📚 API Endpoints](#-api-endpoints)
8. [💡 Exemples d'Utilisation](#-exemples-dutilisation)
9. [🐳 Déploiement](#-déploiement)
10. [🧪 Tests](#-tests)
11. [📊 Monitoring](#-monitoring)
12. [🔧 Troubleshooting](#-troubleshooting)
13. [📝 Changelog](#-changelog)

---

## 🎯 Aperçu

**One HCM SEEG Backend** est une API RESTful complète pour gérer l'ensemble du processus de recrutement de la SEEG :

- 🔐 **Authentification** avec JWT et refresh tokens + retour des informations utilisateur
- 👥 **Gestion des utilisateurs** (candidats internes/externes, recruteurs, admins, observateurs)
- 💼 **Offres d'emploi** avec filtrage interne/externe
- ❓ **Questions MTP** flexibles au format JSON auto-incrémenté (métier, talent, paradigme)
- 📝 **Candidatures** avec tracking complet et réponses MTP
- 📄 **Documents PDF** (CV, lettres, diplômes)
- 📊 **Évaluations** (protocoles MTP)
- 📅 **Entretiens** avec planification
- 🔔 **Notifications** en temps réel

---

## 🚀 Démarrage Rapide

### Pour les Développeurs

```bash
# 1. Cloner et installer
git clone <repo>
cd SEEG-API
python -m venv env
.\env\Scripts\Activate.ps1  # Windows PowerShell
# source env/bin/activate    # Linux/Mac
pip install -r requirements.txt

# 2. Configurer
copy env.example .env.local
# Éditer .env.local avec vos paramètres locaux

# 3. Migrations
alembic upgrade head

# 4. Lancer
uvicorn app.main:app --reload
```

➡️ API disponible sur `http://localhost:8000/docs`

### Pour le Déploiement Azure

```powershell
# Déploiement complet automatisé
.\scripts\deploy-api-v2.ps1

# Application des migrations
.\scripts\run-migrations.ps1
```

➡️ API disponible sur `https://seeg-backend-api.azurewebsites.net`

---

## ⚙️ Configuration

### 🎯 Architecture de Configuration (12-Factor App)

Cette application suit les principes des [12-Factor Apps](https://12factor.net/config) pour la gestion de la configuration.

#### Hiérarchie de Priorité

**Du plus au moins prioritaire :**

1. **🥇 Variables d'environnement système** (priorité maximale)
   ```bash
   # PowerShell
   $env:DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
   python main.py
   
   # Bash/Linux
   export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
   python main.py
   ```

2. **🥈 Fichiers `.env.{environment}`** (spécifiques à l'environnement)
   - `.env.production` → En production (Azure, etc.)
   - `.env.local` → En développement local

3. **🥉 Fichier `.env`** (valeurs communes)
   - Contient les valeurs par défaut pour tous les environnements

4. **Valeurs par défaut** (dans le code)
   - Utilisées seulement si aucune autre source n'est définie

#### Structure des Fichiers de Configuration

```
SEEG-API/
├── .env                  # ✅ Commitable - Valeurs par défaut (pas de secrets)
├── .env.example          # ✅ Commitable - Template pour documentation
├── .env.production       # ❌ NE PAS commiter - Configuration production
├── .env.local            # ❌ NE PAS commiter - Configuration développement local
└── .gitignore            # Ignore .env.production et .env.local
```

### 📝 Fichiers de Configuration

#### `.env.local` (Développement)

```bash
# Environnement
ENVIRONMENT=development
DEBUG=true

# Base de données locale
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/recruteur
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/recruteur

# Sécurité (générer avec: python -c "import secrets; print(secrets.token_urlsafe(48))")
SECRET_KEY=<minimum-32-caracteres-aleatoires>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (développement)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ALLOWED_CREDENTIALS=true

# Email (optionnel en dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<votre-email>
SMTP_PASSWORD=<app-password>
```

#### `.env` ou `.env.production` (Production)

```bash
# Environnement
ENVIRONMENT=production
DEBUG=false

# Base de données Azure PostgreSQL
DATABASE_URL=postgresql+asyncpg://Sevan:password@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://Sevan:password@seeg-postgres-server.postgres.database.azure.com:5432/postgres

# Sécurité (clé forte requise!)
SECRET_KEY=<generer-cle-securisee-48-caracteres>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (production - domaines spécifiques)
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
ALLOWED_CREDENTIALS=true

# Monitoring Azure
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
ENABLE_TRACING=true
METRICS_ENABLED=true

# Migrations (ne pas exécuter au démarrage en prod)
SKIP_MIGRATIONS=true
```

### 🔐 Gestion des Secrets

#### ❌ NE JAMAIS Commiter

- `.env.local`
- `.env.production`
- Tout fichier contenant des mots de passe, clés API, tokens

#### ✅ Commiter

- `.env` (seulement si aucun secret)
- `.env.example` (template avec valeurs factices)
- `README.md` (cette documentation)

#### 🔒 Générer des Secrets Forts

```bash
# Générer une SECRET_KEY forte (48 caractères recommandés)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Exemple de sortie:
# GVxt590ktWvcTL6BLttyq7CVxhhGcZ18EA34vnDZczLDIf6Gh2uHpQOahkn2LXF8
```

---

## 🗄️ Base de Données & Migrations

### Modèles Principaux

#### Table `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    phone VARCHAR,
    date_of_birth DATE,
    sexe VARCHAR(1) CHECK (sexe IN ('M', 'F')),
    adresse TEXT,
    matricule INTEGER UNIQUE,
    poste_actuel TEXT,
    annees_experience INTEGER,
    role VARCHAR NOT NULL,
    candidate_status VARCHAR(10) CHECK (candidate_status IN ('interne', 'externe')),
    statut VARCHAR(20) DEFAULT 'actif',
    no_seeg_email BOOLEAN DEFAULT false,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Table `job_offers`

```sql
CREATE TABLE job_offers (
    id UUID PRIMARY KEY,
    recruiter_id UUID REFERENCES users(id),
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR NOT NULL,
    contract_type VARCHAR NOT NULL,
    is_internal_only BOOLEAN DEFAULT false,
    status VARCHAR DEFAULT 'active',
    questions_mtp JSONB,  -- Format: {"questions_metier": [...], "questions_talent": [...], "questions_paradigme": [...]}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Table `applications`

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY,
    candidate_id UUID REFERENCES users(id),
    job_offer_id UUID REFERENCES job_offers(id),
    status VARCHAR DEFAULT 'pending',
    mtp_answers JSONB,  -- Format: {"reponses_metier": [...], "reponses_talent": [...], "reponses_paradigme": [...]}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 🔄 Migrations Alembic

#### Commandes de Base

```bash
# Voir l'état actuel de la base
alembic current

# Voir l'historique des migrations
alembic history --verbose

# Voir les migrations en attente
alembic heads

# Appliquer toutes les migrations
alembic upgrade head

# Appliquer une migration spécifique
alembic upgrade <revision_id>

# Revenir en arrière (1 migration)
alembic downgrade -1

# Créer une nouvelle migration
alembic revision --autogenerate -m "description"

# Générer le SQL sans l'exécuter
alembic upgrade head --sql
```

#### Migrations vers Différents Environnements

##### 1️⃣ Migrations Locales (développement)

```bash
# Activer l'environnement virtuel
.\env\Scripts\Activate.ps1  # Windows
source env/bin/activate      # Linux/Mac

# Appliquer les migrations
alembic upgrade head
```

##### 2️⃣ Migrations Azure (production) - Via Variables d'Environnement

**Option A : Variable temporaire (recommandé)**

```bash
# PowerShell
$env:DATABASE_URL="postgresql+asyncpg://Sevan:password@seeg-postgres-server.postgres.database.azure.com:5432/postgres"
alembic upgrade head

# Bash/Linux
export DATABASE_URL="postgresql+asyncpg://Sevan:password@seeg-postgres-server.postgres.database.azure.com:5432/postgres"
alembic upgrade head
```

**Option B : Script PowerShell automatisé**

```powershell
# Utilise le script qui gère automatiquement la connexion et le firewall
.\scripts\run-migrations.ps1 -Action upgrade -Target head

# Voir l'état
.\scripts\run-migrations.ps1 -Action current

# Voir l'historique
.\scripts\run-migrations.ps1 -Action history
```

##### 3️⃣ Migrations Azure - Avec Forçage d'Environnement

```bash
# Forcer l'environnement de production
$env:ENVIRONMENT="production"
$env:DATABASE_URL="postgresql+asyncpg://..."
alembic upgrade head
```

#### ⚠️ Important : Hiérarchie de Configuration

Les **variables d'environnement système ont TOUJOURS priorité** sur les fichiers `.env.*`

```bash
# Exemple : même si .env.local définit DATABASE_URL pour localhost,
# cette commande se connectera à Azure
$env:DATABASE_URL="postgresql+asyncpg://...azure..."
alembic upgrade head
```

#### 🔧 Résoudre les Problèmes de Migration

##### Problème : Têtes de Migration Multiples

```bash
# Identifier les têtes
alembic heads

# Créer une migration de fusion
alembic merge -m "merge_multiple_heads" heads

# Appliquer la fusion
alembic upgrade head
```

##### Problème : Révision Manquante

```bash
# Marquer manuellement la base à une révision spécifique (sans exécuter le SQL)
alembic stamp <revision_id>

# Puis appliquer les migrations suivantes
alembic upgrade head
```

##### Problème : Nettoyage de la Table alembic_version

Si la table `alembic_version` est corrompue :

```sql
-- Sur Azure Data Studio ou psql
DELETE FROM alembic_version;

-- Puis marquer la base à la révision actuelle
-- alembic stamp head  (ou autre révision appropriée)
```

#### 📋 Bonnes Pratiques de Migration

1. **Toujours tester localement d'abord**
   ```bash
   # Tester sur base locale
   alembic upgrade head
   
   # Vérifier que tout fonctionne
   alembic current
   ```

2. **Générer le SQL avant d'exécuter sur production**
   ```bash
   alembic upgrade head --sql > migration.sql
   # Examiner migration.sql avant de l'appliquer
   ```

3. **Sauvegarder la base avant migration importante**
   ```bash
   # Via Azure CLI
   az postgres flexible-server backup create \
     --resource-group seeg-rg \
     --name seeg-postgres-server
   ```

4. **Nommer les migrations de manière descriptive**
   ```bash
   # ✅ Bon
   alembic revision --autogenerate -m "add_questions_mtp_to_job_offers"
   
   # ❌ Mauvais
   alembic revision --autogenerate -m "update"
   ```

5. **Garder les IDs de révision courts (≤32 caractères)**
   ```python
   # Dans le fichier de migration
   revision = '20251017_add_field'  # ✅ 21 caractères
   # pas: '20251017_add_field_to_applications_table'  # ❌ 43 caractères
   ```

---

## 🏗️ Architecture

### Stack Technique

**Backend**
- FastAPI 0.109+ (async/await)
- SQLAlchemy 2.0+ (ORM avec Mapped types)
- PostgreSQL 16 (base de données)
- Alembic (migrations)
- Pydantic 2.5+ (validation)

**Sécurité**
- JWT (python-jose)
- Bcrypt (hashing passwords)
- CORS configuré
- Rate limiting (slowapi)

**Monitoring**
- Structlog (logging JSON)
- Application Insights (Azure)

### Structure du Projet

```
SEEG-API/
├── app/
│   ├── api/v1/endpoints/      # Endpoints FastAPI
│   ├── core/
│   │   ├── config/            # Configuration (12-Factor App)
│   │   ├── security/          # JWT, hashing
│   │   └── dependencies.py    # Dépendances injectables
│   ├── db/
│   │   ├── migrations/        # Migrations Alembic
│   │   ├── database.py        # Engine & Session
│   │   └── session.py         # Session factory
│   ├── models/                # Models SQLAlchemy 2.0
│   ├── schemas/               # Schemas Pydantic
│   ├── services/              # Business logic
│   └── main.py                # Point d'entrée
├── scripts/
│   ├── deploy-api-v2.ps1      # Déploiement complet Azure
│   ├── run-migrations.ps1     # Migrations avec gestion firewall
│   └── migrate_database_azure.py  # Migration SQL directe
├── tests/
│   ├── fixtures/              # Fixtures pytest
│   └── test_*.py              # Tests unitaires & intégration
├── .env.example               # Template de configuration
├── alembic.ini                # Config migrations
├── docker-compose.yml         # Stack complète (dev)
├── Dockerfile                 # Multi-stage build
├── requirements.txt           # 51 dépendances
└── README.md                  # Cette documentation
```

### Principes Architecturaux

- **Clean Code** : Séparation des responsabilités
- **SOLID** : Dépendances inversées
- **12-Factor App** : Configuration externalisée
- **Async First** : Performances optimales
- **Type Safety** : Types stricts partout (Pydantic + SQLAlchemy Mapped)

---

## 🔐 Authentification & Autorisation

### Système d'Authentification Multi-Niveaux

#### Types de Candidats

**1. Candidats EXTERNES** : Accès immédiat
- `candidate_status = 'externe'`
- Aucun matricule requis
- `statut = 'actif'` dès l'inscription

**2. Candidats INTERNES avec email @seeg-gabon.com** : Accès immédiat
- `candidate_status = 'interne'`
- Matricule SEEG obligatoire et vérifié
- Email professionnel requis
- `statut = 'actif'` dès l'inscription

**3. Candidats INTERNES sans email @seeg-gabon.com** : Validation requise
- `candidate_status = 'interne'`
- Matricule SEEG obligatoire et vérifié
- Email personnel (gmail, yahoo, etc.)
- `statut = 'en_attente'` → demande d'accès créée
- Validation par un recruteur nécessaire

### Rôles Utilisateur

| Rôle | Description | Permissions |
|------|-------------|-------------|
| **admin** | Administrateur système | Toutes les permissions |
| **recruiter** | Recruteur RH | Gestion complète du recrutement |
| **observer** | Observateur | Lecture seule (monitoring) |
| **candidate** | Candidat | Actions sur ses propres données |

---

## 📚 API Endpoints

### 🔐 Authentification (`/api/v1/auth`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/login` | Connexion (retourne tokens + infos utilisateur) |
| POST | `/signup` | Inscription candidat |
| POST | `/verify-matricule` | Vérifier un matricule SEEG |
| POST | `/create-user` | Créer utilisateur (admin) |
| GET | `/me` | Profil utilisateur connecté |
| POST | `/refresh` | Rafraîchir le token |
| POST | `/logout` | Déconnexion |
| POST | `/forgot-password` | Réinitialisation MdP |
| POST | `/reset-password` | Confirmer réinitialisation |
| POST | `/change-password` | Changer mot de passe |

### 👥 Demandes d'Accès (`/api/v1/access-requests`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Lister toutes les demandes |
| POST | `/approve` | Approuver une demande |
| POST | `/reject` | Refuser une demande |
| POST | `/mark-all-viewed` | Marquer comme vues |
| GET | `/unviewed-count` | Nombre de demandes non vues |

### 💼 Offres d'Emploi (`/api/v1/jobs`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Liste des offres (filtrées automatiquement) |
| POST | `/` | Créer offre avec questions MTP |
| GET | `/{id}` | Détails offre |
| PUT | `/{id}` | Modifier offre |
| DELETE | `/{id}` | Supprimer offre |

### 📝 Candidatures (`/api/v1/applications`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/` | Soumettre candidature avec réponses MTP |
| GET | `/` | Lister candidatures |
| GET | `/{id}` | Détails candidature |
| PUT | `/{id}/status` | Changer statut |
| POST | `/{id}/documents` | Upload PDF |

---

## 💡 Exemples d'Utilisation

### 1. Connexion avec Retour des Infos Utilisateur

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@seeg.ga",
  "password": "AdminSecure123!"
}

# Réponse:
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "admin@seeg.ga",
    "first_name": "Admin",
    "last_name": "SEEG",
    "role": "admin",
    "statut": "actif",
    ...
  }
}
```

### 2. Créer une Offre avec Questions MTP Flexibles

```bash
POST /api/v1/jobs/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Ingénieur Logiciel Senior",
  "description": "Poste stratégique pour la SEEG",
  "location": "Libreville, Gabon",
  "contract_type": "CDI",
  "status": "active",
  "is_internal_only": false,
  "questions_mtp": {
    "questions_metier": [
      "Décrivez votre expérience en Python et FastAPI",
      "Quels frameworks backend maîtrisez-vous?",
      "Parlez-nous de vos projets d'API REST"
    ],
    "questions_talent": [
      "Comment gérez-vous le travail en équipe?",
      "Quelle est votre plus grande force professionnelle?"
    ],
    "questions_paradigme": [
      "Quelle est votre vision du développement durable en entreprise?"
    ]
  }
}
```

### 3. Soumettre une Candidature avec Réponses MTP

```bash
POST /api/v1/applications/
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_offer_id": "uuid-de-l-offre",
  "mtp_answers": {
    "reponses_metier": [
      "J'ai 5 ans d'expérience avec Python et FastAPI...",
      "Je maîtrise Django, Flask, FastAPI...",
      "J'ai développé plusieurs API REST pour..."
    ],
    "reponses_talent": [
      "Je privilégie la communication ouverte...",
      "Ma plus grande force est la résolution de problèmes..."
    ],
    "reponses_paradigme": [
      "Je pense que le développement durable..."
    ]
  }
}
```

---

## 🐳 Déploiement

### Azure App Service (Production)

#### Prérequis

- Azure CLI installé (`az --version`)
- Connexion Azure active (`az login`)
- Container Registry configuré
- PostgreSQL configuré
- Firewall Azure configuré pour votre IP

#### Configuration des Variables d'Environnement

Variables définies dans **Azure App Service > Configuration > Application Settings** :

```bash
# Environnement
ENVIRONMENT=production
DEBUG=false

# Sécurité
SECRET_KEY=<generer-cle-securisee-48-caracteres>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Base de données
DATABASE_URL=postgresql+asyncpg://user:pass@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://user:pass@seeg-postgres-server.postgres.database.azure.com:5432/postgres

# CORS (domaines spécifiques uniquement)
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
ALLOWED_CREDENTIALS=true

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
ENABLE_TRACING=true
METRICS_ENABLED=true

# Migrations (ne pas exécuter au démarrage)
SKIP_MIGRATIONS=true
```

#### Workflow de Déploiement

**1. Déployer l'Application**

```powershell
# Déploiement complet (build + config + deploy)
.\scripts\deploy-api-v2.ps1

# Ou avec build local si Docker disponible
.\scripts\deploy-api-v2.ps1 -BuildMode local
```

**Ce que fait ce script :**
- ✅ Vérifie les prérequis (Azure CLI, Docker)
- ✅ Construit l'image Docker (cloud ou local)
- ✅ Push vers Azure Container Registry
- ✅ Configure l'App Service
- ✅ Redémarre l'application
- ✅ Effectue un health check
- ✅ Génère un rapport détaillé

**2. Appliquer les Migrations**

```powershell
# Méthode A : Script automatisé (recommandé)
.\scripts\run-migrations.ps1 -Action upgrade -Target head

# Méthode B : Manuellement avec variables d'environnement
$env:DATABASE_URL="postgresql+asyncpg://..."
alembic upgrade head

# Voir l'état actuel
.\scripts\run-migrations.ps1 -Action current

# Voir l'historique
.\scripts\run-migrations.ps1 -Action history

# Rollback (si nécessaire)
.\scripts\run-migrations.ps1 -Action downgrade -Target "-1"
```

**Ce que fait le script run-migrations.ps1 :**
- ✅ Récupère la chaîne de connexion depuis Azure
- ✅ Ajoute automatiquement votre IP au firewall PostgreSQL
- ✅ Affiche l'état des migrations
- ✅ Exécute les migrations
- ✅ Propose de nettoyer la règle de firewall

**3. Vérifier le Déploiement**

```bash
# Health check
curl https://seeg-backend-api.azurewebsites.net/health

# Documentation interactive
https://seeg-backend-api.azurewebsites.net/docs

# Logs en temps réel
az webapp log tail --name seeg-backend-api --resource-group seeg-rg
```

### Docker Compose (Développement Local)

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f seeg-api

# Arrêter
docker-compose down

# Reconstruire
docker-compose up -d --build
```

---

## 🧪 Tests

```bash
# Activer l'environnement virtuel
.\env\Scripts\Activate.ps1

# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html
# Rapport dans htmlcov/index.html

# Tests spécifiques
pytest tests/test_auth_complete.py -v

# Tests avec logs
pytest -s -v

# Tests par catégorie
pytest tests/test_applications_complete.py
pytest tests/test_job_offers_complete.py
pytest tests/test_notifications_complete.py
```

---

## 📊 Monitoring

### Application Insights (Azure)

- **Distributed Tracing** : Traçage end-to-end
- **Dependency Tracking** : Suivi PostgreSQL, Redis
- **Exception Tracking** : Capture automatique
- **Performance Metrics** : CPU, RAM, latence
- **Live Metrics** : Métriques temps réel

Accès : Portail Azure → Application Insights → `seeg-api-insights`

### Logs

```powershell
# Logs en temps réel
az webapp log tail --name seeg-backend-api --resource-group seeg-rg

# Télécharger les logs
az webapp log download --name seeg-backend-api --resource-group seeg-rg --log-file logs.zip

# Activer les logs de conteneur
az webapp log config --name seeg-backend-api --resource-group seeg-rg --docker-container-logging filesystem
```

---

## 🔧 Troubleshooting

### Problèmes de Configuration

#### ❌ Problème : `.env.local` écrase mes variables système

**✅ Solution :** Les variables d'environnement système ont maintenant priorité automatiquement.

```bash
# Tester la priorité
$env:DATABASE_URL="ma-valeur-test"
python -c "from app.core.config.config import settings; print(settings.DATABASE_URL)"
# Doit afficher "ma-valeur-test"
```

#### ❌ Problème : Configuration ne se charge pas

**✅ Vérifications :**

1. Le fichier `.env` existe-t-il ?
   ```bash
   ls -la .env*
   ```

2. Les variables sont-elles bien formatées ?
   ```bash
   # ✅ Correct
   DATABASE_URL=postgresql://...
   
   # ❌ Incorrect (espaces, guillemets inutiles)
   DATABASE_URL = "postgresql://..."
   ```

3. Vérifier les logs de démarrage
   ```
   [INFO] Detection: Developpement LOCAL
   [INFO] Chargement: .env + .env.local
   [INFO] Configuration chargee: development
   [INFO] Variables système ont priorite sur fichiers .env
   ```

### Problèmes de Migration

#### ❌ Problème : Alembic utilise la mauvaise base de données

**✅ Solution :** Définir explicitement `DATABASE_URL` avant Alembic

```bash
# PowerShell
$env:DATABASE_URL="postgresql+asyncpg://..."
alembic upgrade head

# Bash/Linux
export DATABASE_URL="postgresql+asyncpg://..."
alembic upgrade head
```

#### ❌ Problème : "Multiple head revisions are present"

**✅ Solution :** Créer une migration de fusion

```bash
# Voir les têtes
alembic heads

# Créer une fusion
alembic merge -m "merge_multiple_heads" heads

# Appliquer
alembic upgrade head
```

#### ❌ Problème : "Can't locate revision identified by 'xxx'"

**✅ Solution :** Révision manquante ou corrompue

```bash
# Option 1: Nettoyer la table alembic_version (via psql ou Azure Data Studio)
DELETE FROM alembic_version;

# Option 2: Marquer manuellement la base à une révision connue
alembic stamp <revision_id>

# Puis réappliquer
alembic upgrade head
```

#### ❌ Problème : "value too long for type character varying(32)"

**✅ Solution :** ID de révision trop long

```bash
# Soit agrandir la colonne (via SQL):
ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255);

# Soit raccourcir les IDs de révision dans les fichiers de migration
# (max 32 caractères recommandés)
```

### Problèmes de Connexion

#### ❌ Problème : Erreur de connexion DB "timeout expired"

**✅ Solutions :**

1. Vérifier le firewall Azure
   ```bash
   # Ajouter votre IP
   az postgres flexible-server firewall-rule create \
     --resource-group seeg-rg \
     --name seeg-postgres-server \
     --rule-name allow-my-ip \
     --start-ip-address <votre-ip> \
     --end-ip-address <votre-ip>
   ```

2. Vérifier les credentials
   ```bash
   # Tester la connexion
   psql "host=seeg-postgres-server.postgres.database.azure.com port=5432 dbname=postgres user=Sevan sslmode=require"
   ```

#### ❌ Problème : Erreur 401 Unauthorized

**✅ Vérifications :**

- Le token n'est pas expiré (30 min par défaut)
- Format header : `Authorization: Bearer <token>`
- Le token est valide (pas modifié)

```bash
# Tester avec curl
curl -H "Authorization: Bearer <token>" https://seeg-backend-api.azurewebsites.net/api/v1/auth/me
```

#### ❌ Problème : Erreur CORS

**✅ Solution :** Vérifier `ALLOWED_ORIGINS`

```bash
# En développement
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# En production (domaines spécifiques uniquement)
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
```

### Debugging

```bash
# Activer le mode DEBUG
# Dans .env.local
DEBUG=true
LOG_LEVEL=DEBUG

# Puis relancer
uvicorn app.main:app --reload

# Logs détaillés dans la console
```

---

## 📝 Changelog

### Version 2.2.0 (2025-10-17) 🆕

**🎯 Configuration Robuste (12-Factor App) :**
- ✅ **Hiérarchie de priorité** : Variables système > .env.{environment} > .env > défauts
- ✅ **Résolution du conflit** `.env.local` vs variables système
- ✅ **Documentation complète** de la configuration dans README
- ✅ **Migrations vers Azure** facilitées avec variables d'environnement

**🔧 Corrections de Migrations :**
- ✅ IDs de révision raccourcis à ≤32 caractères
- ✅ Fusion des têtes multiples de migration
- ✅ Correction des références de révisions (`20251010_add_mtp_questions`)
- ✅ Table `alembic_version` nettoyée et synchronisée

**📚 Documentation :**
- ✅ README consolidé avec toutes les sections
- ✅ Guide complet des migrations Alembic
- ✅ Troubleshooting exhaustif
- ✅ Exemples de commandes pour tous les environnements

### Version 2.1.0 (2025-10-13)

**🎉 Nouvelles Fonctionnalités :**
- ✅ **Questions MTP flexibles** au format JSON (max 7 métier, 3 talent, 3 paradigme)
- ✅ **Login enrichi** avec toutes les infos utilisateur (sans mot de passe)
- ✅ **ID créateur automatique** lors de la création d'offres
- ✅ **Champs optionnels** pour admin/recruteur/observateur

**🔧 Corrections :**
- ✅ Commits manquants ajoutés dans les endpoints d'offres
- ✅ Gestion d'erreur améliorée avec logs détaillés
- ✅ Toutes les erreurs de linter corrigées

**📊 Migrations :**
- ✅ `20251013_add_mtp_questions_to_job_offers` : Colonne `questions_mtp` (JSONB)
- ✅ 9 colonnes MTP supprimées de `applications`

### Version 2.0.0 (2025-10-10)

**🎉 Système d'Authentification Multi-Niveaux :**
- ✅ Gestion des demandes d'accès pour candidats internes
- ✅ 3 types d'inscription (externe, interne avec/sans email SEEG)
- ✅ Système de statuts (actif, en_attente, bloqué, etc.)
- ✅ Workflow d'approbation/refus avec emails
- ✅ Badge de notification pour les demandes non vues

### Version 1.0.0 (2025-10-08)

**🎉 Version Initiale :**
- ✅ Système d'authentification complet
- ✅ Distinction candidats internes/externes
- ✅ Upload de documents PDF
- ✅ Évaluations MTP
- ✅ Monitoring complet

---

## ✅ Checklist Avant Production

- [ ] `SECRET_KEY` forte et unique (48+ caractères)
- [ ] `DEBUG=false` en production
- [ ] Base de données Azure PostgreSQL configurée
- [ ] Variables définies dans Azure App Service Settings
- [ ] `.env.production` et `.env.local` dans `.gitignore`
- [ ] Secrets stockés dans Azure Key Vault (recommandé)
- [ ] CORS configuré avec origines spécifiques (pas "*")
- [ ] HTTPS activé et certificat valide
- [ ] Monitoring (Application Insights) configuré
- [ ] Migrations testées localement avant production
- [ ] Backup de base de données configuré
- [ ] Health check endpoint fonctionnel
- [ ] Logs centralisés et accessibles

---

## 📞 Support & Contact

### Développeur Principal

**Lead Developer** : Sevan Kedesh IKISSA PENDY  
**Email** : sevankedesh11@gmail.com  
**Organisation** : CNX 4.0

### Ressources Utiles

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [12-Factor App](https://12factor.net/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/)

---

## 🚀 Statut du Projet

**Version Actuelle** : 2.2.0  
**Environnement** : Production ✅  
**Architecture** : Clean Code + 12-Factor App ✅  
**Déploiement** : Azure + Docker ✅  
**Migrations** : Alembic ✅  
**Monitoring** : Application Insights ✅

---

**Construit avec ❤️ pour la SEEG**

*Société d'Énergie et d'Eau du Gabon*
