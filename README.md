# 🏢 One HCM SEEG Backend API

> **API de gestion des ressources humaines pour la SEEG**  
> *Société d'Énergie et d'Eau du Gabon*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-00C7B7?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Azure](https://img.shields.io/badge/Azure-Deployed-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

### 🔗 Liens rapides

| Service | URL | Status |
|---------|-----|--------|
| **API Production** | [seeg-backend-api.azurewebsites.net](https://seeg-backend-api.azurewebsites.net) | 🟢 |
| **Documentation** | [/docs](https://seeg-backend-api.azurewebsites.net/docs) | 📖 |
| **Frontend Production** | [seeg-talentsource.com](https://www.seeg-talentsource.com) | 🌐 |
| **Frontend Staging** | [seeg-hcm.vercel.app](https://seeg-hcm.vercel.app) | 🧪 |

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

## 🚀 Démarrage rapide

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

### Pour le déploiement Azure

```powershell
# Déploiement complet automatisé
.\scripts\deploy-api-v2.ps1

# Application des migrations
.\scripts\run-migrations.ps1
```

➡️ API disponible sur `https://seeg-backend-api.azurewebsites.net`

---

## ✨ Nouveautés - Version 2.1.0 (2025-10-13)

### 🎯 **1. Système de Questions MTP Flexible** 🔥

Remplacement du système rigide de colonnes individuelles par un format JSON dynamique :

**Avant** (colonnes fixes) :
```python
question_metier: str   # 1 seule question
question_talent: str   # 1 seule question  
question_paradigme: str  # 1 seule question
```

**Maintenant** (JSON flexible) :
```json
{
  "questions_mtp": {
    "questions_metier": [
      "Question métier 1",
      "Question métier 2",
      "Question métier 3"
    ],
    "questions_talent": [
      "Question talent 1",
      "Question talent 2"
    ],
    "questions_paradigme": [
      "Question paradigme 1"
    ]
  }
}
```

**Avantages** :
- ✅ Nombre flexible de questions (max 7 métier, 3 talent, 3 paradigme)
- ✅ Format JSON natif dans PostgreSQL (JSONB)
- ✅ Validation automatique via Pydantic
- ✅ Facilité d'ajout/suppression de questions
- ✅ Meilleure performance (1 colonne au lieu de 13)

**Changements dans les modèles** :

**JobOffer** :
- ✅ Colonne `questions_mtp` (JSONB) ajoutée

**Application** :
- ✅ Colonne `mtp_answers` (JSONB) modifiée pour le même format
- ✅ 9 colonnes supprimées : `mtp_metier_q1-3`, `mtp_talent_q1-3`, `mtp_paradigme_q1-3`

### 🔐 **2. Authentification Enrichie** 🔥

Le login retourne maintenant **toutes les informations utilisateur** (sauf le mot de passe) :

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "role": "candidate",
    "phone": "+24106223344",
    "date_of_birth": "1990-05-15",
    "sexe": "M",
    "matricule": 123456,
    "email_verified": false,
    "last_login": "2025-10-13T12:08:45+00:00",
    "is_active": true,
    "is_internal_candidate": true,
    "adresse": "123 Rue de la Liberté",
    "candidate_status": "interne",
    "statut": "actif",
    "poste_actuel": "Technicien",
    "annees_experience": 5,
    "no_seeg_email": false,
    "created_at": "2025-10-10T12:07:24+00:00",
    "updated_at": "2025-10-13T12:08:45+00:00"
  }
}
```

**Avantages** :
- ✅ Plus besoin d'appeler `/api/v1/auth/me` après le login
- ✅ Réduction de 1 requête HTTP par connexion
- ✅ Meilleure UX avec chargement instantané du profil

### 🔧 **3. Corrections et Améliorations**

- ✅ Champs `date_of_birth`, `sexe`, `candidate_status` optionnels pour admin/recruteur/observateur
- ✅ ID du créateur automatiquement assigné lors de la création d'offres
- ✅ Commits manquants ajoutés dans les endpoints d'offres
- ✅ Gestion d'erreur améliorée avec logs détaillés
- ✅ Toutes les erreurs de linter corrigées
- ✅ Documentation complète mise à jour

---

## 🏗️ Architecture

### Stack technique

**Backend**
- FastAPI 0.109+ (async/await)
- SQLAlchemy 2.0+ (ORM async)
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

### Structure du projet

```
SEEG-API/
├── app/
│   ├── api/v1/endpoints/      # Endpoints FastAPI
│   ├── core/                  # Configuration, sécurité
│   ├── db/                    # Database, migrations
│   ├── models/                # Models SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   ├── services/              # Business logic
│   └── main.py                # Point d'entrée
├── scripts/                   # Scripts de déploiement
│   ├── deploy-api-v2.ps1     # Déploiement complet
│   └── run-migrations.ps1    # Migrations DB
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Stack complète
├── alembic.ini                # Config migrations
├── requirements.txt           # 51 dépendances
└── README.md                  # Documentation
```

---

## 🔐 Authentification & Autorisation

### Système d'authentification multi-niveaux

#### Types de candidats

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

### Rôles utilisateur

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

### 💼 Offres d'emploi (`/api/v1/jobs`)

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

## 💡 Exemples d'utilisation

### 1. Connexion avec retour des infos utilisateur

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

### 2. Créer une offre avec questions MTP flexibles

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

### 3. Soumettre une candidature avec réponses MTP

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

#### Configuration

Variables d'environnement requises (App Service → Configuration) :

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
DATABASE_URL=postgresql+asyncpg://user:pass@server.postgres.database.azure.com:5432/db
DATABASE_URL_SYNC=postgresql://user:pass@server.postgres.database.azure.com:5432/db

# CORS
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
ALLOWED_CREDENTIALS=true
```

#### Workflow de déploiement

**1. Déployer l'application**

```powershell
# Déploiement complet (build + config + deploy)
.\scripts\deploy-api-v2.ps1

# Ou avec build local si Docker disponible
.\scripts\deploy-api-v2.ps1 -BuildMode local
```

**Ce que fait ce script** :
- ✅ Vérifie les prérequis (Azure CLI, Docker)
- ✅ Construit l'image Docker (cloud ou local)
- ✅ Push vers Azure Container Registry
- ✅ Configure l'App Service
- ✅ Redémarre l'application
- ✅ Effectue un health check
- ✅ Génère un rapport détaillé

**2. Appliquer les migrations**

```powershell
# Appliquer toutes les migrations en attente
.\scripts\run-migrations.ps1

# Voir l'état actuel
.\scripts\run-migrations.ps1 -Action current

# Voir l'historique
.\scripts\run-migrations.ps1 -Action history

# Rollback
.\scripts\run-migrations.ps1 -Action downgrade -Target "-1"
```

**Ce que fait ce script** :
- ✅ Récupère la chaîne de connexion depuis Azure
- ✅ Ajoute automatiquement votre IP au firewall PostgreSQL
- ✅ Affiche l'état des migrations
- ✅ Exécute les migrations
- ✅ Propose de nettoyer la règle de firewall

**3. Vérifier le déploiement**

```bash
# Health check
curl https://seeg-backend-api.azurewebsites.net/health

# Documentation
https://seeg-backend-api.azurewebsites.net/docs

# Logs en temps réel
az webapp log tail --name seeg-backend-api --resource-group seeg-rg
```

### Docker Compose (Local)

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f seeg-api

# Arrêter
docker-compose down
```

---

## ⚙️ Configuration

### Fichier .env

```bash
# Environnement
ENVIRONMENT=development
DEBUG=true

# Base de données
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/recruteur
DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/recruteur

# Sécurité (générer avec: python -c "import secrets; print(secrets.token_urlsafe(48))")
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

---

## 🗄️ Base de données

### Modèles principaux

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
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'en_attente', 'inactif', 'bloqué', 'archivé')),
    no_seeg_email BOOLEAN DEFAULT false,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    is_internal_candidate BOOLEAN DEFAULT false,
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

#### Table `access_requests`

```sql
CREATE TABLE access_requests (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    phone VARCHAR,
    matricule VARCHAR,
    request_type VARCHAR DEFAULT 'internal_no_seeg_email',
    status VARCHAR DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    viewed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID REFERENCES users(id)
);
```

### Migrations Alembic

```bash
# Créer une nouvelle migration
alembic revision --autogenerate -m "description"

# Appliquer toutes les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1

# Voir l'historique
alembic history

# Voir l'état actuel
alembic current
```

---

## 🧪 Tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_auth_endpoints.py -v
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
```

---

## 🔒 Sécurité

### Authentification
- JWT avec signature HS256
- Access tokens : 30 minutes
- Refresh tokens : 7 jours
- Bcrypt pour les mots de passe (cost=12)

### Validation
- Pydantic pour toutes les entrées
- Email : Format validé
- Mot de passe : Minimum 12 caractères (signup), 8 (login)
- Date de naissance : Âge minimum 18 ans

### CORS
- **Dev** : localhost:3000, localhost:8080
- **Prod** : seeg-talentsource.com, seeg-hcm.vercel.app

---

## 📝 Changelog

### Version 2.1.0 (2025-10-13)

**🎉 Nouvelles fonctionnalités :**
- ✅ **Questions MTP flexibles** au format JSON (max 7 métier, 3 talent, 3 paradigme)
- ✅ **Login enrichi** avec toutes les infos utilisateur (sans mot de passe)
- ✅ **ID créateur automatique** lors de la création d'offres
- ✅ **Champs optionnels** pour admin/recruteur/observateur

**🔧 Corrections :**
- ✅ Commits manquants ajoutés dans les endpoints d'offres
- ✅ Gestion d'erreur améliorée avec logs détaillés
- ✅ Toutes les erreurs de linter corrigées

**📊 Migrations :**
- ✅ `20251013_add_mtp_questions_to_job_offers.py` : Colonne `questions_mtp` (JSONB) ajoutée à `job_offers`
- ✅ 9 colonnes MTP supprimées de `applications`

### Version 2.0.0 (2025-10-10)

**🎉 Système d'Authentification Multi-Niveaux :**
- ✅ Gestion des demandes d'accès pour candidats internes
- ✅ 3 types d'inscription (externe, interne avec/sans email SEEG)
- ✅ Système de statuts (actif, en_attente, bloqué, etc.)
- ✅ Workflow d'approbation/refus avec emails
- ✅ Badge de notification pour les demandes non vues

### Version 1.0.0 (2025-10-08)

**🎉 Version initiale :**
- ✅ Système d'authentification complet
- ✅ Distinction candidats internes/externes
- ✅ Upload de documents PDF
- ✅ Évaluations MTP
- ✅ Monitoring complet

---

## 📞 Support

### Problèmes courants

**1. Erreur de connexion DB**
```bash
# Vérifier PostgreSQL
psql -U postgres -c "SELECT 1"
```

**2. Erreur 401 Unauthorized**
- Vérifier que le token n'est pas expiré
- Format : `Authorization: Bearer <token>`

**3. Erreur CORS**
- Vérifier `ALLOWED_ORIGINS` dans .env

### Logs & Debugging

```bash
# Activer le mode DEBUG dans .env
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## 👨‍💻 Développeurs

**Lead Developer** : Sevan Kedesh IKISSA PENDY  
**Email** : sevankedesh11@gmail.com
**Organisation** : CNX 4.0

---

## 🚀 Statut

**Version actuelle** : 2.1.0  
**Environnement** : Production ✅  
**Architecture** : Clean Code ✅  
**Déploiement** : Azure + Docker ✅

---

**Construit avec ❤️ pour la SEEG**

