"""
Test des routes POST des candidatures en local
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_applications_post_local():
    """Test complet des routes POST de candidatures en local"""
    
    print_section("TEST ROUTES POST CANDIDATURES EN LOCAL")
    print(f"URL de base: {BASE_URL}")
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Login avec un compte admin
    print_section("1. LOGIN ADMIN")
    CANDIDATE_EMAIL = "sevankedesh11@gmail.com"
    CANDIDATE_PASSWORD = "Sevan@Seeg"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
            timeout=10
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "access_token" in data["data"]:
                token = data["data"]["access_token"]
            elif "access_token" in data:
                token = data["access_token"]
            else:
                print(f"[ERREUR] Format de reponse inattendu: {data.keys()}")
                return
            
            print(f"[OK] Token obtenu: {token[:50]}...")
        else:
            print(f"[ERREUR] Login echoue: {response.text}")
            return
    except Exception as e:
        print(f"[ERREUR] Exception login: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Récupérer les offres d'emploi disponibles
    print_section("2. RECUPERER OFFRES D'EMPLOI")
    job_offer_id = None
    try:
        response = requests.get(
            f"{BASE_URL}/jobs/",
            headers=headers,
            params={"limit": 1},
            timeout=10
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            jobs_list = response.json()
            # GET /jobs/ retourne List[JobOfferResponse] directement
            
            if isinstance(jobs_list, list):
                print(f"[OK] Liste d'offres recue: {len(jobs_list)} offre(s)")
                if jobs_list:
                    job_offer_id = jobs_list[0].get("id")
                    print(f"[OK] Offre trouvee: {job_offer_id}")
                    print(f"  - Titre: {jobs_list[0].get('title', 'N/A')}")
                else:
                    print(f"[WARN] Aucune offre disponible en base")
            else:
                print(f"[ERREUR] Format inattendu: {type(jobs_list).__name__}")
                print(f"Data: {json.dumps(jobs_list, indent=2)[:300]}")
        else:
            print(f"[ERREUR] Erreur: {response.text[:200]}")
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    if not job_offer_id:
        print("\n[ERREUR] Impossible de continuer sans offre d'emploi")
        return
    
    # 3. Test création brouillon (POST /applications/drafts)
    print_section("3. TEST CREATION BROUILLON (POST /applications/drafts)")
    try:
        draft_payload = {
            "job_offer_id": job_offer_id,
            "form_data": {
                "step": 1,
                "values": {
                    "firstname": "Test",
                    "lastname": "Brouillon Local",
                    "email": CANDIDATE_EMAIL
                }
            },
            "ui_state": {
                "currentStep": 2,
                "completedSteps": [1]
            }
        }
        
        print(f"Payload: {json.dumps(draft_payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/applications/drafts/by-offer",
            json=draft_payload,
            headers=headers,
            timeout=10
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Brouillon cree avec succes")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Test récupération du brouillon
            print("\n  -> Verification recuperation brouillon")
            response_get = requests.get(
                f"{BASE_URL}/applications/drafts/by-offer",
                params={"job_offer_id": job_offer_id},
                headers=headers,
                timeout=10
            )
            print(f"     Statut GET: {response_get.status_code}")
            
            if response_get.status_code == 200:
                draft_data = response_get.json()
                print(f"     [OK] Brouillon recupere")
                if "data" in draft_data and draft_data["data"]:
                    print(f"     - Form data present: {'form_data' in draft_data['data']}")
            else:
                print(f"     [ERREUR] GET brouillon echoue")
                try:
                    error_detail = response_get.json()
                    print(f"     Detail: {error_detail}")
                except:
                    print(f"     Response text: {response_get.text}")
        else:
            print(f"[ERREUR] Statut {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Test création candidature
    print_section("4. TEST CREATION CANDIDATURE (POST /applications/)")
    admin_token = token  # Utiliser le token de l'étape 1
    admin_headers = headers
    
    try:
        # Récupérer un candidat
        response_users = requests.get(
            f"{BASE_URL}/users/",
            headers=admin_headers,
            params={"limit": 10},
            timeout=10
        )
        
        candidate_id = None
        if response_users.status_code == 200:
            users_data = response_users.json()
            if "data" in users_data:
                for user in users_data["data"]:
                    if user.get("role") == "candidate":
                        candidate_id = user.get("id")
                        print(f"Candidat trouve: {user.get('email', 'N/A')}")
                        break
        
        if candidate_id and job_offer_id:
            application_payload = {
                "candidate_id": candidate_id,
                "job_offer_id": job_offer_id,
                "reference_contacts": "Test Contact Local (+241 01 02 03 04)",
                "has_been_manager": False,
                "ref_entreprise": "Entreprise Test Local",
                "ref_fullname": "Jean Test Local",
                "ref_mail": "jean.test.local@example.com",
                "ref_contact": "+241 01 02 03 04",
                "mtp_answers": {
                    "reponses_metier": [
                        "Réponse test métier 1",
                        "Réponse test métier 2",
                        "Réponse test métier 3"
                    ],
                    "reponses_talent": [
                        "Réponse test talent 1",
                        "Réponse test talent 2"
                    ],
                    "reponses_paradigme": [
                        "Réponse test paradigme 1",
                        "Réponse test paradigme 2"
                    ]
                }
            }
            
            print(f"Payload: {json.dumps(application_payload, indent=2)[:200]}...")
            
            response = requests.post(
                f"{BASE_URL}/applications/",
                json=application_payload,
                headers=admin_headers,
                timeout=10
            )
            print(f"Statut: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                print(f"[OK] Candidature creee avec succes")
                if "data" in data:
                    new_app = data["data"]
                    print(f"  - Nouvelle candidature ID: {new_app.get('id')}")
                    print(f"  - Status: {new_app.get('status', 'N/A')}")
            else:
                print(f"[ERREUR] Statut {response.status_code}")
                print(f"Response: {response.text[:500]}")
        else:
            print(f"[WARN] Candidat ou offre manquant")
            print(f"  - Candidat ID: {candidate_id}")
            print(f"  - Offre ID: {job_offer_id}")
    except Exception as e:
        print(f"[ERREUR] Exception creation candidature: {e}")
        import traceback
        traceback.print_exc()
    
    print_section("RESUME DES TESTS")
    print("[OK] Tests termines")
    print("Verifiez les sections ci-dessus pour voir les eventuelles erreurs")

if __name__ == "__main__":
    test_applications_post_local()

