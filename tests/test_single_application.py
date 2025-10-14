"""Test simple pour debug"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Login candidat
login = requests.post(f"{BASE_URL}/auth/login", data={
    "username": "candidat.test.local@example.com",
    "password": "Candidat123!"
})

if login.status_code != 200:
    print(f"❌ Erreur login: {login.status_code}")
    exit(1)

token = login.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Récupérer user ID
me = requests.get(f"{BASE_URL}/users/me", headers=headers)
candidate_id = me.json().get("data", {}).get("id")

print(f"👤 Candidat ID: {candidate_id}")
print(f"📋 Job ID: 8ff8ebd9-4a8c-41a2-9e72-3ea93ab5453f")

# Candidature
app_data = {
    "candidate_id": candidate_id,
    "job_offer_id": "8ff8ebd9-4a8c-41a2-9e72-3ea93ab5453f",
    "ref_entreprise": "Société ABC",
    "ref_fullname": "Marie Dupont",
    "ref_mail": "marie.dupont@abc.com",
    "ref_contact": "+241 01 23 45 67",
    "mtp_answers": {
        "reponses_metier": ["R1", "R2", "R3"],
        "reponses_talent": ["R1", "R2"],
        "reponses_paradigme": ["R1", "R2"]
    }
}

print("\n📤 Envoi candidature...")
print(json.dumps(app_data, indent=2, ensure_ascii=False))

response = requests.post(f"{BASE_URL}/applications/", headers=headers, json=app_data)

print(f"\n📥 Réponse: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

