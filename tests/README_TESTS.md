# 🧪 Module de Tests SEEG API

Module de tests complet et professionnel suivant les meilleures pratiques de Génie Logiciel.

## 📁 Architecture

```
tests/
├── fixtures/                      # Fixtures réutilisables (DRY)
│   ├── __init__.py
│   ├── auth_fixtures.py          # Données auth (signup, login)
│   ├── application_fixtures.py    # Données candidatures + documents
│   ├── db_fixtures.py            # Sessions DB avec isolation
│   └── http_fixtures.py          # Clients HTTP authentifiés
│
├── test_auth_complete.py         # Tests authentification (signup, login, refresh)
├── test_applications_complete.py  # Tests candidatures (CRUD + documents)
├── test_access_requests_complete.py # Tests demandes d'accès
├── test_job_offers_complete.py   # Tests offres d'emploi (CRUD)
├── test_users_complete.py        # Tests utilisateurs (CRUD + permissions)
├── test_notifications_complete.py # Tests notifications
│
├── conftest.py                    # Configuration centrale pytest
└── README_TESTS.md               # Cette documentation
```

## 🚀 Utilisation

### Tests Locaux (environnement de développement)

```bash
# Tous les tests
python run_tests.py

# Module spécifique
python run_tests.py --module auth
python run_tests.py --module applications

# Mode verbeux
python run_tests.py --verbose
```

### Tests Production (Azure)

```bash
# Tous les tests en production
python run_tests.py --env production

# Module spécifique en production
python run_tests.py --env production --module auth --verbose
```

### Tests avec pytest directement

```bash
# Tous les tests
pytest tests/ -v

# Tests d'un fichier spécifique
pytest tests/test_auth_complete.py -v

# Tests d'une classe spécifique
pytest tests/test_auth_complete.py::TestAuthSignup -v

# Test spécifique
pytest tests/test_auth_complete.py::TestAuthSignup::test_signup_externe_success -v
```

## 📋 Modules de Tests

### 1. **Authentication** (`test_auth_complete.py`)

**Couverture:**
- ✅ Inscription (externe, interne avec/sans email SEEG)
- ✅ Connexion (credentials valides/invalides, statuts)
- ✅ Refresh token
- ✅ Vérification matricule
- ✅ Profil utilisateur (/auth/me)

**Tests clés:**
- Inscription interne sans email SEEG → statut `'en_attente'` + AccessRequest
- Inscription interne avec email SEEG → statut `'actif'` sans AccessRequest
- Connexion avec compte en attente → 403 Forbidden

### 2. **Applications** (`test_applications_complete.py`)

**Couverture:**
- ✅ Création avec 3 documents obligatoires (CV, lettre, diplôme)
- ✅ Validation documents manquants
- ✅ Listing et pagination
- ✅ Récupération par ID
- ✅ Liste et téléchargement documents

**Tests clés:**
- Création atomique candidature + documents en une requête
- Validation des 3 types de documents obligatoires
- Gestion documents invalides

### 3. **Access Requests** (`test_access_requests_complete.py`)

**Couverture:**
- ✅ Création automatique (inscription interne sans email SEEG)
- ✅ Listing (admin uniquement)
- ✅ Approbation/Rejet (admin uniquement)
- ✅ Permissions

**Tests clés:**
- AccessRequest créée si `no_seeg_email=True`
- Candidat ne peut pas accéder aux demandes (403)

### 4. **Job Offers** (`test_job_offers_complete.py`)

**Couverture:**
- ✅ CRUD complet
- ✅ Listing public
- ✅ Permissions par rôle

### 5. **Users** (`test_users_complete.py`)

**Couverture:**
- ✅ Listing (admin)
- ✅ Récupération par ID
- ✅ Mise à jour profil
- ✅ Permissions

### 6. **Notifications** (`test_notifications_complete.py`)

**Couverture:**
- ✅ Listing notifications utilisateur
- ✅ Marquage comme lu

## 🎯 Principes SOLID Appliqués

### **Single Responsibility**
- Chaque classe de tests teste un endpoint ou une fonctionnalité
- Fixtures dédiées par domaine

### **Open/Closed**
- Fixtures extensibles sans modification
- Ajout de nouveaux tests sans casser l'existant

### **Dependency Injection**
- Fixtures injectées via pytest
- Configuration externalisée

### **Interface Segregation**
- Fixtures spécialisées plutôt que monolithiques
- Clients HTTP factory pour différents rôles

### **Don't Repeat Yourself (DRY)**
- Fixtures réutilisables
- Factories pour données paramétrables

## 📊 Rapports

### Rapport XML (JUnit)

```bash
test-results-local.xml      # Tests locaux
test-results-production.xml # Tests production
```

Compatible avec CI/CD (Azure Pipelines, GitHub Actions, etc.)

### Rapport Console

```
✅ Tests réussis: 45
❌ Tests échoués: 2
⏭  Tests skippés: 5
📊 Total: 52
⏱  Durée: 12.34s
```

## 🔧 Configuration

### Variables d'Environnement

```bash
TEST_ENV=local          # ou 'production'
ENVIRONMENT=testing     # Activer mode test
```

### Pytest Configuration (conftest.py)

- Markers personnalisés (`@pytest.mark.asyncio`, `@pytest.mark.slow`)
- Event loop partagé pour tests async
- Fixtures scope function pour isolation

## ✅ Bonnes Pratiques

1. **Isolation**: Chaque test est indépendant (rollback DB)
2. **Nommage**: `test_<action>_<scenario>_<expected_result>`
3. **AAA Pattern**: Arrange, Act, Assert
4. **Documentation**: Docstring pour chaque test
5. **Fixtures**: Données réutilisables et paramétrables
6. **Assertions**: Claires et spécifiques
7. **Skip**: Utiliser `pytest.skip()` pour tests nécessitant setup spécial

## 🆘 Dépannage

### Erreur "ModuleNotFoundError"

```bash
pip install pytest pytest-asyncio httpx
```

### Tests DB échouent

```bash
# Vérifier PostgreSQL
psql -U postgres -d recruteur -c "SELECT 1;"
```

### Tests production échouent

```bash
# Vérifier API accessible
curl https://seeg-backend-api.azurewebsites.net/health
```

### Réinitialiser DB de test

```bash
# Recreate test database
dropdb recruteur_test
createdb recruteur_test
python scripts/migrate_database_local.py --action upgrade
```

## 📈 Métriques de Couverture

Pour générer un rapport de couverture de code:

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

Rapport généré dans `htmlcov/index.html`

## 🔄 Intégration CI/CD

Le module de tests est prêt pour l'intégration dans Azure Pipelines:

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install -r requirements.txt
    python run_tests.py --env production --verbose
  displayName: 'Run Tests'

- task: PublishTestResults@2
  inputs:
    testResultsFiles: 'test-results-*.xml'
    testRunTitle: 'SEEG API Tests'
```

## 📝 Ajouter de Nouveaux Tests

1. Créer un nouveau fichier: `tests/test_<module>_complete.py`
2. Organiser en classes par endpoint
3. Utiliser les fixtures existantes
4. Suivre le pattern AAA (Arrange, Act, Assert)
5. Documenter chaque test avec docstring

Exemple:

```python
@pytest.mark.asyncio
async def test_my_new_feature_success(
    self,
    http_client: AsyncClient,
    my_fixture: Dict[str, Any]
):
    """
    Scénario: Description du cas de test
    Attendu: Résultat attendu
    """
    # Arrange
    data = {"key": "value"}
    
    # Act
    response = await http_client.post("/endpoint", json=data)
    
    # Assert
    assert response.status_code == 200
```

