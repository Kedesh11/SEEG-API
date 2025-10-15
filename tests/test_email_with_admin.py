"""
Test simplifié : Utiliser l'admin pour envoyer directement un email d'entretien à sevan@cnx4-0.com
"""
import requests
from datetime import datetime, timedelta

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"
TARGET_EMAIL = "sevan@cnx4-0.com"

print("\n" + "=" * 80)
print("  📧 TEST EMAIL D'INVITATION ENTRETIEN")
print("=" * 80)
print(f"🎯 Destinataire: {TARGET_EMAIL}")
print(f"🌐 API: {BASE_URL}")

# ÉTAPE 1: Connexion admin
print("\n🔐 Connexion admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if admin_login.status_code != 200:
    print(f"❌ Échec connexion: {admin_login.status_code}")
    exit(1)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print("✅ Connecté")

# ÉTAPE 2: Trouver une candidature existante (n'importe laquelle)
print("\n📋 Recherche d'une candidature...")
apps_response = requests.get(
    f"{BASE_URL}/applications/",
    headers=admin_headers,
    params={"limit": 1},
    timeout=10
)

if apps_response.status_code != 200:
    print(f"❌ Erreur: {apps_response.status_code}")
    exit(1)

apps_data = apps_response.json()
if isinstance(apps_data, dict):
    applications = apps_data.get("items", apps_data.get("data", []))
else:
    applications = apps_data

if not applications:
    print("❌ Aucune candidature trouvée")
    exit(1)

application_id = applications[0].get("id")
print(f"✅ Candidature trouvée: {application_id}")

# ÉTAPE 3: Planifier un entretien (= envoi automatique d'email)
print(f"\n📅 Planification entretien pour {TARGET_EMAIL}...")

interview_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
interview_time = "14:30:00"

interview_data = {
    "application_id": application_id,
    "candidate_name": "Sevan Kedesh IKISSA",
    "job_title": "Test d'envoi d'email",
    "date": interview_date,
    "time": interview_time,
    "location": "Siège SEEG, Libreville - Salle de Conférence A",
    "notes": "Entretien technique et RH. Durée: 1h30. Documents requis: CV original, diplômes, pièce d'identité."
}

interview_response = requests.post(
    f"{BASE_URL}/interviews/slots",
    headers=admin_headers,
    json=interview_data,
    timeout=30
)

if interview_response.status_code == 201:
    interview = interview_response.json()
    print("✅ ✅ ENTRETIEN PLANIFIÉ - EMAIL ENVOYÉ !")
    print(f"\n🆔 ID Entretien: {interview.get('id')}")
    print(f"📧 Email envoyé à: {TARGET_EMAIL}")
    print(f"📅 Date: {interview_date}")
    print(f"⏰ Heure: {interview_time}")
    print(f"📍 Lieu: Siège SEEG, Libreville")
    print(f"\n💡 Vérifiez la boîte mail {TARGET_EMAIL}")
    print("   (Consultez aussi le dossier spam)")
else:
    print(f"❌ Échec: {interview_response.status_code}")
    print(f"Détails: {interview_response.text[:500]}")

print("\n" + "=" * 80 + "\n")

