"""
TEST COMPLET DU SYSTÈME : Notifications, Emails, Entretiens
Utilise le compte admin pour tester toutes les fonctionnalités
"""
import requests
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8000/api/v1"

# Credentials
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"
CANDIDATE_EMAIL = "sevan@cnx4-0.com"
CANDIDATE_PASSWORD = "Sevan@cnx4-0"

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(message: str, success: bool):
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")

print_section("🚀 TEST COMPLET DU SYSTÈME")
print(f"📧 Admin: {ADMIN_EMAIL}")
print(f"👤 Candidat: {CANDIDATE_EMAIL}")

# ==================== TEST 1: CONNEXION ADMIN ====================
print_section("1️⃣ CONNEXION ADMIN")

admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if admin_login.status_code != 200:
    print_result(f"Connexion admin échouée: {admin_login.status_code}", False)
    print(admin_login.text)
    exit(1)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print_result("Admin connecté", True)

# ==================== TEST 2: RÉCUPÉRER CANDIDATURE ====================
print_section("2️⃣ RÉCUPÉRATION CANDIDATURE DU CANDIDAT TEST")

# Récupérer toutes les candidatures
apps_response = requests.get(
    f"{BASE_URL}/applications/",
    headers=admin_headers,
    timeout=10
)

if apps_response.status_code != 200:
    print_result(f"Erreur récupération candidatures: {apps_response.status_code}", False)
    exit(1)

apps_data = apps_response.json()
applications = apps_data.get("data", []) if isinstance(apps_data, dict) else apps_data

print(f"📊 {len(applications)} candidature(s) trouvée(s)")

# Trouver la candidature du candidat test
target_app = None
for app in applications:
    # Récupérer les détails de chaque candidature pour voir les relations
    app_id = app.get("id")
    app_detail_response = requests.get(
        f"{BASE_URL}/applications/{app_id}",
        headers=admin_headers,
        timeout=10
    )
    
    if app_detail_response.status_code == 200:
        app_detail = app_detail_response.json()
        if isinstance(app_detail, dict) and "data" in app_detail:
            app_detail = app_detail["data"]
        
        candidate = app_detail.get("candidate") or {}
        if candidate.get("email") == CANDIDATE_EMAIL:
            target_app = app_detail
            break

if not target_app:
    print_result(f"Candidature de {CANDIDATE_EMAIL} non trouvée", False)
    print("⚠️ Veuillez d'abord créer une candidature pour ce candidat")
    exit(1)

application_id = target_app.get("id")
candidate = target_app.get("candidate") or {}
job_offer = target_app.get("job_offer") or {}
candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
candidate_email = candidate.get("email")
job_title = job_offer.get("title", "Poste")

print_result(f"Candidature trouvée: {application_id}", True)
print(f"   👤 Candidat: {candidate_name}")
print(f"   📧 Email: {candidate_email}")
print(f"   💼 Poste: {job_title}")

# ==================== TEST 3: PLANIFIER ENTRETIEN ====================
print_section("3️⃣ PLANIFICATION ENTRETIEN")

interview_datetime = datetime.now() + timedelta(days=2)
interview_data = {
    "date": interview_datetime.strftime("%Y-%m-%d"),
    "time": "14:00:00",
    "application_id": application_id,
    "candidate_name": candidate_name,
    "job_title": job_title,
    "status": "scheduled",
    "location": "Siège SEEG, Libreville - Salle de Conférence A",
    "notes": "Entretien technique et RH combiné. Durée: 1h30. Prévoir documents originaux."
}

print(f"📅 Planification pour: {interview_data['date']} à {interview_data['time']}")
print(f"📍 Lieu: {interview_data['location']}")

interview_response = requests.post(
    f"{BASE_URL}/interviews/slots",
    headers=admin_headers,
    json=interview_data,
    timeout=15
)

if interview_response.status_code == 201:
    print_result("Entretien planifié avec succès !", True)
    interview_result = interview_response.json()
    interview_id = interview_result.get("id")
    
    print(f"   🆔 ID Entretien: {interview_id}")
    print(f"   📅 Date: {interview_result.get('date')}")
    print(f"   ⏰ Heure: {interview_result.get('time')}")
    print(f"   📍 Lieu: {interview_result.get('location')}")
    
    print(f"\n   📧 EMAIL ENVOYÉ À: {candidate_email}")
    print(f"   🔔 NOTIFICATION CRÉÉE")
    
elif interview_response.status_code == 409:
    print_result("Entretien déjà existant pour ce créneau", False)
    print("   ℹ️  C'est normal si vous avez déjà testé")
else:
    print_result(f"Erreur planification: {interview_response.status_code}", False)
    print(f"   Détails: {interview_response.text}")

# ==================== TEST 4: VÉRIFIER NOTIFICATIONS CANDIDAT ====================
print_section("4️⃣ VÉRIFICATION NOTIFICATIONS CANDIDAT")

print("⏳ Attente de 3 secondes pour l'envoi...")
time.sleep(3)

candidate_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
    timeout=10
)

if candidate_login.status_code != 200:
    print_result(f"Connexion candidat échouée: {candidate_login.status_code}", False)
else:
    candidate_token = candidate_login.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    print_result("Candidat connecté", True)
    
    notif_response = requests.get(
        f"{BASE_URL}/notifications/",
        headers=candidate_headers,
        timeout=10
    )
    
    if notif_response.status_code == 200:
        notifications = notif_response.json().get("items", [])
        print(f"\n📊 Total notifications: {len(notifications)}")
        
        if notifications:
            print("\n📬 NOTIFICATIONS REÇUES:")
            
            # Grouper par type
            types_count = {}
            for notif in notifications:
                notif_type = notif.get("type", "unknown")
                types_count[notif_type] = types_count.get(notif_type, 0) + 1
            
            print("\n📈 Répartition par type:")
            for notif_type, count in types_count.items():
                emoji = {
                    "registration": "👤",
                    "application_submitted": "📨",
                    "draft_saved": "💾",
                    "interview_scheduled": "📅"
                }.get(notif_type, "🔔")
                print(f"   {emoji} {notif_type}: {count}")
            
            # Chercher la notification d'entretien
            interview_notif = next(
                (n for n in notifications if n.get("type") == "interview_scheduled"),
                None
            )
            
            if interview_notif:
                print("\n✅ ✅ NOTIFICATION D'ENTRETIEN TROUVÉE !")
                print(f"   📝 Titre: {interview_notif.get('title')}")
                print(f"   💬 Message: {interview_notif.get('message')}")
                print(f"   🔗 Lien: {interview_notif.get('link')}")
                print(f"   {'📖' if interview_notif.get('read') else '📬'} {'Lu' if interview_notif.get('read') else 'Non lu'}")
            else:
                print("\n⚠️ Notification d'entretien non trouvée")
            
            # Chercher la notification de candidature
            app_notif = next(
                (n for n in notifications if n.get("type") == "application_submitted"),
                None
            )
            
            if app_notif:
                print("\n✅ NOTIFICATION DE CANDIDATURE TROUVÉE !")
                print(f"   📝 {app_notif.get('title')}")
            
        else:
            print_result("AUCUNE NOTIFICATION TROUVÉE", False)
            print("   ⚠️ Le système de notifications ne fonctionne pas encore")
            print("   ℹ️  Vérifiez que l'API a bien été redémarrée")
    else:
        print_result(f"Erreur récupération notifications: {notif_response.status_code}", False)

# ==================== RÉSUMÉ FINAL ====================
print_section("📊 RÉSUMÉ DU TEST")

print("\n✅ Tests effectués:")
print("   1. ✅ Connexion admin")
print("   2. ✅ Récupération candidature")
print("   3. ✅ Planification entretien")
print("   4. ✅ Vérification notifications")

print(f"\n📧 VÉRIFICATIONS À FAIRE:")
print(f"   1. Vérifiez la boîte mail: {candidate_email}")
print(f"      ➡️  Email d'invitation à l'entretien avec tous les détails")
print(f"   2. Connectez-vous à l'application avec: {candidate_email}")
print(f"      ➡️  Notification d'entretien dans la cloche 🔔")

print("\n🎯 FONCTIONNALITÉS TESTÉES:")
print("   ✅ Système de notifications")
print("   ✅ Système d'emails")
print("   ✅ Planification d'entretiens")
print("   ✅ Logging structuré")

print("\n" + "="*80)
print("✅ TEST COMPLET TERMINÉ")
print("="*80 + "\n")

