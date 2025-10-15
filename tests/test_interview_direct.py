"""
Test direct de planification d'entretien avec l'ID de candidature connu
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

# ID de la candidature créée précédemment
APPLICATION_ID = "d9695bfd-cb01-471e-aa2e-abc7a09a2b0c"

print("="*80)
print("  📅 TEST DIRECT PLANIFICATION ENTRETIEN")
print("="*80)

# Connexion admin
print("\n🔐 Connexion admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if admin_login.status_code != 200:
    print(f"❌ Erreur: {admin_login.status_code} - {admin_login.text}")
    exit(1)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print("✅ Admin connecté")

# Récupérer les détails de la candidature
print(f"\n📋 Récupération candidature {APPLICATION_ID}...")
app_detail_response = requests.get(
    f"{BASE_URL}/applications/{APPLICATION_ID}",
    headers=admin_headers,
    timeout=10
)

if app_detail_response.status_code == 200:
    app_detail = app_detail_response.json()
    
    # Extraire les données
    if isinstance(app_detail, dict) and "data" in app_detail:
        app_detail = app_detail["data"]
    
    candidate = app_detail.get("candidate") or {}
    job_offer = app_detail.get("job_offer") or {}
    
    candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or "Sevan Kedesh IKISSA PENDY"
    candidate_email_from_app = candidate.get("email") or CANDIDATE_EMAIL
    job_title = job_offer.get("title") or "Chef de Projet IT Senior"
    
    print(f"✅ Candidature trouvée:")
    print(f"   👤 {candidate_name}")
    print(f"   📧 {candidate_email_from_app}")
    print(f"   💼 {job_title}")
else:
    print(f"⚠️ Erreur récupération candidature: {app_detail_response.status_code}")
    # Utiliser les valeurs par défaut
    candidate_name = "Sevan Kedesh IKISSA PENDY"
    candidate_email_from_app = CANDIDATE_EMAIL
    job_title = "Chef de Projet IT Senior"

# Planifier l'entretien
print("\n📅 Planification entretien...")
interview_datetime = datetime.now() + timedelta(days=3)
interview_data = {
    "date": interview_datetime.strftime("%Y-%m-%d"),
    "time": "10:00:00",
    "application_id": APPLICATION_ID,
    "candidate_name": candidate_name,
    "job_title": job_title,
    "status": "scheduled",
    "location": "Siège SEEG, Libreville - Salle de Conférence A",
    "notes": "Entretien technique et RH. Durée: 1h30. Documents originaux requis."
}

print(f"   📅 {interview_data['date']} à {interview_data['time']}")
print(f"   👤 Pour: {candidate_name}")
print(f"   📍 Lieu: {interview_data['location']}")

interview_response = requests.post(
    f"{BASE_URL}/interviews/slots",
    headers=admin_headers,
    json=interview_data,
    timeout=15
)

print(f"\n📤 Réponse: {interview_response.status_code}")

if interview_response.status_code == 201:
    print(f"\n✅ ✅ ENTRETIEN PLANIFIÉ AVEC SUCCÈS !")
    result = interview_response.json()
    
    print(f"\n   🆔 ID Entretien: {result.get('id')}")
    print(f"   📅 Date: {result.get('date')}")
    print(f"   ⏰ Heure: {result.get('time')}")
    print(f"   📍 Lieu: {result.get('location')}")
    print(f"   📝 Statut: {result.get('status')}")
    
    print(f"\n📧 EMAIL D'INVITATION ENVOYÉ À: {candidate_email_from_app}")
    print(f"   ➡️  Vérifiez la boîte mail")
    
    # Vérifier les notifications
    import time
    print(f"\n⏳ Attente 3 secondes...")
    time.sleep(3)
    
    print(f"\n🔔 Vérification notifications candidat...")
    candidate_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
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
            notif_data = notif_response.json()
            # L'API retourne "notifications" et non "items"
            notifications = notif_data.get("notifications", notif_data.get("items", []))
            total = notif_data.get("total", len(notifications))
            print(f"✅ {total} notification(s) totale(s)")
            
            if notifications:
                print(f"\n📬 Dernières notifications:")
                for i, notif in enumerate(notifications[:5], 1):
                    print(f"\n   {i}. {notif.get('title')}")
                    print(f"      Type: {notif.get('type')}")
                    print(f"      Message: {notif.get('message')[:100]}...")
                
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
        else:
            print(f"⚠️ Erreur notifications: {notif_response.status_code}")
    else:
        print(f"⚠️ Connexion candidat échouée: {candidate_login.status_code}")
    
else:
    print(f"\n❌ ERREUR PLANIFICATION: {interview_response.status_code}")
    print(f"\n{interview_response.text}")

print("\n" + "="*80)
print("✅ TEST TERMINÉ")
print("="*80 + "\n")

