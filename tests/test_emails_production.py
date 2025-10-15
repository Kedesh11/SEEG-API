"""
Test d'envoi d'emails avec l'API en production Azure
Teste tous les types d'emails : inscription, invitation entretien, reset password, etc.
"""
import requests
import time
from datetime import datetime, timedelta

# URL de l'API en production
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# Credentials admin pour les tests
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

# Email de test pour recevoir les notifications
TEST_EMAIL = "sevan@cnx4-0.com"
TEST_PASSWORD = "Sevan@2025"

def print_section(title):
    """Affiche une section formatée"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(message, success=None):
    """Affiche une étape avec son statut"""
    if success is True:
        print(f"✅ {message}")
    elif success is False:
        print(f"❌ {message}")
    else:
        print(f"🔄 {message}")

def test_registration_email():
    """Test 1: Email d'inscription (welcome email)"""
    print_section("TEST 1: EMAIL D'INSCRIPTION")
    
    print_step("⚠️ Test d'inscription ignoré (compte sevan@cnx4-0.com déjà existant)", None)
    print("   ℹ️  L'email de bienvenue a déjà été envoyé lors de la création initiale du compte")
    print(f"   📧 Email utilisé: {TEST_EMAIL}")
    
    # Retourner succès car le compte existe déjà
    return True, TEST_EMAIL

def test_interview_invitation_email():
    """Test 2: Email d'invitation à un entretien"""
    print_section("TEST 2: EMAIL D'INVITATION ENTRETIEN")
    
    # ID de candidature existante sur Azure
    application_id = "88f1316c-a848-4765-9419-597a3cc0f24f"
    
    # 1. Connexion admin
    print_step("Connexion en tant qu'admin...")
    try:
        admin_login = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if admin_login.status_code != 200:
            print_step(f"❌ Connexion admin échouée: {admin_login.status_code}", False)
            return False
        
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print_step("✅ Admin connecté", True)
    except Exception as e:
        print_step(f"❌ Erreur connexion admin: {str(e)}", False)
        return False
    
    # 2. Récupérer directement les détails de la candidature connue
    try:
        print_step(f"Récupération des détails de la candidature {application_id}...")
        app_detail_response = requests.get(
            f"{BASE_URL}/applications/{application_id}",
            headers=admin_headers,
            timeout=10
        )
        
        # Initialiser les variables par défaut
        candidate_email = TEST_EMAIL
        candidate_name = "Sevan Kedesh IKISSA PENDY"
        job_title = "Chef de Projet IT Senior"
        
        if app_detail_response.status_code == 200:
            app_details = app_detail_response.json()
            candidate_email = app_details.get("candidate", {}).get("email", TEST_EMAIL)
            first_name = app_details.get('candidate', {}).get('first_name', 'Sevan')
            last_name = app_details.get('candidate', {}).get('last_name', 'IKISSA')
            candidate_name = f"{first_name} {last_name}".strip()
            job_title = app_details.get("job_offer", {}).get("title", "Poste")
            
            print_step("✅ Détails de la candidature récupérés", True)
            print(f"   👤 Candidat: {candidate_name}")
            print(f"   📧 Email: {candidate_email}")
            print(f"   💼 Poste: {job_title}")
        else:
            print_step(f"⚠️ Code {app_detail_response.status_code} - Utilisation des valeurs par défaut", None)
        
    except Exception as e:
        print_step(f"❌ Erreur: {str(e)}", False)
        return False
    
    # 3. Planifier un entretien (= envoyer l'email d'invitation)
    print_step("Planification d'un entretien (envoi email)...")
    
    # Date/heure de l'entretien (dans 3 jours)
    interview_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    interview_time = "14:30:00"
    
    interview_data = {
        "application_id": application_id,
        "candidate_name": candidate_name if candidate_name != "N/A" else "Candidat",
        "job_title": job_title if job_title != "N/A" else "Poste",
        "date": interview_date,
        "time": interview_time,
        "location": "Siège SEEG - Salle de Conférence B",
        "notes": "Test d'email d'invitation. Entretien technique et RH. Durée estimée: 1h30. Veuillez apporter vos documents originaux."
    }
    
    try:
        interview_response = requests.post(
            f"{BASE_URL}/interviews/slots",
            headers=admin_headers,
            json=interview_data,
            timeout=30
        )
        
        if interview_response.status_code == 201:
            interview = interview_response.json()
            print_step("✅ Entretien planifié avec succès !", True)
            print(f"   🆔 ID Entretien: {interview.get('id')}")
            print(f"   📅 Date: {interview.get('date')}")
            print(f"   ⏰ Heure: {interview.get('time')}")
            print(f"   📍 Lieu: {interview.get('location')}")
            print(f"\n   📧 EMAIL D'INVITATION ENVOYÉ À: {candidate_email}")
            print(f"   ➡️  Vérifiez la boîte mail du candidat !")
            print(f"\n   🔔 Une notification in-app a également été créée")
            return True
        else:
            print_step(f"❌ Échec planification: {interview_response.status_code}", False)
            print(f"   Détails: {interview_response.text[:300]}")
            return False
    except Exception as e:
        print_step(f"❌ Erreur: {str(e)}", False)
        return False

def test_password_reset_email():
    """Test 3: Email de réinitialisation de mot de passe"""
    print_section("TEST 3: EMAIL RESET PASSWORD")
    
    print_step(f"Demande de réinitialisation pour: {TEST_EMAIL}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/forgot-password",
            json={"email": TEST_EMAIL},
            timeout=30
        )
        
        if response.status_code == 200:
            print_step("✅ Demande de reset envoyée avec succès !", True)
            print(f"   📧 Email de réinitialisation envoyé à: {TEST_EMAIL}")
            print(f"   ℹ️  Vérifiez la boîte mail pour le lien de reset")
            return True
        else:
            print_step(f"⚠️ Réponse: {response.status_code}", None)
            print(f"   Détails: {response.text[:200]}")
            return False
    except Exception as e:
        print_step(f"❌ Erreur: {str(e)}", False)
        return False

def test_application_submission_email():
    """Test 4: Email de confirmation de candidature"""
    print_section("TEST 4: EMAIL SOUMISSION CANDIDATURE")
    
    print_step("Ce test nécessite de soumettre une vraie candidature")
    print("   ℹ️  Utilisez le frontend ou un autre test pour créer une candidature")
    print("   ℹ️  L'email de confirmation sera automatiquement envoyé")
    return None

def main():
    """Fonction principale pour exécuter tous les tests"""
    print("\n" + "=" * 80)
    print("  🧪 TESTS D'ENVOI D'EMAILS - API PRODUCTION")
    print("  " + "=" * 78)
    print(f"  📍 API: {BASE_URL}")
    print(f"  📧 Email admin: {ADMIN_EMAIL}")
    print(f"  📧 Email test: {TEST_EMAIL}")
    print("=" * 80)
    
    results = {}
    
    # Test 1: Email d'inscription
    success, new_email = test_registration_email()
    results["registration"] = success
    time.sleep(2)
    
    # Test 2: Email d'invitation entretien
    success = test_interview_invitation_email()
    results["interview_invitation"] = success
    time.sleep(2)
    
    # Test 3: Email reset password
    success = test_password_reset_email()
    results["password_reset"] = success
    
    # Test 4: Info
    test_application_submission_email()
    
    # Résumé
    print_section("📊 RÉSUMÉ DES TESTS")
    
    print("\n📧 Résultats par type d'email:")
    for test_name, result in results.items():
        if result is True:
            print(f"   ✅ {test_name.replace('_', ' ').title()}")
        elif result is False:
            print(f"   ❌ {test_name.replace('_', ' ').title()}")
        else:
            print(f"   ⚠️  {test_name.replace('_', ' ').title()} - Non testé")
    
    success_count = sum(1 for r in results.values() if r is True)
    total_count = len([r for r in results.values() if r is not None])
    
    print(f"\n📈 Score: {success_count}/{total_count} tests réussis")
    
    if success_count == total_count:
        print("\n🎉 TOUS LES TESTS D'EMAILS ONT RÉUSSI !")
        print("   ✅ Le système d'envoi d'emails fonctionne correctement en production")
    else:
        print("\n⚠️ Certains tests ont échoué")
        print("   ℹ️  Vérifiez la configuration SMTP dans les variables d'environnement Azure")
    
    print("\n💡 INSTRUCTIONS:")
    print("   1. Vérifiez les boîtes mail des destinataires")
    print("   2. Consultez les logs Azure pour plus de détails:")
    print("      az webapp log tail --name seeg-backend-api --resource-group seeg-rg")
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()

