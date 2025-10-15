"""
Test du système de notifications pour toutes les actions utilisateur
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def test_notification_system():
    """Test complet du système de notifications"""
    
    print("\n" + "="*80)
    print("🔔 TEST SYSTÈME DE NOTIFICATIONS AUTOMATIQUES")
    print("="*80)
    
    # ==================== TEST 1: INSCRIPTION ====================
    print("\n📝 TEST 1: Notification d'inscription")
    print("-" * 80)
    
    # Générer un email unique
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"test_notif_{timestamp}@example.com"
    
    signup_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Notification",
        "phone": "+241 01 23 45 67",
        "date_of_birth": "1995-01-15",
        "sexe": "M",
        "role": "candidate",
        "statut": "actif"
    }
    
    print(f"📤 Inscription avec: {test_email}")
    signup_response = requests.post(
        f"{BASE_URL}/auth/signup/candidate",
        json=signup_data,
        timeout=10
    )
    
    if signup_response.status_code == 201:
        print(f"✅ Inscription réussie: {signup_response.status_code}")
        user_data = signup_response.json()
        user_id = user_data.get("id")
        print(f"   User ID: {user_id}")
    else:
        print(f"❌ Inscription échouée: {signup_response.status_code}")
        print(f"   Erreur: {signup_response.text}")
        return
    
    # Connexion pour obtenir le token
    print("\n🔐 Connexion...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": test_email,
            "password": "TestPassword123!"
        },
        timeout=10
    )
    
    if login_response.status_code != 200:
        print(f"❌ Connexion échouée: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    print("✅ Connecté avec succès")
    
    # ==================== VÉRIFICATION DES NOTIFICATIONS ====================
    print("\n🔍 TEST 2: Vérification des notifications")
    print("-" * 80)
    
    notif_response = requests.get(
        f"{BASE_URL}/notifications/",
        headers=headers,
        timeout=10
    )
    
    if notif_response.status_code == 200:
        notifications = notif_response.json()
        print(f"✅ Récupération réussie: {notif_response.status_code}")
        
        # Afficher les notifications
        items = notifications.get("items", [])
        print(f"\n📊 Nombre de notifications: {len(items)}")
        
        if items:
            print("\n📬 Notifications reçues:")
            for i, notif in enumerate(items, 1):
                print(f"\n   {i}. {notif.get('title')}")
                print(f"      Type: {notif.get('type')}")
                print(f"      Message: {notif.get('message')}")
                print(f"      Lien: {notif.get('link')}")
                print(f"      Lu: {notif.get('read')}")
                print(f"      Date: {notif.get('created_at')}")
            
            # Vérifier la notification de bienvenue
            welcome_notif = next(
                (n for n in items if n.get("type") == "registration"),
                None
            )
            if welcome_notif:
                print("\n✅ Notification de bienvenue trouvée:")
                print(f"   Titre: {welcome_notif.get('title')}")
                print(f"   Message: {welcome_notif.get('message')}")
            else:
                print("\n⚠️ Notification de bienvenue non trouvée")
        else:
            print("⚠️ Aucune notification trouvée")
    else:
        print(f"❌ Récupération notifications échouée: {notif_response.status_code}")
        print(f"   Erreur: {notif_response.text}")
    
    # ==================== TEST 3: CANDIDATURE ====================
    print("\n📄 TEST 3: Notification de candidature")
    print("-" * 80)
    
    # Récupérer une offre d'emploi
    jobs_response = requests.get(
        f"{BASE_URL}/jobs/?limit=1",
        headers=headers,
        timeout=10
    )
    
    if jobs_response.status_code == 200:
        jobs_data = jobs_response.json()
        jobs = jobs_data.get("data", []) if isinstance(jobs_data, dict) else jobs_data
        
        if jobs:
            job = jobs[0]
            job_id = job.get("id")
            job_title = job.get("title")
            
            print(f"✅ Offre trouvée: {job_title}")
            print(f"   ID: {job_id}")
            
            # Soumettre une candidature
            application_data = {
                "candidate_id": user_id,
                "job_offer_id": job_id,
                "cover_letter": "Je suis très motivé pour ce poste de test de notifications.",
                "status": "submitted",
                "mtp_answers": None
            }
            
            print(f"\n📤 Soumission candidature...")
            app_response = requests.post(
                f"{BASE_URL}/applications/",
                headers=headers,
                json=application_data,
                timeout=15
            )
            
            if app_response.status_code == 201:
                print(f"✅ Candidature soumise: {app_response.status_code}")
                app_data = app_response.json()
                application_id = app_data.get("data", {}).get("id")
                print(f"   Application ID: {application_id}")
                
                # Attendre un peu que la notification soit créée
                import time
                time.sleep(2)
                
                # Vérifier les nouvelles notifications
                print("\n🔍 Vérification nouvelles notifications...")
                notif_response2 = requests.get(
                    f"{BASE_URL}/notifications/",
                    headers=headers,
                    timeout=10
                )
                
                if notif_response2.status_code == 200:
                    notifications2 = notif_response2.json()
                    items2 = notifications2.get("items", [])
                    print(f"✅ Total notifications: {len(items2)}")
                    
                    # Vérifier la notification de candidature
                    app_notif = next(
                        (n for n in items2 if n.get("type") == "application_submitted"),
                        None
                    )
                    if app_notif:
                        print("\n✅ Notification de candidature trouvée:")
                        print(f"   Titre: {app_notif.get('title')}")
                        print(f"   Message: {app_notif.get('message')}")
                        print(f"   Lien: {app_notif.get('link')}")
                    else:
                        print("\n⚠️ Notification de candidature non trouvée")
                        print("\n📝 Toutes les notifications:")
                        for notif in items2:
                            print(f"   - {notif.get('type')}: {notif.get('title')}")
            else:
                print(f"❌ Candidature échouée: {app_response.status_code}")
                print(f"   Erreur: {app_response.text}")
        else:
            print("⚠️ Aucune offre d'emploi disponible pour tester")
    else:
        print(f"❌ Récupération offres échouée: {jobs_response.status_code}")
    
    # ==================== TEST 4: BROUILLON ====================
    print("\n💾 TEST 4: Notification de brouillon")
    print("-" * 80)
    
    if jobs:
        draft_data = {
            "user_id": user_id,
            "job_offer_id": job_id,
            "form_data": {
                "personal_info": {
                    "motivation": "Test de sauvegarde de brouillon"
                },
                "step": 1
            },
            "ui_state": {
                "current_step": 1,
                "progress": 20
            }
        }
        
        print(f"📤 Sauvegarde brouillon...")
        draft_response = requests.post(
            f"{BASE_URL}/applications/drafts",
            headers=headers,
            json=draft_data,
            timeout=10
        )
        
        if draft_response.status_code == 200:
            print(f"✅ Brouillon sauvegardé: {draft_response.status_code}")
            
            # Vérifier les notifications
            import time
            time.sleep(2)
            
            notif_response3 = requests.get(
                f"{BASE_URL}/notifications/",
                headers=headers,
                timeout=10
            )
            
            if notif_response3.status_code == 200:
                notifications3 = notif_response3.json()
                items3 = notifications3.get("items", [])
                
                draft_notif = next(
                    (n for n in items3 if n.get("type") == "draft_saved"),
                    None
                )
                if draft_notif:
                    print("\n✅ Notification de brouillon trouvée:")
                    print(f"   Titre: {draft_notif.get('title')}")
                    print(f"   Message: {draft_notif.get('message')}")
                else:
                    print("\n⚠️ Notification de brouillon non trouvée")
        else:
            print(f"❌ Sauvegarde brouillon échouée: {draft_response.status_code}")
            print(f"   Erreur: {draft_response.text}")
    
    # ==================== RÉSUMÉ ====================
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    final_notif_response = requests.get(
        f"{BASE_URL}/notifications/",
        headers=headers,
        timeout=10
    )
    
    if final_notif_response.status_code == 200:
        final_notifications = final_notif_response.json()
        final_items = final_notifications.get("items", [])
        
        print(f"\n✅ Total final des notifications: {len(final_items)}")
        print("\n📋 Types de notifications reçues:")
        
        types_count = {}
        for notif in final_items:
            notif_type = notif.get("type", "unknown")
            types_count[notif_type] = types_count.get(notif_type, 0) + 1
        
        for notif_type, count in types_count.items():
            print(f"   - {notif_type}: {count}")
        
        # Statistiques
        unread = sum(1 for n in final_items if not n.get("read", False))
        print(f"\n📬 Non lues: {unread}")
        print(f"📖 Lues: {len(final_items) - unread}")
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        test_notification_system()
    except Exception as e:
        print(f"\n❌ ERREUR GLOBALE: {e}")
        import traceback
        traceback.print_exc()

