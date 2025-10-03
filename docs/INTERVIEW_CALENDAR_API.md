# 📅 API Calendrier d'Entretiens - Documentation Complète

**Date de mise à jour** : 2025-10-03  
**Version** : 1.0  
**Status** : ✅ Implémenté et prêt pour production

---

## 🎯 Vue d'Ensemble

L'API Calendrier d'Entretiens permet de gérer les créneaux d'entretien pour les candidatures SEEG. Elle est entièrement compatible avec le composant frontend `InterviewCalendarModal.tsx`.

### Fonctionnalités Principales

- ✅ **Création de créneaux** avec validation de conflits
- ✅ **Modification de créneaux** avec gestion automatique des changements de date/heure
- ✅ **Annulation de créneaux** (soft delete pour historique)
- ✅ **Filtrage avancé** par date, disponibilité, statut, candidature
- ✅ **Statistiques** globales des entretiens

---

## 📊 Modèle de Données

### Structure `InterviewSlot`

```python
{
  "id": "uuid",                          # Identifiant unique
  "date": "2025-10-15",                  # Format: YYYY-MM-DD
  "time": "09:00:00",                    # Format: HH:mm:ss
  "application_id": "uuid" | null,       # ID candidature (null si disponible)
  "candidate_name": "John Doe" | null,   # Nom du candidat
  "job_title": "Développeur" | null,     # Titre du poste
  "status": "scheduled",                 # scheduled | completed | cancelled
  "is_available": false,                 # true = libre, false = occupé
  "location": "Libreville",              # Lieu de l'entretien
  "notes": "Entretien technique",        # Notes supplémentaires
  "created_at": "2025-10-02T10:00:00Z",
  "updated_at": "2025-10-02T10:00:00Z"
}
```

### Statuts Disponibles

| Statut | Description |
|--------|-------------|
| `scheduled` | Entretien programmé (par défaut) |
| `completed` | Entretien terminé |
| `cancelled` | Entretien annulé |

---

## 🔌 Routes API

### 1. 📋 **GET** `/api/v1/interviews/slots` - Lister les Créneaux

**Description** : Récupère tous les créneaux d'entretien avec filtres avancés

#### Query Parameters

| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `skip` | int | Pagination (offset) | `0` |
| `limit` | int | Nombre max d'éléments | `50` |
| `date_from` | string | Date de début (YYYY-MM-DD) | `2025-10-01` |
| `date_to` | string | Date de fin (YYYY-MM-DD) | `2025-10-31` |
| `is_available` | boolean | Filtrer par disponibilité | `false` |
| `application_id` | uuid | Filtrer par candidature | `uuid` |
| `status` | string | Filtrer par statut | `scheduled` |
| `order` | string | Ordre de tri | `date:asc,time:asc` |

#### Exemples de Requêtes

**Liste des entretiens occupés du mois**
```http
GET /api/v1/interviews/slots?date_from=2025-10-01&date_to=2025-10-31&is_available=false

Response: 200 OK
{
  "data": [
    {
      "id": "uuid-1",
      "date": "2025-10-15",
      "time": "09:00:00",
      "application_id": "app-uuid-1",
      "candidate_name": "John Doe",
      "job_title": "Développeur Full Stack",
      "status": "scheduled",
      "is_available": false,
      "location": "Libreville",
      "notes": "Entretien technique",
      "created_at": "2025-10-02T10:00:00Z",
      "updated_at": "2025-10-02T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 50,
  "total_pages": 1
}
```

**Liste des créneaux disponibles**
```http
GET /api/v1/interviews/slots?date_from=2025-10-15&date_to=2025-10-15&is_available=true
```

#### Comportements Spécifiques

1. ✅ Retourne **uniquement les créneaux occupés** si `is_available=false`
2. ✅ Exclut les créneaux sans `application_id` si `is_available=false`
3. ✅ Tri par défaut : `date ASC`, puis `time ASC`
4. ✅ Inclut `candidate_name` et `job_title` (données dénormalisées)

---

### 2. ➕ **POST** `/api/v1/interviews/slots` - Créer un Créneau

**Description** : Crée un nouveau créneau d'entretien avec validation de conflits

#### Request Body

```json
{
  "date": "2025-10-15",
  "time": "09:00:00",
  "application_id": "app-uuid-1",
  "candidate_name": "John Doe",
  "job_title": "Développeur Full Stack",
  "status": "scheduled",
  "location": "Libreville",
  "notes": "Entretien technique"
}
```

#### Validations Backend

1. ✅ **Vérifier que l'application existe** (FK constraint)
2. ✅ **Vérifier que le créneau n'est pas déjà occupé**
3. ✅ **Valider le format de la date** (YYYY-MM-DD)
4. ✅ **Valider le format de l'heure** (HH:mm:ss)
5. ✅ **Automatiquement set** `is_available: false` et `status: "scheduled"`
6. ✅ **Si créneau existant disponible** → Mise à jour au lieu de création

#### Réponses

**Succès - 201 Created**
```json
{
  "id": "uuid-new",
  "date": "2025-10-15",
  "time": "09:00:00",
  "application_id": "app-uuid-1",
  "candidate_name": "John Doe",
  "job_title": "Développeur Full Stack",
  "status": "scheduled",
  "is_available": false,
  "location": "Libreville",
  "notes": "Entretien technique",
  "created_at": "2025-10-02T14:30:00Z",
  "updated_at": "2025-10-02T14:30:00Z"
}
```

**Erreur - 409 Conflict**
```json
{
  "detail": "Le créneau 2025-10-15 à 09:00:00 est déjà occupé"
}
```

**Erreur - 404 Not Found**
```json
{
  "detail": "Candidature non trouvée"
}
```

**Erreur - 400 Bad Request**
```json
{
  "detail": "Format de date invalide. Attendu: YYYY-MM-DD"
}
```

---

### 3. ✏️ **PUT** `/api/v1/interviews/slots/{slot_id}` - Modifier un Créneau

**Description** : Met à jour un créneau avec logique complexe de changement de date/heure

#### Logique Complexe - Changement de Date/Heure

Lorsque la **date** ou **l'heure** change :

1. **Libérer l'ancien créneau**
   - Marquer comme `is_available: true`
   - Dissocier la candidature (`application_id: null`)
   - Status `cancelled`

2. **Vérifier si le nouveau créneau existe**
   - Si disponible → L'occuper
   - Si n'existe pas → Créer nouveau
   - Si occupé par autre application → Erreur 409

3. **Retourner le nouveau créneau**

#### Request Body (tous les champs optionnels)

```json
{
  "date": "2025-10-16",      // Changement de date
  "time": "10:00:00",        // Changement d'heure
  "status": "scheduled",
  "notes": "Entretien reporté"
}
```

#### Exemples

**Mise à jour simple (sans changement de date/heure)**
```http
PUT /api/v1/interviews/slots/slot-uuid-1

Request:
{
  "status": "completed",
  "notes": "Entretien réussi"
}

Response: 200 OK
{
  "id": "slot-uuid-1",
  "date": "2025-10-15",
  "time": "09:00:00",
  "status": "completed",
  "notes": "Entretien réussi",
  ...
}
```

**Mise à jour avec changement de date/heure**
```http
PUT /api/v1/interviews/slots/slot-uuid-1

Request:
{
  "date": "2025-10-16",
  "time": "10:00:00"
}

Response: 200 OK
{
  "id": "slot-uuid-new",     // ⚠️ Nouvel ID (nouveau créneau créé)
  "date": "2025-10-16",
  "time": "10:00:00",
  "application_id": "app-uuid-1",  // Conservé
  "candidate_name": "John Doe",    // Conservé
  ...
}
```

**Erreur - Nouveau créneau occupé**
```http
Response: 409 Conflict
{
  "detail": "Le créneau 2025-10-16 à 10:00:00 est déjà occupé par une autre candidature"
}
```

---

### 4. 🗑️ **DELETE** `/api/v1/interviews/slots/{slot_id}` - Annuler un Créneau

**Description** : Annule un créneau (soft delete pour conserver l'historique)

#### Logique Backend

- ✅ **Soft delete** : Ne pas supprimer physiquement
- ✅ **Libérer le créneau** : `is_available: true`
- ✅ **Marquer comme annulé** : `status: "cancelled"`
- ✅ **Dissocier la candidature** : `application_id: null`
- ✅ **Garder l'historique** : Conserver les données pour audit

#### Exemple

```http
DELETE /api/v1/interviews/slots/slot-uuid-1

Response: 200 OK
{
  "message": "Entretien annulé avec succès",
  "slot_id": "slot-uuid-1"
}
```

---

### 5. 📊 **GET** `/api/v1/interviews/stats/overview` - Statistiques

**Description** : Récupère les statistiques globales des entretiens

#### Réponse

```json
{
  "total_interviews": 120,
  "scheduled_interviews": 45,
  "completed_interviews": 60,
  "cancelled_interviews": 15,
  "interviews_by_status": {
    "scheduled": 45,
    "completed": 60,
    "cancelled": 15
  }
}
```

---

## 🔐 Permissions et Sécurité

### Règles de Permissions

| Rôle | GET | POST | PUT | DELETE |
|------|-----|------|-----|--------|
| **Admin** | ✅ Tous | ✅ Tous | ✅ Tous | ✅ Tous |
| **Recruiter** | ✅ Ses applications | ✅ Ses applications | ✅ Ses créneaux | ✅ Ses créneaux |
| **Observer** | ✅ Tous (lecture) | ❌ | ❌ | ❌ |
| **Candidate** | ✅ Ses entretiens | ❌ | ❌ | ❌ |

---

## 🧪 Tests Recommandés

### Scénarios de Test

#### Test 1 : Créer un créneau
```http
POST /api/v1/interviews/slots
{
  "date": "2025-10-15",
  "time": "09:00:00",
  "application_id": "app-1",
  "candidate_name": "John Doe",
  "job_title": "Développeur"
}
→ 201 Created ✅
```

#### Test 2 : Créer un créneau déjà occupé
```http
POST /api/v1/interviews/slots
{
  "date": "2025-10-15",
  "time": "09:00:00",    // Déjà occupé
  "application_id": "app-2"
}
→ 409 Conflict ❌
```

#### Test 3 : Modifier la date d'un entretien
```http
PUT /api/v1/interviews/slots/slot-1
{
  "date": "2025-10-16"   // Changement de date
}
→ 200 OK ✅
→ Ancien créneau libéré automatiquement
```

#### Test 4 : Lister les créneaux du mois
```http
GET /api/v1/interviews/slots?date_from=2025-10-01&date_to=2025-10-31&is_available=false
→ 200 OK ✅
→ Liste triée par date ASC, time ASC
```

#### Test 5 : Annuler un entretien
```http
DELETE /api/v1/interviews/slots/slot-1
→ 200 OK ✅
→ Status = "cancelled", is_available = true
```

---

## 🚀 Migration Frontend

### Remplacement Supabase → Backend API

#### Ancien Code (Supabase)
```typescript
const { data: slots } = await supabase
  .from('interview_slots')
  .select('*')
  .eq('is_available', false)
  .gte('date', monthStartStr)
  .lte('date', monthEndStr)
  .order('date', { ascending: true });
```

#### Nouveau Code (Backend API)
```typescript
import { listSlots, createSlot, updateSlot, deleteSlot } from '@/integrations/api/interviews';

// Lister
const response = await listSlots({
  date_from: monthStartStr,
  date_to: monthEndStr,
  is_available: false
});
const slots = response.data;

// Créer
const newSlot = await createSlot({
  date: "2025-10-15",
  time: "09:00:00",
  application_id: "app-uuid-1",
  candidate_name: "John Doe",
  job_title: "Développeur"
});

// Mettre à jour
const updatedSlot = await updateSlot(slotId, {
  date: "2025-10-16",
  time: "10:00:00"
});

// Supprimer
await deleteSlot(slotId);
```

---

## 📝 Base de Données

### Table `interview_slots`

```sql
CREATE TABLE interview_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date VARCHAR NOT NULL,                         -- YYYY-MM-DD
    time VARCHAR NOT NULL,                         -- HH:mm:ss
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    candidate_name VARCHAR,
    job_title VARCHAR,
    status VARCHAR DEFAULT 'scheduled',            -- scheduled, completed, cancelled
    is_available BOOLEAN DEFAULT false NOT NULL,   -- true = libre, false = occupé
    location VARCHAR,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Index pour performance
CREATE INDEX idx_interview_slots_date_time ON interview_slots(date, time);
CREATE INDEX idx_interview_slots_is_available ON interview_slots(is_available);
```

---

## 📦 Livrables

### Fichiers Modifiés/Créés

1. ✅ `app/models/interview.py` - Modèle SQLAlchemy
2. ✅ `app/schemas/interview.py` - Schémas Pydantic
3. ✅ `app/services/interview.py` - Logique métier
4. ✅ `app/api/v1/endpoints/interviews.py` - Endpoints FastAPI
5. ✅ `app/db/migrations/versions/20251003_update_interview_slots.py` - Migration Alembic
6. ✅ `docs/INTERVIEW_CALENDAR_API.md` - Documentation complète

---

## 🎯 Prochaines Étapes

1. ✅ **Exécuter la migration** : `alembic upgrade head`
2. ✅ **Tester les endpoints** via Swagger UI : `/docs`
3. ✅ **Intégrer au frontend** : Remplacer les appels Supabase
4. ✅ **Déployer sur Azure** : Inclure dans le prochain déploiement

---

**Date de création** : 2025-10-03  
**Auteur** : SEEG Backend Team  
**Status** : ✅ Prêt pour production

