# 🧪 Tests - API Calendrier d'Entretiens

**Date de création** : 2025-10-03  
**Couverture** : Routes `/api/v1/interviews/slots`

---

## 📋 Vue d'Ensemble

Cette suite de tests couvre l'intégralité des endpoints de l'API Calendrier d'Entretiens, compatible avec le composant frontend `InterviewCalendarModal.tsx`.

---

## 📊 Couverture des Tests

### Tests d'Intégration (`test_interviews_endpoints.py`)

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestCreateInterviewSlot` | 6 tests | Création de créneaux |
| `TestGetInterviewSlots` | 5 tests | Liste avec filtres |
| `TestGetInterviewSlot` | 2 tests | Récupération par ID |
| `TestUpdateInterviewSlot` | 5 tests | Mise à jour (logique complexe) |
| `TestDeleteInterviewSlot` | 2 tests | Suppression (soft delete) |
| `TestInterviewStatistics` | 2 tests | Statistiques |
| `TestInterviewSlotsOrdering` | 1 test | Ordre de tri |

**Total : 23 tests d'intégration**

### Tests Unitaires (`test_interview_service.py`)

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestCreateInterviewSlot` | 4 tests | Logique création |
| `TestGetInterviewSlots` | 3 tests | Logique filtrage |
| `TestUpdateInterviewSlot` | 3 tests | Logique mise à jour |
| `TestDeleteInterviewSlot` | 2 tests | Logique suppression |
| `TestInterviewStatistics` | 2 tests | Logique statistiques |

**Total : 14 tests unitaires**

---

## 🎯 Scénarios Testés

### 1. Création de Créneaux (POST)

✅ **Création réussie**
```python
test_create_slot_success
- Crée un créneau avec toutes les données
- Vérifie les champs retournés
- Valide is_available = false
```

✅ **Validation des formats**
```python
test_create_slot_invalid_date_format
test_create_slot_invalid_time_format
- Format date invalide (20/10/2025 → 422)
- Format heure invalide (14:00 → 422)
```

✅ **Gestion des conflits**
```python
test_create_slot_already_occupied
- Créneau déjà occupé → 409 Conflict
```

✅ **Application inexistante**
```python
test_create_slot_application_not_found
- application_id inexistant → 404
```

✅ **Mise à jour de créneau disponible**
```python
test_create_slot_update_available_slot
- Créneau disponible → Occuper au lieu de créer
```

### 2. Liste des Créneaux (GET)

✅ **Filtrage par période**
```python
test_list_slots_filter_by_date_range
- date_from / date_to
- Retourne uniquement les créneaux dans la période
```

✅ **Filtrage par disponibilité**
```python
test_list_slots_filter_by_availability
- is_available=false → Seulement créneaux occupés
- Exclut les créneaux sans application_id
```

✅ **Filtrage par statut**
```python
test_list_slots_filter_by_status
- status=scheduled → Seulement programmés
```

✅ **Pagination**
```python
test_list_slots_pagination
- skip / limit
- Vérification page, per_page, total
```

✅ **Ordre de tri**
```python
test_slots_ordered_by_date_and_time
- Tri : date ASC, puis time ASC
```

### 3. Mise à Jour de Créneaux (PUT)

✅ **Mise à jour simple**
```python
test_update_slot_simple
- status, notes → Sans changement date/heure
```

✅ **Changement de date (Logique Complexe)**
```python
test_update_slot_change_date
- Libération ancien créneau automatique
- Création nouveau créneau
- Vérification status=cancelled sur ancien
```

✅ **Changement d'heure**
```python
test_update_slot_change_time
- Même logique que changement de date
```

✅ **Conflit lors du changement**
```python
test_update_slot_change_to_occupied_slot
- Nouveau créneau déjà occupé → 409
```

### 4. Suppression de Créneaux (DELETE)

✅ **Soft Delete**
```python
test_delete_slot_success
- Marque status=cancelled
- is_available=true
- application_id=null
- Garde les données (historique)
```

### 5. Statistiques (GET)

✅ **Calcul des statistiques**
```python
test_get_statistics_with_data
- total_interviews
- scheduled/completed/cancelled
- interviews_by_status
```

---

## 🚀 Exécution des Tests

### Tous les tests d'entretiens
```bash
pytest tests/interviews/ -v
```

### Tests d'intégration uniquement
```bash
pytest tests/interviews/test_interviews_endpoints.py -v
```

### Tests unitaires uniquement
```bash
pytest tests/unit/test_interview_service.py -v
```

### Test spécifique
```bash
pytest tests/interviews/test_interviews_endpoints.py::TestCreateInterviewSlot::test_create_slot_success -v
```

### Avec couverture
```bash
pytest tests/interviews/ --cov=app.services.interview --cov=app.api.v1.endpoints.interviews --cov-report=html
```

---

## 🔧 Fixtures Utilisées

### Fixtures de Base
- `test_db` : Session de base de données de test
- `client` : Client HTTP AsyncClient
- `auth_headers` : Headers d'authentification
- `test_user` : Utilisateur de test

### Fixtures Spécifiques
- `test_job_offer` : Offre d'emploi de test
- `test_application` : Candidature de test
- `test_interview_slot` : Créneau d'entretien de test
- `interview_service` : Instance du service

---

## 📈 Métriques de Qualité

### Couverture Attendue
- **Service** : 100% (`app/services/interview.py`)
- **Endpoints** : 100% (`app/api/v1/endpoints/interviews.py`)
- **Schémas** : 100% (validations Pydantic)

### Temps d'Exécution
- **Tests unitaires** : ~2 secondes
- **Tests d'intégration** : ~5 secondes
- **Total** : ~7 secondes

---

## ⚠️ Points d'Attention

### 1. Logique Complexe de Changement Date/Heure
Les tests vérifient que :
- L'ancien créneau est bien libéré
- Le nouveau créneau est créé ou occupé
- Les conflits sont détectés

### 2. Soft Delete
Les tests vérifient que :
- Les données sont conservées
- Le statut devient "cancelled"
- Le créneau redevient disponible

### 3. Validations Pydantic
Les tests vérifient que :
- Les formats date/heure sont validés
- Les erreurs 422 sont retournées

---

## 🐛 Débogage

### Test qui échoue
```bash
pytest tests/interviews/test_interviews_endpoints.py::TestName::test_name -vv -s
```

### Voir les logs
```bash
pytest tests/interviews/ -v --log-cli-level=INFO
```

### Seulement le premier échec
```bash
pytest tests/interviews/ -x
```

---

## 📝 Ajouter un Nouveau Test

### Template de Test
```python
@pytest.mark.asyncio
async def test_my_scenario(
    self,
    client: AsyncClient,
    test_db: AsyncSession,
    auth_headers: dict,
    test_application: Application
):
    """Test description"""
    # Arrange
    payload = {...}
    
    # Act
    response = await client.post(
        "/api/v1/interviews/slots",
        json=payload,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == expected_value
```

---

**Dernière mise à jour** : 2025-10-03  
**Mainteneur** : SEEG Backend Team  
**Status** : ✅ Prêt pour CI/CD

