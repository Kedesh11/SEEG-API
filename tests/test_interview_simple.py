"""
Test simplifié de planification d'entretien
"""
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

# Admin
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

# Candidat
CANDIDATE_EMAIL = "sevan@cnx4-0.com"
CANDIDATE_PASSWORD = "Sevan@cnx4-0"

print("="*80)
print("  📅 TEST PLANIFICATION ENTRETIEN SIMPLIFIÉ")
print("="*80)

# Connexion admin
print("\n🔐 Connexion admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if admin_login.status_code != 200:
    print(f"❌ Erreur: {admin_login.status_code}")
    print(admin_login.text)
    exit(1)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print("✅ Admin connecté")

# Récupérer les candidatures
print("\n📋 Récupération candidatures...")
apps_response = requests.get(
    f"{BASE_URL}/applications/",
    headers=admin_headers,
    timeout=10
)

if apps_response.status_code != 200:
    print(f"❌ Erreur: {apps_response.status_code}")
    exit(1)

apps_data = apps_response.json()
applications = apps_data.get("data", []) if isinstance(apps_data, dict) else apps_data

print(f"✅ {len(applications)} candidature(s)")

# Afficher toutes les candidatures
print("\n📋 Liste des candidatures:")
for i, app in enumerate(applications[:5], 1):
    app_id = app.get("id")
    candidate = app.get("candidate") or {}
    job_offer = app.get("job_offer") or {}
    
    candidate_email = candidate.get("email", "N/A")
    candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or "N/A"
    job_title = job_offer.get("title", "N/A")
    
    print(f"\n   {i}. ID: {app_id}")
    print(f"      👤 {candidate_name} ({candidate_email})")
    print(f"      💼 {job_title}")

# Trouver la candidature du candidat test
target_app = None
for app in applications:
    candidate = app.get("candidate") or {}
    if candidate.get("email") == CANDIDATE_EMAIL:
        target_app = app
        break

if not target_app and applications:
    print(f"\n⚠️ Candidature de {CANDIDATE_EMAIL} non trouvée")
    print("   Utilisation de la première candidature disponible")
    target_app = applications[0]

if not target_app:
    print("\n❌ Aucune candidature disponible")
    exit(1)

application_id = target_app.get("id")
candidate = target_app.get("candidate") or {}
job_offer = target_app.get("job_offer") or {}

candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or "Candidat"
candidate_email = candidate.get("email", "unknown@example.com")
job_title = job_offer.get("title", "Poste")

print(f"\n✅ Candidature sélectionnée:")
print(f"   🆔 {application_id}")
print(f"   👤 {candidate_name}")
print(f"   📧 {candidate_email}")
print(f"   💼 {job_title}")

# Planifier l'entretien
print("\n📅 Planification entretien...")
interview_datetime = datetime.now() + timedelta(days=2)
interview_data = {
    "date": interview_datetime.strftime("%Y-%m-%d"),
    "time": "14:30:00",
    "application_id": application_id,
    "candidate_name": candidate_name,
    "job_title": job_title,
    "status": "scheduled",
    "location": "Siège SEEG, Libreville - Salle de Conférence A",
    "notes": "Entretien technique et comportemental. Durée: 1h30. Prévoir documents originaux."
}

print(f"   📅 {interview_data['date']} à {interview_data['time']}")
print(f"   📍 {interview_data['location']}")

interview_response = requests.post(
    f"{BASE_URL}/interviews/slots",
    headers=admin_headers,
    json=interview_data,
    timeout=15
)

if interview_response.status_code == 201:
    print(f"\n✅ ✅ ENTRETIEN PLANIFIÉ !")
    result = interview_response.json()
    
    print(f"\n🎯 Détails:")
    print(f"   🆔 ID: {result.get('id')}")
    print(f"   📅 Date: {result.get('date')}")
    print(f"   ⏰ Heure: {result.get('time')}")
    print(f"   📍 Lieu: {result.get('location')}")
    
    print(f"\n📧 EMAIL ENVOYÉ À: {candidate_email}")
    print(f"   ➡️  Vérifiez la boîte mail du candidat")
    
    print(f"\n🔔 NOTIFICATION CRÉÉE")
    print(f"   ➡️  Le candidat doit voir une notification dans l'application")
    
    # Vérifier les notifications du candidat
    import time
    time.sleep(3)
    
    print(f"\n🔍 Vérification notifications candidat...")
    candidate_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": candidate_email, "password": CANDIDATE_PASSWORD},
        timeout=10
    )
    
    if candidate_login.status_code == 200:
        candidate_token = candidate_login.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
        
        notif_response = requests.get(
            f"{BASE_URL}/notifications/",
            headers=candidate_headers,
            timeout=10
        )
        
        if notif_response.status_code == 200:
            notifications = notif_response.json().get("items", [])
            print(f"✅ {len(notifications)} notification(s)")
            
            interview_notif = next(
                (n for n in notifications if n.get("type") == "interview_scheduled"),
                None
            )
            
            if interview_notif:
                print(f"\n✅ ✅ NOTIFICATION D'ENTRETIEN TROUVÉE !")
                print(f"   📝 {interview_notif.get('title')}")
                print(f"   💬 {interview_notif.get('message')}")
            else:
                print(f"\n⚠️ Notification d'entretien non trouvée")
                if notifications:
                    print(f"\n   Types présents:")
                    for n in notifications:
                        print(f"      - {n.get('type')}")
        else:
            print(f"⚠️ Erreur récupération notifications: {notif_response.status_code}")
    else:
        print(f"⚠️ Impossible de se connecter en tant que candidat")

else:
    print(f"\n❌ ERREUR: {interview_response.status_code}")
    print(interview_response.text)

print("\n" + "="*80)
print("✅ TEST TERMINÉ")
print(f"📧 Vérifiez {candidate_email} pour l'email d'invitation")
print("="*80 + "\n")

