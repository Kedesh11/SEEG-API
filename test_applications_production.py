"""
Test complet des candidatures en production Azure
"""
import requests
import json
from datetime import datetime
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_applications():
    """Test complet des routes de candidatures"""
    
    # Identifiants pour les tests
    ADMIN_EMAIL = "sevankedesh11@gmail.com"
    ADMIN_PASSWORD = "Sevan@Seeg"
    
    print_section("TEST CANDIDATURES EN PRODUCTION")
    print(f"URL de base: {BASE_URL}")
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Login admin
    print_section("1. LOGIN ADMIN")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Gérer les deux formats de réponse
            if "data" in data and "access_token" in data["data"]:
                token = data["data"]["access_token"]
            elif "access_token" in data:
                token = data["access_token"]
            else:
                print(f"[ERREUR] Format de réponse inattendu: {data}")
                return
            
            print(f"[OK] Token obtenu: {token[:50]}...")
        else:
            print(f"[ERREUR] Erreur login: {response.text}")
            return
    except Exception as e:
        print(f"[ERREUR] Exception login: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Lister les candidatures
    print_section("2. LISTER LES CANDIDATURES (GET /applications/)")
    application_id = None
    try:
        response = requests.get(
            f"{BASE_URL}/applications/",
            headers=headers,
            timeout=30
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Reponse recue")
            print(f"Structure: {json.dumps({k: type(v).__name__ for k, v in data.items()}, indent=2)}")
            
            if "data" in data:
                applications = data.get("data", [])
                total = data.get("total", 0)
                print(f"Nombre de candidatures: {len(applications)}/{total}")
                
                if applications:
                    print(f"\nPremiere candidature:")
                    first_app = applications[0]
                    print(f"  - ID: {first_app.get('id', 'N/A')}")
                    print(f"  - Status: {first_app.get('status', 'N/A')}")
                    print(f"  - Candidate ID: {first_app.get('candidate_id', 'N/A')}")
                    print(f"  - Job Offer ID: {first_app.get('job_offer_id', 'N/A')}")
                    print(f"  - Created: {first_app.get('created_at', 'N/A')}")
                    
                    application_id = first_app.get('id')  # Stocker l'ID pour les tests suivants
            else:
                print(f"[WARN] Pas de cle 'data' dans la reponse: {list(data.keys())}")
        else:
            print(f"[ERREUR] Erreur: {response.text[:500]}")
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Récupérer une candidature spécifique
    if application_id:
        print_section(f"3. RECUPERER CANDIDATURE SPECIFIQUE (GET /applications/{application_id})")
        try:
            response = requests.get(
                f"{BASE_URL}/applications/{application_id}",
                headers=headers,
                timeout=30
            )
            print(f"Statut: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Candidature recuperee")
                
                if "data" in data:
                    app_data = data["data"]
                    print(f"  - ID: {app_data.get('id', 'N/A')}")
                    print(f"  - Status: {app_data.get('status', 'N/A')}")
                    print(f"  - Has candidate relation: {'candidate' in app_data}")
                    print(f"  - Has job_offer relation: {'job_offer' in app_data}")
                    
                    if 'candidate' in app_data:
                        candidate = app_data['candidate']
                        print(f"  - Candidate: {candidate.get('first_name', '')} {candidate.get('last_name', '')}")
                    
                    if 'job_offer' in app_data:
                        job = app_data['job_offer']
                        print(f"  - Job: {job.get('title', 'N/A')}")
            else:
                print(f"[ERREUR] Erreur: {response.text[:500]}")
        except Exception as e:
            print(f"[ERREUR] Exception: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. Test de création (si on veut)
    print_section("4. TEST STATISTIQUES")
    try:
        response = requests.get(
            f"{BASE_URL}/applications/stats/overview",
            headers=headers,
            timeout=30
        )
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Statistiques recuperees")
            if "data" in data:
                stats = data["data"]
                print(f"Statistiques: {json.dumps(stats, indent=2)}")
        else:
            print(f"[WARN] Erreur stats: {response.text[:200]}")
    except Exception as e:
        print(f"[WARN] Exception stats: {e}")
    
    # 5. Test création de candidature (POST /applications/)
    print_section("5. TEST CREATION CANDIDATURE (POST /applications/)")
    try:
        # Récupérer un candidat et une offre pour le test
        response_users = requests.get(f"{BASE_URL}/users/", headers=headers, timeout=30)
        response_jobs = requests.get(f"{BASE_URL}/jobs/", headers=headers, timeout=30)
        
        if response_users.status_code == 200 and response_jobs.status_code == 200:
            users_data = response_users.json()
            jobs_data = response_jobs.json()
            
            # Trouver un candidat
            candidate_id = None
            if "data" in users_data:
                for user in users_data["data"]:
                    if user.get("role") == "candidate":
                        candidate_id = user.get("id")
                        break
            
            # Trouver une offre - essayer différents formats de réponse
            job_offer_id = None
            if "data" in jobs_data:
                jobs_list = jobs_data["data"]
                if isinstance(jobs_list, list) and jobs_list:
                    job_offer_id = jobs_list[0].get("id")
            
            # Si pas d'offre, utiliser celle d'une candidature existante
            if not job_offer_id and application_id:
                try:
                    app_response = requests.get(f"{BASE_URL}/applications/{application_id}", headers=headers, timeout=30)
                    if app_response.status_code == 200:
                        app_data = app_response.json().get("data", {})
                        job_offer_id = app_data.get("job_offer_id")
                        print(f"[INFO] Utilisation offre existante: {job_offer_id}")
                except:
                    pass
            
            if candidate_id and job_offer_id:
                print(f"Candidat ID: {candidate_id}")
                print(f"Offre ID: {job_offer_id}")
                
                # Créer une candidature de test
                application_payload = {
                    "candidate_id": candidate_id,
                    "job_offer_id": job_offer_id,
                    "reference_contacts": "Test Contact (+241 01 02 03 04)",
                    "has_been_manager": False,
                    "ref_entreprise": "Entreprise Test",
                    "ref_fullname": "Jean Test",
                    "ref_mail": "jean.test@example.com",
                    "ref_contact": "+241 01 02 03 04"
                }
                
                response = requests.post(
                    f"{BASE_URL}/applications/",
                    json=application_payload,
                    headers=headers,
                    timeout=30
                )
                print(f"Statut: {response.status_code}")
                
                if response.status_code == 201:
                    data = response.json()
                    print(f"[OK] Candidature creee avec succes")
                    if "data" in data:
                        new_app = data["data"]
                        new_app_id = new_app.get("id")
                        print(f"  - Nouvelle candidature ID: {new_app_id}")
                        print(f"  - Status: {new_app.get('status', 'N/A')}")
                        
                        # Test mise à jour de cette candidature
                        if new_app_id:
                            test_update_application(new_app_id, headers)
                else:
                    response_text = response.text[:500] if len(response.text) > 500 else response.text
                    print(f"[ERREUR] Statut {response.status_code}: {response_text}")
            else:
                print(f"[WARN] Impossible de trouver candidat ou offre pour le test")
                print(f"  - Candidat ID: {candidate_id}")
                print(f"  - Offre ID: {job_offer_id}")
        else:
            print(f"[WARN] Impossible de recuperer users ou jobs")
            print(f"  - Users status: {response_users.status_code}")
            print(f"  - Jobs status: {response_jobs.status_code}")
    except Exception as e:
        print(f"[ERREUR] Exception creation candidature: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Test brouillon (POST /applications/drafts)
    print_section("6. TEST BROUILLON CANDIDATURE (POST /applications/drafts)")
    try:
        # Récupérer une offre pour le brouillon
        response_jobs = requests.get(f"{BASE_URL}/jobs/", headers=headers, params={"limit": 1}, timeout=30)
        
        if response_jobs.status_code == 200:
            jobs_data = response_jobs.json()
            job_offer_id = None
            
            if "data" in jobs_data:
                jobs_list = jobs_data["data"]
                if isinstance(jobs_list, list) and jobs_list:
                    job_offer_id = jobs_list[0].get("id")
            
            # Si pas d'offre, utiliser celle d'une candidature existante
            if not job_offer_id and application_id:
                try:
                    app_response = requests.get(f"{BASE_URL}/applications/{application_id}", headers=headers, timeout=30)
                    if app_response.status_code == 200:
                        app_data = app_response.json().get("data", {})
                        job_offer_id = app_data.get("job_offer_id")
                        print(f"[INFO] Utilisation offre existante pour brouillon: {job_offer_id}")
                except:
                    pass
            
            if job_offer_id:
                draft_payload = {
                    "job_offer_id": job_offer_id,
                    "form_data": {
                        "step": 1,
                        "values": {
                            "firstname": "Test",
                            "lastname": "Brouillon"
                        }
                    },
                    "ui_state": {
                        "currentStep": 2
                    }
                }
                
                response = requests.post(
                    f"{BASE_URL}/applications/drafts",
                    json=draft_payload,
                    headers=headers,
                    timeout=30
                )
                print(f"Statut: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"[OK] Brouillon sauvegarde avec succes")
                    if "data" in data:
                        print(f"  - Brouillon ID: {data['data'].get('id', 'N/A')}")
                    
                    # Test récupération du brouillon
                    test_get_draft(job_offer_id, headers)
                else:
                    print(f"[ERREUR] Statut {response.status_code}: {response.text[:500]}")
            else:
                print(f"[WARN] Aucune offre disponible pour test brouillon")
        else:
            print(f"[WARN] Impossible de recuperer les offres (status: {response_jobs.status_code})")
    except Exception as e:
        print(f"[ERREUR] Exception brouillon: {e}")
        import traceback
        traceback.print_exc()
    
    print_section("RESUME DES TESTS")
    print("[OK] Tests termines")
    print("Verifiez les sections ci-dessus pour voir les eventuelles erreurs")

def test_update_application(app_id, headers):
    """Test de mise à jour d'une candidature"""
    print(f"\n  -> Test mise a jour de la candidature {app_id}")
    try:
        update_payload = {
            "status": "reviewed"
        }
        
        response = requests.put(
            f"{BASE_URL}/applications/{app_id}",
            json=update_payload,
            headers=headers,
            timeout=30
        )
        print(f"     Statut PUT: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"     [OK] Candidature mise a jour")
            if "data" in data:
                print(f"     - Nouveau status: {data['data'].get('status', 'N/A')}")
        else:
            print(f"     [ERREUR] Mise a jour echouee: {response.text[:200]}")
    except Exception as e:
        print(f"     [ERREUR] Exception mise a jour: {e}")

def test_get_draft(job_offer_id, headers):
    """Test de récupération d'un brouillon"""
    print(f"\n  -> Test recuperation brouillon pour offre {job_offer_id}")
    try:
        response = requests.get(
            f"{BASE_URL}/applications/drafts",
            params={"job_offer_id": job_offer_id},
            headers=headers,
            timeout=30
        )
        print(f"     Statut GET: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"     [OK] Brouillon recupere")
            if "data" in data and data["data"]:
                draft_data = data["data"]
                print(f"     - Form data present: {'form_data' in draft_data}")
                print(f"     - UI state present: {'ui_state' in draft_data}")
        else:
            print(f"     [ERREUR] Recuperation echouee: {response.text[:200]}")
    except Exception as e:
        print(f"     [ERREUR] Exception recuperation: {e}")

def test_get_applications_list(headers):
    """Helper pour récupérer la liste et retourner un ID"""
    try:
        response = requests.get(
            f"{BASE_URL}/applications/",
            headers=headers,
            params={"limit": 5},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                return data["data"][0].get("id")
    except:
        pass
    return None

if __name__ == "__main__":
    test_applications()

