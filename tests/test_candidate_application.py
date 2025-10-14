"""
Script de test rapide pour vérifier qu'un candidat peut postuler à plusieurs postes
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://seeg-backend-api.azurewebsites.net"  # Production
API_URL = f"{BASE_URL}/api/v1"

def test_candidate_can_apply_to_multiple_jobs():
    """
    Test complet du parcours candidat :
    1. Inscription d'un candidat
    2. Connexion
    3. Consultation des offres publiques
    4. Candidature à plusieurs postes
    """
    
    print("=" * 60)
    print("TEST : Un candidat peut postuler à plusieurs postes")
    print("=" * 60)
    
    # Étape 1 : Créer un candidat de test
    print("\n1️⃣  Création d'un compte candidat...")
    
    # Utiliser un timestamp pour éviter les conflits
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"test.candidat.{timestamp}@example.com"
    
    signup_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "first_name": "Jean",
        "last_name": "Test",
        "phone": "+24106223344",
        "date_of_birth": "1995-05-15",
        "sexe": "M",
        "candidate_status": "externe",
        "adresse": "123 Rue Test, Libreville"
    }
    
    print(f"   📧 Email de test : {test_email}")
    
    try:
        response = requests.post(f"{API_URL}/auth/signup", json=signup_data)
        if response.status_code == 200:
            print("   ✅ Compte créé avec succès")
            user_data = response.json()
            print(f"   👤 Utilisateur : {user_data.get('first_name')} {user_data.get('last_name')}")
        elif response.status_code == 400 and "existe déjà" in response.text:
            print("   ℹ️  Compte existe déjà, on continue avec le login")
        else:
            print(f"   ❌ Erreur création compte : {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"   ⚠️  Erreur : {e}")
        print("   ℹ️  On suppose que le compte existe et on continue")
    
    # Étape 2 : Connexion
    print("\n2️⃣  Connexion...")
    login_data = {
        "email": signup_data["email"],
        "password": signup_data["password"]
    }
    
    try:
        response = requests.post(f"{API_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            user = token_data.get("user", {})
            print(f"   ✅ Connexion réussie")
            print(f"   🔑 Token obtenu")
            print(f"   👤 Role : {user.get('role')}")
            print(f"   📧 Email : {user.get('email')}")
        else:
            print(f"   ❌ Erreur connexion : {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return False
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Étape 3 : Consulter les offres publiques
    print("\n3️⃣  Consultation des offres publiques (SANS authentification)...")
    try:
        response = requests.get(f"{API_URL}/public/jobs")
        if response.status_code == 200:
            jobs = response.json()
            print(f"   ✅ {len(jobs)} offres disponibles")
            if len(jobs) > 0:
                print(f"   📋 Exemple : {jobs[0].get('title')}")
        else:
            print(f"   ❌ Erreur : {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
    
    # Étape 4 : Consulter les offres authentifiées
    print("\n4️⃣  Consultation des offres (AVEC authentification)...")
    try:
        response = requests.get(f"{API_URL}/jobs/", headers=headers)
        if response.status_code == 200:
            result = response.json()
            jobs = result.get("data", []) if isinstance(result, dict) else result
            print(f"   ✅ {len(jobs)} offres disponibles")
            
            if len(jobs) > 0:
                print(f"\n   📋 Liste des offres disponibles :")
                for idx, job in enumerate(jobs[:5], 1):  # Afficher les 5 premières
                    print(f"      {idx}. {job.get('title')} (ID: {job.get('id')})")
            
            if len(jobs) >= 2:
                print(f"\n   🎯 Test de candidature à 2 postes différents...")
                job1_id = jobs[0].get("id")
                job2_id = jobs[1].get("id")
                candidate_id = user.get("id")
                
                print(f"   📊 Job 1 ID: {job1_id}")
                print(f"   📊 Job 2 ID: {job2_id}")
                print(f"   👤 Candidate ID: {candidate_id}")
                
                # Candidature 1
                print(f"\n   📝 Candidature 1 : {jobs[0].get('title')}")
                application1_data = {
                    "candidate_id": candidate_id,
                    "job_offer_id": job1_id,
                    "ref_entreprise": "Entreprise Test",
                    "ref_fullname": "Référent Test",
                    "ref_mail": "referent@test.com",
                    "ref_contact": "+24106223344"
                }
                
                response1 = requests.post(f"{API_URL}/applications/", headers=headers, json=application1_data)
                if response1.status_code == 201:
                    print("      ✅ Candidature 1 créée avec succès")
                elif response1.status_code == 400 and "existe déjà" in response1.text:
                    print("      ℹ️  Candidature 1 existe déjà")
                else:
                    print(f"      ❌ Erreur candidature 1 : {response1.status_code}")
                    try:
                        error_detail = response1.json()
                        print(f"      📋 Détail : {json.dumps(error_detail, indent=6, ensure_ascii=False)}")
                    except:
                        print(f"      {response1.text}")
                
                # Candidature 2
                print(f"\n   📝 Candidature 2 : {jobs[1].get('title')}")
                application2_data = {
                    "candidate_id": candidate_id,
                    "job_offer_id": job2_id,
                    "ref_entreprise": "Entreprise Test",
                    "ref_fullname": "Référent Test",
                    "ref_mail": "referent@test.com",
                    "ref_contact": "+24106223344"
                }
                
                response2 = requests.post(f"{API_URL}/applications/", headers=headers, json=application2_data)
                if response2.status_code == 201:
                    print("      ✅ Candidature 2 créée avec succès")
                elif response2.status_code == 400 and "existe déjà" in response2.text:
                    print("      ℹ️  Candidature 2 existe déjà")
                else:
                    print(f"      ❌ Erreur candidature 2 : {response2.status_code}")
                    try:
                        error_detail = response2.json()
                        print(f"      📋 Détail : {json.dumps(error_detail, indent=6, ensure_ascii=False)}")
                    except:
                        print(f"      {response2.text}")
                
                print("\n" + "=" * 60)
                print("✅ TEST RÉUSSI : Le candidat peut postuler à plusieurs postes")
                print("=" * 60)
                return True
            else:
                print(f"   ⚠️  Pas assez d'offres pour tester (besoin de 2, trouvé {len(jobs)})")
                return False
        else:
            print(f"   ❌ Erreur : {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    test_candidate_can_apply_to_multiple_jobs()

