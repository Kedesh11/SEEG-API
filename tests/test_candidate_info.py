"""
Test des nouveaux endpoints pour récupérer les informations complètes des candidats
"""
import requests

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

print("\n" + "=" * 80)
print("  🧪 TEST - INFORMATIONS COMPLÈTES CANDIDAT")
print("=" * 80)

# 1. Connexion admin
print("\n🔐 Connexion admin...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if login_response.status_code != 200:
    print(f"❌ Échec connexion: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Connecté")

# 2. Récupérer une candidature
print("\n📋 Récupération d'une candidature...")
apps_response = requests.get(
    f"{BASE_URL}/applications/",
    headers=headers,
    params={"limit": 1},
    timeout=10
)

if apps_response.status_code != 200:
    print(f"❌ Erreur: {apps_response.status_code}")
    exit(1)

apps_data = apps_response.json()
if isinstance(apps_data, dict):
    applications = apps_data.get("data", apps_data.get("items", []))
else:
    applications = apps_data

if not applications:
    print("❌ Aucune candidature trouvée")
    exit(1)

application_id = applications[0].get("id")
candidate_id = applications[0].get("candidate_id")
print(f"✅ Candidature trouvée: {application_id}")
print(f"   Candidat ID: {candidate_id}")

# 3. TEST 1: Récupérer les infos complètes via l'ID candidat
print("\n📊 TEST 1: Infos complètes via ID candidat")
print(f"   GET /candidates/{candidate_id}/complete")

candidate_info_response = requests.get(
    f"{BASE_URL}/candidates/{candidate_id}/complete",
    headers=headers,
    timeout=10
)

if candidate_info_response.status_code == 200:
    candidate_info = candidate_info_response.json()
    print("✅ Informations récupérées !")
    print(f"\n👤 UTILISATEUR:")
    print(f"   Nom: {candidate_info.get('first_name')} {candidate_info.get('last_name')}")
    print(f"   Email: {candidate_info.get('email')}")
    print(f"   Téléphone: {candidate_info.get('phone', 'N/A')}")
    print(f"   Date naissance: {candidate_info.get('date_of_birth', 'N/A')}")
    print(f"   Sexe: {candidate_info.get('sexe', 'N/A')}")
    print(f"   Statut: {candidate_info.get('candidate_status', 'N/A')}")
    
    profile = candidate_info.get('profile')
    if profile:
        print(f"\n📋 PROFIL CANDIDAT:")
        print(f"   Années d'expérience: {profile.get('years_experience', 'N/A')}")
        print(f"   Poste actuel: {profile.get('current_position', 'N/A')}")
        print(f"   Disponibilité: {profile.get('availability', 'N/A')}")
        
        skills = profile.get('skills')
        if skills and skills != "N/A":
            print(f"   Compétences: Oui ({len(skills)} caractères)")
        
        education = profile.get('education')
        if education and education != "N/A":
            print(f"   Formation: Oui ({len(education)} caractères)")
    else:
        print(f"\n📋 PROFIL CANDIDAT: Pas encore rempli")
    
    print(f"\n📊 STATISTIQUES:")
    print(f"   Total candidatures: {candidate_info.get('total_applications', 0)}")
    print(f"   En attente: {candidate_info.get('pending_applications', 0)}")
    print(f"   Acceptées: {candidate_info.get('accepted_applications', 0)}")
    print(f"   Rejetées: {candidate_info.get('rejected_applications', 0)}")
else:
    print(f"❌ Échec: {candidate_info_response.status_code}")
    print(f"   Détails: {candidate_info_response.text[:300]}")

# 4. TEST 2: Récupérer les infos complètes via l'ID de candidature
print("\n📊 TEST 2: Infos complètes via ID candidature")
print(f"   GET /applications/{application_id}/candidate-info")

candidate_from_app_response = requests.get(
    f"{BASE_URL}/applications/{application_id}/candidate-info",
    headers=headers,
    timeout=10
)

if candidate_from_app_response.status_code == 200:
    print("✅ Informations récupérées via candidature !")
    candidate_data = candidate_from_app_response.json()
    print(f"   Candidat: {candidate_data.get('first_name')} {candidate_data.get('last_name')}")
    print(f"   Email: {candidate_data.get('email')}")
    print(f"   Total candidatures: {candidate_data.get('total_applications', 0)}")
else:
    print(f"❌ Échec: {candidate_from_app_response.status_code}")
    print(f"   Détails: {candidate_from_app_response.text[:300]}")

print("\n" + "=" * 80)
print("✅ TESTS TERMINÉS")
print("=" * 80)
print("\n💡 Ces endpoints sont maintenant disponibles pour:")
print("   - Les admins")
print("   - Les recruteurs")
print("\nUtilisation:")
print("   GET /api/v1/candidates/{candidate_id}/complete")
print("   GET /api/v1/applications/{application_id}/candidate-info")
print("\n" + "=" * 80 + "\n")

