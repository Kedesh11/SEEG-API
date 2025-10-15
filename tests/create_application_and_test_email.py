"""
Script pour créer une candidature avec sevan@cnx4-0.com et tester l'email d'entretien
"""
import requests
from datetime import datetime, timedelta

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# Credentials
CANDIDATE_EMAIL = "sevan@cnx4-0.com"
CANDIDATE_PASSWORD = "Sevan@2025Test"  # Au moins 12 caractères
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(message, success=None):
    if success is True:
        print(f"✅ {message}")
    elif success is False:
        print(f"❌ {message}")
    else:
        print(f"🔄 {message}")

print_section("🚀 CRÉATION CANDIDATURE + TEST EMAIL")
print(f"📧 Email candidat: {CANDIDATE_EMAIL}")
print(f"🌐 API: {BASE_URL}")

# ÉTAPE 1: Connexion ou création du compte candidat
print_section("ÉTAPE 1: CONNEXION/CRÉATION CANDIDAT")
try:
    # Tenter la connexion
    candidate_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
        timeout=10
    )
    
    if candidate_login.status_code == 200:
        candidate_token = candidate_login.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
        candidate_id = candidate_login.json().get("user", {}).get("id")
        print_step(f"Connexion réussie - ID: {candidate_id}", True)
    elif candidate_login.status_code == 401:
        # Le compte n'existe pas ou mauvais mot de passe, tentons de le créer
        print_step("Compte non trouvé - Création...", None)
        
        signup_data = {
            "email": CANDIDATE_EMAIL,
            "password": CANDIDATE_PASSWORD,
            "first_name": "Sevan",
            "last_name": "Kedesh IKISSA",
            "phone": "+241 06 12 34 56",
            "date_of_birth": "1990-01-15",
            "sexe": "M",
            "role": "candidate",
            "candidate_status": "externe"
        }
        
        signup_response = requests.post(
            f"{BASE_URL}/auth/signup",
            json=signup_data,
            timeout=30
        )
        
        if signup_response.status_code in [200, 201]:
            print_step("✅ Compte créé avec succès !", True)
            print(f"   📧 Email de bienvenue envoyé à: {CANDIDATE_EMAIL}")
            
            # Se connecter avec le nouveau compte
            candidate_login = requests.post(
                f"{BASE_URL}/auth/login",
                data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
                timeout=10
            )
            
            if candidate_login.status_code == 200:
                candidate_token = candidate_login.json()["access_token"]
                candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
                candidate_id = candidate_login.json().get("user", {}).get("id")
                print_step(f"Connexion réussie - ID: {candidate_id}", True)
            else:
                print_step(f"Échec connexion après création: {candidate_login.status_code}", False)
                exit(1)
        else:
            print_step(f"Échec création compte: {signup_response.status_code}", False)
            print(f"Détails: {signup_response.text[:300]}")
            exit(1)
    else:
        print_step(f"Erreur inattendue: {candidate_login.status_code}", False)
        print(f"Détails: {candidate_login.text}")
        exit(1)
except Exception as e:
    print_step(f"Erreur: {str(e)}", False)
    exit(1)

# ÉTAPE 2: Récupérer une offre d'emploi disponible
print_section("ÉTAPE 2: RECHERCHE OFFRE D'EMPLOI")
try:
    jobs_response = requests.get(
        f"{BASE_URL}/public/jobs",
        params={"status": "active", "limit": 1},
        timeout=10
    )
    
    if jobs_response.status_code == 200:
        jobs_data = jobs_response.json()
        if isinstance(jobs_data, dict):
            jobs = jobs_data.get("items", jobs_data.get("data", []))
        else:
            jobs = jobs_data
        
        if not jobs:
            print_step("Aucune offre disponible", False)
            exit(1)
        
        job = jobs[0]
        job_id = job.get("id")
        job_title = job.get("title", "Poste")
        print_step(f"Offre trouvée: {job_title}", True)
        print(f"   🆔 ID: {job_id}")
    else:
        print_step(f"Erreur récupération offres: {jobs_response.status_code}", False)
        exit(1)
except Exception as e:
    print_step(f"Erreur: {str(e)}", False)
    exit(1)

# ÉTAPE 3: Soumettre la candidature
print_section("ÉTAPE 3: SOUMISSION CANDIDATURE")

application_data = {
    "job_offer_id": job_id,
    "reference_contacts": "Oui",
    "availability_start": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
    "has_been_manager": True,
    "ref_entreprise": "SEEG - Test",
    "ref_fullname": "Jean Dupont",
    "ref_mail": "jean.dupont@seeg.ga",
    "ref_contact": "+241 01 23 45 67",
    "mtp_answers": {}  # Sera ajusté selon les questions MTP
}

try:
    # Récupérer les détails de l'offre pour les questions MTP
    job_detail = requests.get(
        f"{BASE_URL}/public/jobs/{job_id}",
        timeout=10
    )
    
    if job_detail.status_code == 200:
        job_data = job_detail.json()
        questions_mtp = job_data.get("questions_mtp")
        
        if questions_mtp:
            print_step("Questions MTP détectées - Génération des réponses...", None)
            # Générer des réponses pour chaque question
            if isinstance(questions_mtp, dict):
                for key, questions in questions_mtp.items():
                    if isinstance(questions, list) and questions:
                        application_data["mtp_answers"][key] = [
                            f"Réponse test pour {key} - Question {i+1}"
                            for i in range(len(questions))
                        ]
            print(f"   📝 {len(application_data['mtp_answers'])} catégories de réponses MTP générées")
    
    # Soumettre la candidature
    print_step("Envoi de la candidature...", None)
    application_response = requests.post(
        f"{BASE_URL}/applications/",
        headers=candidate_headers,
        json=application_data,
        timeout=30
    )
    
    if application_response.status_code in [200, 201]:
        application = application_response.json()
        application_id = application.get("id")
        print_step("✅ CANDIDATURE CRÉÉE AVEC SUCCÈS !", True)
        print(f"   🆔 ID: {application_id}")
        print(f"   📧 Email de confirmation envoyé à: {CANDIDATE_EMAIL}")
        print(f"   💼 Poste: {job_title}")
    else:
        print_step(f"Échec soumission: {application_response.status_code}", False)
        print(f"Détails: {application_response.text[:500]}")
        exit(1)
except Exception as e:
    print_step(f"Erreur: {str(e)}", False)
    exit(1)

# ÉTAPE 4: Connexion admin pour planifier l'entretien
print_section("ÉTAPE 4: PLANIFICATION ENTRETIEN (EMAIL)")

try:
    admin_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    
    if admin_login.status_code == 200:
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print_step("Admin connecté", True)
    else:
        print_step(f"Échec connexion admin: {admin_login.status_code}", False)
        exit(1)
    
    # Récupérer les détails de la candidature pour le nom et le poste
    app_detail = requests.get(
        f"{BASE_URL}/applications/{application_id}",
        headers=admin_headers,
        timeout=10
    )
    
    if app_detail.status_code == 200:
        details = app_detail.json()
        candidate_name = f"{details.get('candidate', {}).get('first_name', 'Sevan')} {details.get('candidate', {}).get('last_name', 'IKISSA')}"
        job_title_full = details.get('job_offer', {}).get('title', job_title)
    else:
        candidate_name = "Sevan Kedesh IKISSA"
        job_title_full = job_title
    
    # Planifier l'entretien (dans 5 jours à 14h)
    interview_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    interview_time = "14:00:00"
    
    interview_data = {
        "application_id": application_id,
        "candidate_name": candidate_name,
        "job_title": job_title_full,
        "date": interview_date,
        "time": interview_time,
        "location": "Siège SEEG, Libreville - Salle de Conférence A",
        "notes": "Entretien technique et RH. Durée estimée: 1h30. Merci d'apporter vos documents originaux (diplômes, CV, pièce d'identité)."
    }
    
    print_step("Envoi de l'invitation à l'entretien...", None)
    interview_response = requests.post(
        f"{BASE_URL}/interviews/slots",
        headers=admin_headers,
        json=interview_data,
        timeout=30
    )
    
    if interview_response.status_code == 201:
        interview = interview_response.json()
        print_step("✅ ✅ ENTRETIEN PLANIFIÉ - EMAIL ENVOYÉ !", True)
        print(f"\n   🆔 ID Entretien: {interview.get('id')}")
        print(f"   📅 Date: {interview.get('date')}")
        print(f"   ⏰ Heure: {interview.get('time')}")
        print(f"   📍 Lieu: {interview.get('location')}")
        print(f"\n   📧 ✉️  EMAIL D'INVITATION ENVOYÉ À: {CANDIDATE_EMAIL}")
        print(f"   🔔 Notification in-app créée")
    else:
        print_step(f"Échec planification: {interview_response.status_code}", False)
        print(f"Détails: {interview_response.text[:500]}")
        # Même si ça échoue, la candidature a été créée
        print("\n⚠️ La candidature a été créée mais l'entretien n'a pas pu être planifié")
        print(f"   Vous pouvez planifier manuellement avec l'ID: {application_id}")
        
except Exception as e:
    print_step(f"Erreur: {str(e)}", False)
    print("\n⚠️ La candidature a été créée mais l'entretien n'a pas pu être planifié")

# RÉSUMÉ FINAL
print_section("📊 RÉSUMÉ")
print(f"\n✅ Candidature créée avec succès")
print(f"   📧 Email: {CANDIDATE_EMAIL}")
print(f"   🆔 ID Candidature: {application_id}")
print(f"   💼 Poste: {job_title}")
print(f"\n📧 EMAILS ENVOYÉS:")
print(f"   1. ✅ Email de confirmation de candidature")
print(f"   2. ✅ Email d'invitation à l'entretien (si planifié)")
print(f"\n💡 Vérifiez la boîte mail {CANDIDATE_EMAIL}")
print(f"   (Consultez aussi le dossier spam si nécessaire)")
print("\n" + "=" * 80 + "\n")

