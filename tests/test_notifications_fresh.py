"""
Test des notifications avec suppression de la candidature existante
"""
import requests
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

# Credentials
USER_EMAIL = "sevan@cnx4-0.com"
USER_PASSWORD = "Sevan@cnx4-0"

def print_section(title: str):
    """Afficher un titre de section"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print_section("🔔 TEST NOTIFICATIONS APRÈS REDÉMARRAGE API")
    
    # Connexion
    print("\n🔐 Connexion...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": USER_EMAIL, "password": USER_PASSWORD},
        timeout=10
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erreur connexion: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = token_data.get("user", {}).get("id")
    
    print(f"✅ Connecté - User ID: {user_id}")
    
    # Récupérer les candidatures existantes
    print("\n📋 Vérification candidatures existantes...")
    apps_response = requests.get(
        f"{BASE_URL}/applications/",
        headers=headers,
        timeout=10
    )
    
    if apps_response.status_code == 200:
        apps_data = apps_response.json()
        applications = apps_data.get("data", []) if isinstance(apps_data, dict) else apps_data
        
        print(f"✅ {len(applications)} candidature(s) existante(s)")
        
        # Supprimer la dernière candidature si elle existe
        if applications:
            last_app = applications[0]
            app_id = last_app.get("id")
            job_title = last_app.get("job_offer", {}).get("title", "N/A")
            
            print(f"\n🗑️  Suppression de la candidature existante pour '{job_title}'...")
            delete_response = requests.delete(
                f"{BASE_URL}/applications/{app_id}",
                headers=headers,
                timeout=10
            )
            
            if delete_response.status_code in [200, 204]:
                print(f"✅ Candidature supprimée")
            else:
                print(f"⚠️ Impossible de supprimer: {delete_response.status_code}")
    
    # Récupérer une offre
    print("\n💼 Récupération d'une offre d'emploi...")
    jobs_response = requests.get(
        f"{BASE_URL}/jobs/?limit=1",
        headers=headers,
        timeout=10
    )
    
    if jobs_response.status_code != 200:
        print(f"❌ Erreur récupération offres: {jobs_response.status_code}")
        return
    
    jobs_data = jobs_response.json()
    jobs = jobs_data.get("data", []) if isinstance(jobs_data, dict) else jobs_data
    
    if not jobs:
        print("❌ Aucune offre disponible")
        return
    
    job = jobs[0]
    job_id = job.get("id")
    job_title = job.get("title")
    
    print(f"✅ Offre sélectionnée: {job_title}")
    
    # Récupérer les détails pour les questions MTP
    print("\n📝 Récupération questions MTP...")
    job_detail_response = requests.get(
        f"{BASE_URL}/jobs/{job_id}",
        headers=headers,
        timeout=10
    )
    
    mtp_answers_data = {
        "reponses_metier": [
            "Je possède une solide expérience technique",
            "Mes compétences sont alignées avec les besoins",
            "Je suis capable de m'adapter rapidement"
        ],
        "reponses_talent": [
            "Mon parcours démontre ma capacité d'adaptation",
            "Je suis motivé et professionnel",
            "Je travaille bien en équipe"
        ],
        "reponses_paradigme": [
            "Je partage les valeurs de SEEG",
            "Je suis engagé dans l'excellence",
            "Je contribue positivement"
        ]
    }
    
    if job_detail_response.status_code == 200:
        job_detail = job_detail_response.json()
        if isinstance(job_detail, dict) and "data" in job_detail:
            job_detail = job_detail["data"]
        
        mtp_questions = job_detail.get("questions_mtp", {})
        if mtp_questions:
            print(f"✅ Questions MTP trouvées")
            
            # Générer les bonnes réponses
            mtp_answers_data = {}
            for questions_key, answers_key in [
                ("questions_metier", "reponses_metier"),
                ("questions_talent", "reponses_talent"),
                ("questions_paradigme", "reponses_paradigme")
            ]:
                questions = mtp_questions.get(questions_key, [])
                if questions:
                    answers_list = [
                        f"Réponse pertinente et professionnelle démontrant mes compétences pour cette question."
                        for _ in questions
                    ]
                    mtp_answers_data[answers_key] = answers_list
                    print(f"   - {len(answers_list)} réponse(s) {answers_key}")
    
    # Soumettre une NOUVELLE candidature
    print("\n📨 Soumission NOUVELLE candidature...")
    application_data = {
        "candidate_id": user_id,
        "job_offer_id": job_id,
        "cover_letter": "Je suis très motivé pour rejoindre SEEG. Mon expérience et mes compétences me permettront de contribuer efficacement à vos projets.",
        "status": "submitted",
        "mtp_answers": mtp_answers_data
    }
    
    app_response = requests.post(
        f"{BASE_URL}/applications/",
        headers=headers,
        json=application_data,
        timeout=20
    )
    
    if app_response.status_code == 201:
        print(f"✅ CANDIDATURE SOUMISE AVEC SUCCÈS !")
        app_data = app_response.json()
        application_id = app_data.get("data", {}).get("id")
        
        print(f"\n   🆔 ID: {application_id}")
        print(f"   💼 Poste: {job_title}")
        print(f"\n   📧 Vérifiez votre email: {USER_EMAIL}")
        print(f"   🔔 Vérification des notifications...")
        
        # Attendre pour l'envoi
        import time
        time.sleep(3)
        
        # Vérifier les notifications
        notif_response = requests.get(
            f"{BASE_URL}/notifications/",
            headers=headers,
            timeout=10
        )
        
        if notif_response.status_code == 200:
            notifications = notif_response.json()
            items = notifications.get("items", [])
            
            print(f"\n📊 NOTIFICATIONS REÇUES: {len(items)}")
            
            if items:
                print("\n📬 Liste des notifications:")
                for i, notif in enumerate(items, 1):
                    print(f"\n   {i}. 🔔 {notif.get('title')}")
                    print(f"      📝 {notif.get('message')}")
                    print(f"      🏷️  Type: {notif.get('type')}")
                    print(f"      {'📖' if notif.get('read') else '📬'} {'Lu' if notif.get('read') else 'Non lu'}")
                
                # Compter par type
                types_count = {}
                for notif in items:
                    notif_type = notif.get("type", "unknown")
                    types_count[notif_type] = types_count.get(notif_type, 0) + 1
                
                print(f"\n📈 Répartition:")
                for notif_type, count in types_count.items():
                    print(f"   - {notif_type}: {count}")
                
                # Vérifier notification de candidature
                app_notif = next(
                    (n for n in items if n.get("type") == "application_submitted"),
                    None
                )
                if app_notif:
                    print(f"\n✅ NOTIFICATION DE CANDIDATURE TROUVÉE !")
                else:
                    print(f"\n⚠️ Notification de candidature non trouvée")
            else:
                print("\n❌ AUCUNE NOTIFICATION CRÉÉE")
                print("   ⚠️ Le système de notifications ne fonctionne pas encore")
        else:
            print(f"\n❌ Erreur récupération notifications: {notif_response.status_code}")
    else:
        print(f"❌ Erreur soumission: {app_response.status_code}")
        print(f"   Détails: {app_response.text}")
    
    print("\n" + "="*80)
    print(f"📧 VÉRIFIEZ AUSSI VOTRE BOÎTE MAIL: {USER_EMAIL}")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

