# 🏢 One HCM SEEG Backend API

API de gestion des ressources humaines pour la SEEG (Société d'Énergie et d'Eau du Gabon)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00C7B7?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Azure](https://img.shields.io/badge/Azure-Ready-0078D4?logo=microsoft-azure)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

---

## 📋 Table des matières

- [Aperçu](#apercu)
- [Fonctionnalités](#fonctionnalites)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Déploiement](#deploiement)
- [API Documentation](#api-documentation)
- [Développement](#developpement)
- [Tests](#tests)
- [Monitoring](#monitoring)
- [Sécurité](#securite)

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
- Inscription candidats (internes avec matricule / externes sans matricule)
- Connexion multi-format (JSON, form-urlencoded)
- JWT avec access & refresh tokens (durées configurables)
- Gestion des rôles (candidate, recruiter, admin, observer)
- Réinitialisation de mot de passe par email
- Vérification de matricule SEEG

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

- Python 3.12+
- PostgreSQL 16+
- Redis (optionnel, pour cache)
- Git

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

#### Prérequis Azure
- Azure CLI installé
- App Service créé
- Azure PostgreSQL configuré

#### Configuration Azure

1. **Variables d'environnement** (App Service → Configuration) :

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generer-une-cle-securisee>
DATABASE_URL=postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
APPLICATIONINSIGHTS_CONNECTION_STRING=<votre-connection-string>
```

2. **Déploiement avec mise à jour continue** :

```bash
# Lancer le script de mise à jour
.\scripts\mise_a_jour.ps1

# Le script vous demandera si vous voulez executer les migrations
# Tapez 'y' pour oui

# Si les migrations echouent localement (normal car DB Azure):
# Tapez 'y' pour continuer le deploiement

# Les migrations seront appliquées AUTOMATIQUEMENT au demarrage
# du conteneur Docker sur Azure via docker-entrypoint.sh
```

**Important** : Les migrations locales peuvent échouer si vous n'avez pas accès à la DB Azure en local. C'est normal ! Les migrations s'exécuteront automatiquement au démarrage du conteneur sur Azure.

3. **Vérifier le déploiement** :

```bash
# Health check
curl https://seeg-backend-api.azurewebsites.net/health

# Swagger UI
https://seeg-backend-api.azurewebsites.net/docs
```

4. **Créer les utilisateurs (après déploiement)** :

```bash
# Se connecter à Azure
az webapp ssh --name seeg-backend-api --resource-group seeg-backend-rg

# Ou localement avec DATABASE_URL pointant vers Azure
python scripts/create_recruiters_after_migration.py
```

---

## 📚 API Documentation

### Endpoints principaux

#### 🔐 Authentification (`/api/v1/auth`)

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| POST | `/login` | Connexion | Non |
| POST | `/signup` | Inscription candidat | Non |
| POST | `/create-user` | Créer utilisateur | Admin |
| GET | `/me` | Profil utilisateur | Oui |
| POST | `/refresh` | Rafraîchir token | Non |
| POST | `/logout` | Déconnexion | Oui |
| POST | `/forgot-password` | Mot de passe oublié | Non |
| POST | `/reset-password` | Réinitialiser MdP | Non |
| POST | `/change-password` | Changer MdP | Oui |
| GET | `/verify-matricule` | Vérifier matricule | Candidat |

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

#### Inscription candidat INTERNE (employé SEEG)

```bash
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "employe@seeg.ga",
  "password": "SecurePass123!@#",
  "first_name": "Marie",
  "last_name": "Obame",
  "matricule": 145678,        # ← Avec matricule = INTERNE
  "phone": "+241066123456",
  "date_of_birth": "1988-03-15",
  "sexe": "F"
}

# Réponse: is_internal_candidate = true
```

#### Inscription candidat EXTERNE

```bash
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "candidat@gmail.com",
  "password": "SecurePass123!@#",
  "first_name": "Jean",
  "last_name": "Dupont",
  "matricule": null,          # ← Sans matricule = EXTERNE
  "phone": "+241077999888",
  "date_of_birth": "1995-07-20",
  "sexe": "M"
}

# Réponse: is_internal_candidate = false
```

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

## 📊 Monitoring

### Métriques (Prometheus)

Accessible sur : **http://localhost:9090** (Docker Compose)

Endpoints exposés :
- `/monitoring/metrics` - Métriques Prometheus
- `/monitoring/health` - Health check détaillé

### Tracing (Jaeger)

Accessible sur : **http://localhost:16686** (Docker Compose)

- Tracing distribué des requêtes
- Analyse des performances
- Détection des goulots d'étranglement

### Logs

- Format : JSON structuré (production) ou console (dev)
- Niveau : Configurable via `LOG_LEVEL`
- Stockage : `logs/` directory

```bash
# Voir les logs en temps réel
tail -f logs/app.log
```

### Azure Application Insights

Configuration :
```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=<votre-connection-string>
```

Fonctionnalités :
- Tracing automatique des requêtes
- Détection d'anomalies
- Alertes configurables
- Dashboards intégrés

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

#### Table `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- candidate, recruiter, admin, observer
    phone VARCHAR,
    date_of_birth TIMESTAMP,
    sexe VARCHAR,
    matricule INTEGER UNIQUE,  -- NULL pour candidats externes
    hashed_password VARCHAR NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    is_internal_candidate BOOLEAN DEFAULT false,  -- NEW: Detection auto interne/externe
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_matricule ON users(matricule);
CREATE INDEX ix_users_is_internal_candidate ON users(is_internal_candidate, role);
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

### `scripts/mise_a_jour.ps1`
Script de mise à jour continue

### `scripts/deploy-azure.ps1`
Déploiement automatisé sur Azure

### `scripts/manual_auth_tests.py`
Tests manuels des endpoints auth

---

## 📝 Changelog

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

Propriété de la SEEG (Société d'Énergie et d'Eau du Gabon)

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
