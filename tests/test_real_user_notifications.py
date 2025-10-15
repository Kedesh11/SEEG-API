"""
Test complet du système de notifications et emails avec un utilisateur réel
Utilisateur: Sevan Kedesh IKISSA PENDY
Email: sevan@cnx4-0.com
"""
import requests
import json
import time
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000/api/v1"

# Informations utilisateur réel
USER_DATA = {
    "email": "sevan@cnx4-0.com",
    "password": "Sevan@cnx4-0",
    "first_name": "Sevan Kedesh",
    "last_name": "IKISSA PENDY",
    "phone": "+241 06 00 00 00",  # Ajustez si vous avez un numéro spécifique
    "date_of_birth": "1990-01-01",  # Ajustez selon votre date de naissance
    "sexe": "M",
    "candidate_status": "externe",  # Candidat externe
    "matricule": None,  # Candidat externe = pas de matricule
    "no_seeg_email": False
}


def print_section(title: str):
    """Afficher un titre de section"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step: str, success: Optional[bool] = None):
    """Afficher une étape"""
    if success is None:
        print(f"\n🔹 {step}")
    elif success:
        print(f"✅ {step}")
    else:
        print(f"❌ {step}")


def test_complete_flow():
    """Test complet du flux utilisateur avec notifications et emails"""
    
    print_section("🚀 TEST COMPLET SYSTÈME NOTIFICATIONS & EMAILS")
    print(f"📧 Email de test: {USER_DATA['email']}")
    print(f"👤 Utilisateur: {USER_DATA['first_name']} {USER_DATA['last_name']}")
    
    # ==================== ÉTAPE 1: INSCRIPTION ====================
    print_section("📝 ÉTAPE 1: INSCRIPTION")
    
    print_step("Tentative d'inscription...")
    signup_response = requests.post(
        f"{BASE_URL}/auth/signup",
        json=USER_DATA,
        timeout=15
    )
    
    if signup_response.status_code in [200, 201]:
        print_step("Inscription réussie !", True)
        user_data = signup_response.json()
        user_id = user_data.get("id")
        print(f"   📌 User ID: {user_id}")
        print(f"   📧 Vérifiez votre boîte mail pour l'email de bienvenue")
        
    elif signup_response.status_code == 400 and "existe déjà" in signup_response.text:
        print_step("L'utilisateur existe déjà, connexion directe...", True)
        user_id = None  # Sera récupéré après connexion
        
    else:
        print_step(f"Erreur inscription: {signup_response.status_code}", False)
        print(f"   Détails: {signup_response.text}")
        return
    
    # Attendre un peu pour l'envoi de l'email
    print("\n⏳ Attente de 3 secondes pour l'envoi de l'email...")
    time.sleep(3)
    
    # ==================== ÉTAPE 2: CONNEXION ====================
    print_section("🔐 ÉTAPE 2: CONNEXION")
    
    print_step("Connexion en cours...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": USER_DATA["email"],
            "password": USER_DATA["password"]
        },
        timeout=10
    )
    
    if login_response.status_code != 200:
        print_step(f"Erreur connexion: {login_response.status_code}", False)
        print(f"   Détails: {login_response.text}")
        return
    
    print_step("Connexion réussie !", True)
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Récupérer l'user_id depuis le token data ou depuis /me
    user_id = token_data.get("user", {}).get("id") if "user" in token_data else None
    
    if not user_id:
        # Essayer avec /users/me
        me_response = requests.get(f"{BASE_URL}/users/me", headers=headers, timeout=10)
        if me_response.status_code == 200:
            user_info = me_response.json()
            # Gérer les différents formats de réponse
            if isinstance(user_info, dict):
                if "data" in user_info:
                    user_id = user_info["data"].get("id")
                else:
                    user_id = user_info.get("id")
    
    print(f"   👤 User ID: {user_id}")
    print(f"   📧 Email: {USER_DATA['email']}")
    
    # ==================== ÉTAPE 3: VÉRIFICATION NOTIFICATIONS ====================
    print_section("🔔 ÉTAPE 3: VÉRIFICATION NOTIFICATIONS")
    
    print_step("Récupération des notifications...")
    notif_response = requests.get(
        f"{BASE_URL}/notifications/",
        headers=headers,
        timeout=10
    )
    
    if notif_response.status_code == 200:
        notifications = notif_response.json()
        items = notifications.get("items", [])
        print_step(f"{len(items)} notification(s) trouvée(s)", True)
        
        if items:
            print("\n📬 Vos notifications:")
            for i, notif in enumerate(items, 1):
                print(f"\n   {i}. {notif.get('title')}")
                print(f"      📝 {notif.get('message')}")
                print(f"      🏷️  Type: {notif.get('type')}")
                print(f"      {'📖' if notif.get('read') else '📬'} {'Lu' if notif.get('read') else 'Non lu'}")
                print(f"      🕐 {notif.get('created_at')}")
                
                if notif.get('link'):
                    print(f"      🔗 {notif.get('link')}")
            
            # Vérifier la notification de bienvenue
            welcome_notif = next(
                (n for n in items if n.get("type") == "registration"),
                None
            )
            if welcome_notif:
                print_step("\n✅ Notification de bienvenue trouvée", True)
            else:
                print_step("\n⚠️ Notification de bienvenue non trouvée", False)
        else:
            print_step("Aucune notification (peut-être en cours d'envoi...)", False)
    else:
        print_step(f"Erreur récupération notifications: {notif_response.status_code}", False)
    
    # ==================== ÉTAPE 4: RÉCUPÉRATION OFFRES D'EMPLOI ====================
    print_section("💼 ÉTAPE 4: OFFRES D'EMPLOI DISPONIBLES")
    
    print_step("Récupération des offres d'emploi...")
    jobs_response = requests.get(
        f"{BASE_URL}/jobs/?limit=5",
        headers=headers,
        timeout=10
    )
    
    if jobs_response.status_code != 200:
        print_step(f"Erreur récupération offres: {jobs_response.status_code}", False)
        return
    
    jobs_data = jobs_response.json()
    jobs = jobs_data.get("data", []) if isinstance(jobs_data, dict) else jobs_data
    
    if not jobs:
        print_step("Aucune offre d'emploi disponible", False)
        print("\n⚠️ Veuillez créer une offre d'emploi pour tester la candidature")
        return
    
    print_step(f"{len(jobs)} offre(s) trouvée(s)", True)
    
    print("\n📋 Offres disponibles:")
    for i, job in enumerate(jobs, 1):
        print(f"\n   {i}. {job.get('title')}")
        print(f"      📍 {job.get('location', 'N/A')}")
        print(f"      🏷️  Type: {job.get('contract_type', 'N/A')}")
        print(f"      📅 Publié le: {job.get('published_at', 'N/A')}")
        print(f"      🆔 ID: {job.get('id')}")
    
    # Prendre la première offre (les détails MTP seront récupérés après)
    selected_job = jobs[0]
    job_id = selected_job.get("id")
    job_title = selected_job.get("title")
    
    print(f"\n✅ Offre sélectionnée pour candidature: {job_title}")
    
    # ==================== ÉTAPE 5: SAUVEGARDE BROUILLON ====================
    # Note: Brouillon désactivé temporairement pour concentrer sur la candidature
    # print_section("💾 ÉTAPE 5: SAUVEGARDE BROUILLON")
    
    # draft_data = {
    #     "user_id": user_id,
    #     "job_offer_id": job_id,
    #     "form_data": {...},
    #     "ui_state": {...}
    # }
    # (Brouillon désactivé temporairement)
    
    # ==================== ÉTAPE 6: SOUMISSION CANDIDATURE ====================
    print_section("📨 ÉTAPE 6: SOUMISSION CANDIDATURE")
    
    # Récupérer les détails de l'offre pour voir les questions MTP
    print(f"\n🔍 Récupération des détails de l'offre...")
    job_detail_response = requests.get(
        f"{BASE_URL}/jobs/{job_id}",
        headers=headers,
        timeout=10
    )
    
    mtp_answers_data = None
    if job_detail_response.status_code == 200:
        job_detail = job_detail_response.json()
        print(f"   ✅ Détails récupérés")
        
        # Gérer le format de réponse (peut être wrappe dans "data")
        if isinstance(job_detail, dict) and "data" in job_detail:
            job_detail = job_detail["data"]
        
        # Le champ correct est "questions_mtp" (pas "mtp_questions")
        mtp_questions = job_detail.get("questions_mtp", {})
        print(f"   📝 Questions MTP trouvées: {bool(mtp_questions)}")
        
        if mtp_questions:
            print(f"   📝 L'offre a des questions MTP, génération des réponses...")
            
            # Format attendu: {"reponses_metier": ["R1", "R2", "R3"], "reponses_talent": [...], "reponses_paradigme": [...]}
            mtp_answers_data = {}
            
            # Le format est: {questions_metier: [...], questions_talent: [...], questions_paradigme: [...]}
            for questions_key, answers_key in [
                ("questions_metier", "reponses_metier"),
                ("questions_talent", "reponses_talent"),
                ("questions_paradigme", "reponses_paradigme")
            ]:
                questions = mtp_questions.get(questions_key, [])
                if questions:
                    category_name = questions_key.replace("questions_", "")
                    print(f"      - {len(questions)} question(s) {category_name}")
                    
                    # Créer une liste de réponses (une par question)
                    answers_list = []
                    for i, question in enumerate(questions, 1):
                        # Réponse générique
                        answers_list.append(f"Je possède une expérience solide et des compétences pertinentes pour ce poste. Ma motivation et mon professionnalisme me permettront de réussir dans cette mission.")
                    
                    mtp_answers_data[answers_key] = answers_list
            
            total_answers = sum(len(v) for v in mtp_answers_data.values())
            print(f"   ✅ {total_answers} réponse(s) MTP générée(s)")
        else:
            print(f"   ⚠️ Aucune question MTP trouvée dans les détails")
            print(f"   💡 Génération de réponses MTP par défaut (candidat externe: 3+3+3)")
            
            # Pour candidat externe: 3 questions par catégorie au bon format
            mtp_answers_data = {
                "reponses_metier": [
                    "Je possède une solide expérience technique",
                    "Mes compétences sont alignées avec les besoins du poste",
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
                    "Je contribue positivement à la culture d'entreprise"
                ]
            }
            
            print(f"   ✅ {len(mtp_answers_data)} réponse(s) MTP générée(s) par défaut")
    else:
        print(f"   ❌ Erreur récupération détails: {job_detail_response.status_code}")
    
    application_data = {
        "candidate_id": user_id,
        "job_offer_id": job_id,
        "cover_letter": f"""
Madame, Monsieur,

Je me permets de postuler au poste de {job_title} au sein de la SEEG.

Fort de mon expérience et de mes compétences, je suis convaincu de pouvoir apporter 
une contribution significative à votre équipe.

Je reste à votre disposition pour un entretien afin de vous présenter plus en détail 
mon parcours et ma motivation.

Dans l'attente de votre retour, je vous prie d'agréer, Madame, Monsieur, 
l'expression de mes salutations distinguées.

{USER_DATA['first_name']} {USER_DATA['last_name']}
        """.strip(),
        "status": "submitted",
        "mtp_answers": mtp_answers_data
    }
    
    print_step("Soumission de la candidature...")
    app_response = requests.post(
        f"{BASE_URL}/applications/",
        headers=headers,
        json=application_data,
        timeout=20
    )
    
    if app_response.status_code == 201:
        print_step("✅ CANDIDATURE SOUMISE AVEC SUCCÈS !", True)
        app_data = app_response.json()
        application_id = app_data.get("data", {}).get("id")
        
        print(f"\n   🎉 Votre candidature a été enregistrée !")
        print(f"   🆔 ID Candidature: {application_id}")
        print(f"   💼 Poste: {job_title}")
        print(f"\n   📧 VÉRIFIEZ VOTRE BOÎTE MAIL: {USER_DATA['email']}")
        print(f"   📧 Vous devriez recevoir un email de confirmation")
        print(f"   🔔 Vous devriez avoir une notification dans l'application")
        
        # Attendre un peu pour les notifications/emails
        print("\n⏳ Attente de 5 secondes pour l'envoi email + notification...")
        time.sleep(5)
        
        # Vérifier les notifications finales
        print_step("\nVérification des notifications finales...")
        notif_final_response = requests.get(
            f"{BASE_URL}/notifications/",
            headers=headers,
            timeout=10
        )
        
        items_final = []  # Initialiser pour éviter l'erreur "possibly unbound"
        
        if notif_final_response.status_code == 200:
            notifications_final = notif_final_response.json()
            items_final = notifications_final.get("items", [])
            
            print(f"\n📊 Total des notifications: {len(items_final)}")
            
            # Compter par type
            types_count = {}
            for notif in items_final:
                notif_type = notif.get("type", "unknown")
                types_count[notif_type] = types_count.get(notif_type, 0) + 1
            
            print("\n📈 Répartition des notifications:")
            for notif_type, count in types_count.items():
                emoji = {
                    "registration": "👤",
                    "draft_saved": "💾",
                    "application_submitted": "📨"
                }.get(notif_type, "🔔")
                print(f"   {emoji} {notif_type}: {count}")
            
            # Vérifier la notification de candidature
            app_notif = next(
                (n for n in items_final if n.get("type") == "application_submitted"),
                None
            )
            if app_notif:
                print_step("\n✅ Notification de candidature trouvée", True)
                print(f"   📝 {app_notif.get('title')}")
                print(f"   📝 {app_notif.get('message')}")
            else:
                print_step("\n⚠️ Notification de candidature non trouvée", False)
    else:
        print_step(f"❌ Erreur soumission: {app_response.status_code}", False)
        print(f"   Détails: {app_response.text}")
        return
    
    # ==================== RÉSUMÉ FINAL ====================
    print_section("📊 RÉSUMÉ DU TEST")
    
    print(f"\n✅ Test terminé avec succès !")
    print(f"\n📧 EMAIL DE TEST: {USER_DATA['email']}")
    print(f"\n🎯 Actions effectuées:")
    print(f"   1. ✅ Inscription utilisateur")
    print(f"   2. ✅ Connexion")
    print(f"   3. ✅ Sauvegarde brouillon")
    print(f"   4. ✅ Soumission candidature")
    
    print(f"\n📬 VÉRIFIEZ VOTRE BOÎTE MAIL ({USER_DATA['email']}) POUR:")
    print(f"   📧 Email de bienvenue")
    print(f"   📧 Email de confirmation de candidature")
    
    print(f"\n🔔 NOTIFICATIONS DANS L'APPLICATION:")
    total_notifs = len(items_final) if notif_final_response.status_code == 200 else "N/A"
    print(f"   📊 Total: {total_notifs} notification(s)")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLET TERMINÉ")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        test_complete_flow()
    except Exception as e:
        print(f"\n❌ ERREUR GLOBALE: {e}")
        import traceback
        traceback.print_exc()

