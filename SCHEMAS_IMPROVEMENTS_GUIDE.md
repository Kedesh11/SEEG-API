# Guide d'amélioration des schémas Pydantic - SEEG API
## Architecture & Bonnes Pratiques

### ✅ Améliorations apportées

Ce document récapitule les améliorations apportées aux schémas Pydantic de l'API selon les principes SOLID et les meilleures pratiques de génie logiciel.

---

## 📚 Principes appliqués

### 1. **DRY (Don't Repeat Yourself)**
- ✅ Constantes centralisées pour valeurs réutilisables
- ✅ Validation unifiée avec références aux constantes
- ✅ Pas de duplication de code

### 2. **Documentation exhaustive**
- ✅ Docstrings détaillées pour chaque classe
- ✅ Descriptions claires pour chaque champ
- ✅ Cas d'usage documentés
- ✅ Exemples multiples et réalistes

### 3. **Type Safety**
- ✅ Types strictement définis
- ✅ Validations avec `field_validator`
- ✅ Messages d'erreur explicites en français

### 4. **Exemples OpenAPI améliorés**
- ✅ Format `examples` (pluriel) pour montrer plusieurs cas
- ✅ Chaque exemple avec `description` et `value`
- ✅ Données gabonaises réalistes (+241, adresses Libreville, etc.)

---

## 📁 Fichiers améliorés

### ✅ **app/schemas/auth.py** - TERMINÉ

#### Constantes ajoutées
```python
# Types de candidats
CANDIDATE_STATUS_INTERNAL = "interne"
CANDIDATE_STATUS_EXTERNAL = "externe"
ALLOWED_CANDIDATE_STATUS = {CANDIDATE_STATUS_INTERNAL, CANDIDATE_STATUS_EXTERNAL}

# Sexes
SEXE_MALE = "M"
SEXE_FEMALE = "F"
ALLOWED_SEXES = {SEXE_MALE, SEXE_FEMALE}

# Contraintes mot de passe
PASSWORD_MIN_LENGTH_LOGIN = 8
PASSWORD_MIN_LENGTH_SIGNUP = 12
```

#### Schémas améliorés

1. **LoginRequest**
   - 3 exemples (candidat externe, interne, recruteur)
   - Documentation cas d'usage
   - Validation avec constantes

2. **CandidateSignupRequest**
   - 3 exemples (externe, interne avec email SEEG, interne sans email)
   - Documentation règles métier
   - Adresses gabonaises réalistes

3. **CreateUserRequest**
   - 2 exemples (recruteur, admin)
   - Documentation rôles

4. **TokenResponse / TokenResponseData**
   - Documentation JWT (durées, usage)
   - Exemples avec UUIDs réalistes

5. **PasswordReset* / ChangePassword**
   - Documentation flow de réinitialisation
   - Sécurité expliquée

---

### ✅ **app/schemas/application.py** - TERMINÉ

#### Constantes ajoutées
```python
# Documents OBLIGATOIRES
REQUIRED_DOCUMENT_TYPES = {'cv', 'cover_letter', 'diplome'}

# Documents OPTIONNELS
OPTIONAL_DOCUMENT_TYPES = {'certificats', 'lettre_recommandation', 'portfolio', 'autres'}

# Tous les types autorisés
ALLOWED_DOCUMENT_TYPES = REQUIRED_DOCUMENT_TYPES | OPTIONAL_DOCUMENT_TYPES

# Noms affichables
DOCUMENT_TYPE_NAMES = {
    'cv': 'CV',
    'cover_letter': 'Lettre de motivation',
    'diplome': 'Diplôme',
    'certificats': 'Certificats',
    'lettre_recommandation': 'Lettre de recommandation',
    'portfolio': 'Portfolio',
    'autres': 'Autres documents'
}
```

#### Améliorations clés
- ✅ Support documents optionnels (certificats, portfolio, etc.)
- ✅ Validation 3 obligatoires + illimités optionnels
- ✅ Détection doublons
- ✅ Messages d'erreur explicites

---

## 🎯 Fichiers à améliorer

### 📋 **app/schemas/user.py** - EN COURS

**Améliorations à apporter:**
- [ ] Constantes pour statuts utilisateur
- [ ] Documentation enrichie (UserBase, UserUpdate, etc.)
- [ ] Exemples réalistes pour chaque schéma
- [ ] Validation avec field_validator
- [ ] CandidateProfile avec exemples complets

---

### 📋 **app/schemas/job.py** - À FAIRE

**Améliorations à apporter:**
- [ ] Constantes pour types de contrat
- [ ] Constantes pour statuts d'offre
- [ ] Documentation questions MTP
- [ ] Exemples d'offres internes/externes
- [ ] Validation départements SEEG

---

### 📋 **app/schemas/evaluation.py** - À FAIRE

**Améliorations à apporter:**
- [ ] Constantes pour critères d'évaluation
- [ ] Documentation protocole MTP
- [ ] Exemples de grilles d'évaluation
- [ ] Validation scores

---

### 📋 **app/schemas/notification.py** - À FAIRE

**Améliorations à apporter:**
- [ ] Constantes pour types de notifications
- [ ] Documentation priorités
- [ ] Exemples de notifications
- [ ] Validation statuts

---

## 📐 Template de schéma amélioré

```python
"""
Schémas Pydantic pour [DOMAIN]
===================================
Architecture: Type-Safe + Validation Stricte + Documentation Complète

Schémas principaux:
- [Schema1]: [Description]
- [Schema2]: [Description]
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# CONSTANTES - [Domain specific constants]
# ============================================================================

CONSTANT_NAME = "value"
ALLOWED_VALUES = {"value1", "value2"}

class ExampleSchema(BaseModel):
    """
    [Description détaillée du schéma]
    
    Utilisé pour:
    - [Cas d'usage 1]
    - [Cas d'usage 2]
    
    **Validation**:
    - [Règle 1]
    - [Règle 2]
    """
    field_name: str = Field(
        ...,
        description="Description claire du champ",
        examples=["exemple1", "exemple2"]
    )
    
    @field_validator('field_name')
    @classmethod
    def validate_field(cls, v):
        """Documentation de la validation."""
        if v not in ALLOWED_VALUES:
            raise ValueError(f"Valeur invalide. Autorisées: {ALLOWED_VALUES}")
        return v
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Cas d'usage 1",
                    "value": {
                        "field_name": "exemple1"
                    }
                },
                {
                    "description": "Cas d'usage 2",
                    "value": {
                        "field_name": "exemple2"
                    }
                }
            ]
        }
```

---

## 🎨 Standards de naming

### Constantes
- **UPPER_SNAKE_CASE** pour constantes
- Préfixe descriptif (ex: `CANDIDATE_STATUS_`, `DOCUMENT_TYPE_`)
- Sets pour collections (ex: `ALLOWED_SEXES`, `REQUIRED_DOCUMENT_TYPES`)

### Champs
- **snake_case** pour champs Pydantic
- **camelCase** évité (sauf conversion JSON si nécessaire)

### Classes
- **PascalCase** pour classes
- Suffixes descriptifs: `Request`, `Response`, `Create`, `Update`

---

## 📝 Exemples de qualité

### ✅ BON exemple
```python
class Config:
    json_schema_extra = {
        "examples": [
            {
                "description": "Candidat externe gabonais",
                "value": {
                    "email": "marie.kouamba@gmail.com",
                    "first_name": "Marie",
                    "last_name": "Kouamba",
                    "phone": "+241 07 11 22 33",
                    "adresse": "Quartier Nzeng-Ayong, Libreville"
                }
            }
        ]
    }
```

### ❌ Mauvais exemple
```python
class Config:
    json_schema_extra = {
        "example": {
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
    }
```

**Pourquoi c'est mieux:**
- ✅ `examples` (pluriel) au lieu de `example`
- ✅ Description pour chaque exemple
- ✅ Données réalistes (gabonais, numéros +241)
- ✅ Plusieurs cas d'usage montrés

---

## 🚀 Bénéfices

### Pour les développeurs
- ✅ Documentation auto-générée dans Swagger/ReDoc
- ✅ Exemples directement testables
- ✅ Messages d'erreur clairs
- ✅ Code maintenable (DRY)

### Pour les utilisateurs API
- ✅ Exemples concrets dans la documentation
- ✅ Validation claire des données
- ✅ Erreurs explicites en français

### Pour la qualité du code
- ✅ Type-safe avec mypy/pyright
- ✅ Validation à l'exécution
- ✅ Tests plus faciles
- ✅ Moins de bugs en production

---

## ✅ Checklist pour chaque schéma

- [ ] Constantes définies en haut du fichier
- [ ] Docstring classe avec cas d'usage
- [ ] Tous les champs ont une `description`
- [ ] `field_validator` pour validations complexes
- [ ] Minimum 2-3 `examples` par schéma
- [ ] Exemples avec données gabonaises réalistes
- [ ] Messages d'erreur en français
- [ ] Aucune duplication de code
- [ ] Linter sans erreur

---

*Document maintenu à jour au fil des améliorations*

