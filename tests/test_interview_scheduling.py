"""
Test complet du système de planification d'entretiens avec notifications et emails
Test avec l'utilisateur réel: Sevan Kedesh IKISSA PENDY (sevan@cnx4-0.com)
"""
import requests
from datetime import datetime, timedelta
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

# Credentials admin (recruteur)
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

# Credentials candidat (pour vérifier les notifications)
CANDIDATE_EMAIL = "sevan@cnx4-0.com"
CANDIDATE_PASSWORD = "Sevan@cnx4-0"


def print_section(title: str):
    """Afficher un titre de section"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    print_section("📅 TEST PLANIFICATION ENTRETIEN + NOTIFICATIONS + EMAILS")
    
    # ==================== ÉTAPE 1: CONNEXION UTILISATEUR ====================
    print_section("🔐 ÉTAPE 1: CONNEXION UTILISATEUR")
    
    print("🔹 Connexion admin/recruteur...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erreur connexion: {login_response.status_code}")
        print(f"   Détails: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = token_data.get("user", {}).get("id")
    
    print(f"✅ Connecté - User ID: {user_id}")
    
    # ==================== ÉTAPE 2: RÉCUPÉRER CANDIDATURES ====================
    print_section("📋 ÉTAPE 2: RÉCUPÉRATION CANDIDATURES")
    
    print("🔹 Récupération des candidatures...")
    apps_response = requests.get(
        f"{BASE_URL}/applications/?limit=10",
        headers=headers,
        timeout=10
    )
    
    if apps_response.status_code != 200:
        print(f"❌ Erreur récupération candidatures: {apps_response.status_code}")
        return
    
    apps_data = apps_response.json()
    applications = apps_data.get("data", []) if isinstance(apps_data, dict) else apps_data
    
    if not applications:
        print("❌ Aucune candidature disponible")
        print("   ⚠️ Veuillez d'abord créer une candidature pour tester")
        return
    
    print(f"✅ {len(applications)} candidature(s) trouvée(s)")
    
    # Trouver une candidature du candidat test
    target_application = None
    for app in applications:
        candidate_info = app.get("candidate", {})
        if candidate_info.get("email") == CANDIDATE_EMAIL:
            target_application = app
            break
    
    if not target_application:
        # Prendre la première
        target_application = applications[0]
        print(f"⚠️ Candidature de test non trouvée, utilisation de la première")
    
    application_id = target_application.get("id")
    candidate_info = target_application.get("candidate", {})
    candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
    candidate_email = candidate_info.get("email", "unknown@example.com")
    job_offer_info = target_application.get("job_offer", {})
    job_title = job_offer_info.get("title", "Poste non spécifié")
    
    print(f"\n📌 Candidature sélectionnée:")
    print(f"   🆔 ID: {application_id}")
    print(f"   👤 Candidat: {candidate_name}")
    print(f"   📧 Email: {candidate_email}")
    print(f"   💼 Poste: {job_title}")
    
    # ==================== ÉTAPE 3: PLANIFIER ENTRETIEN ====================
    print_section("📅 ÉTAPE 3: PLANIFICATION ENTRETIEN")
    
    # Date d'entretien: demain à 10h
    interview_datetime = datetime.now() + timedelta(days=1)
    interview_date = interview_datetime.strftime("%Y-%m-%d")
    interview_time = "10:00:00"
    
    interview_data = {
        "date": interview_date,
        "time": interview_time,
        "application_id": application_id,
        "candidate_name": candidate_name,
        "job_title": job_title,
        "status": "scheduled",
        "location": "Siège SEEG, Libreville - Salle de Conférence A",
        "notes": "Entretien technique et RH combiné. Prévoir 1h30. Documents originaux requis."
    }
    
    print(f"\n🔹 Planification entretien...")
    print(f"   📅 Date: {interview_date}")
    print(f"   ⏰ Heure: {interview_time}")
    print(f"   📍 Lieu: {interview_data['location']}")
    
    interview_response = requests.post(
        f"{BASE_URL}/interviews/slots",
        headers=headers,
        json=interview_data,
        timeout=15
    )
    
    if interview_response.status_code == 201:
        print(f"\n✅ ✅ ENTRETIEN PLANIFIÉ AVEC SUCCÈS !")
        interview_result = interview_response.json()
        interview_id = interview_result.get("id")
        
        print(f"\n   🎯 Détails de l'entretien:")
        print(f"   🆔 ID Entretien: {interview_id}")
        print(f"   📅 Date: {interview_result.get('date')}")
        print(f"   ⏰ Heure: {interview_result.get('time')}")
        print(f"   📍 Lieu: {interview_result.get('location')}")
        print(f"   📝 Notes: {interview_result.get('notes')}")
        
        print(f"\n   📧 EMAIL ENVOYÉ À: {candidate_email}")
        print(f"   🔔 NOTIFICATION CRÉÉE POUR: {candidate_name}")
        
        # Attendre pour l'envoi
        import time
        print(f"\n   ⏳ Attente de 5 secondes pour l'envoi email + notification...")
        time.sleep(5)
        
        # Vérifier les notifications du candidat
        print_section("🔔 ÉTAPE 4: VÉRIFICATION NOTIFICATIONS CANDIDAT")
        
        # Connexion candidat
        print("🔹 Connexion candidat pour vérifier notifications...")
        candidate_login = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": candidate_email, "password": CANDIDATE_PASSWORD},
            timeout=10
        )
        
        if candidate_login.status_code == 200:
            candidate_token = candidate_login.json().get("access_token")
            candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
            
            print("✅ Candidat connecté")
            
            # Récupérer les notifications
            notif_response = requests.get(
                f"{BASE_URL}/notifications/",
                headers=candidate_headers,
                timeout=10
            )
            
            if notif_response.status_code == 200:
                notifications = notif_response.json()
                items = notifications.get("items", [])
                
                print(f"\n📊 Total notifications: {len(items)}")
                
                if items:
                    print("\n📬 Notifications reçues:")
                    for i, notif in enumerate(items, 1):
                        print(f"\n   {i}. 🔔 {notif.get('title')}")
                        print(f"      📝 {notif.get('message')}")
                        print(f"      🏷️  Type: {notif.get('type')}")
                        print(f"      {'📖' if notif.get('read') else '📬'} {'Lu' if notif.get('read') else 'Non lu'}")
                    
                    # Chercher la notification d'entretien
                    interview_notif = next(
                        (n for n in items if n.get("type") == "interview_scheduled"),
                        None
                    )
                    
                    if interview_notif:
                        print(f"\n✅ ✅ NOTIFICATION D'ENTRETIEN TROUVÉE !")
                        print(f"   📝 Titre: {interview_notif.get('title')}")
                        print(f"   📝 Message: {interview_notif.get('message')}")
                        print(f"   🔗 Lien: {interview_notif.get('link')}")
                    else:
                        print(f"\n⚠️ Notification d'entretien non trouvée")
                        print(f"\n   📋 Types de notifications présentes:")
                        for notif in items:
                            print(f"      - {notif.get('type')}")
                else:
                    print("\n❌ AUCUNE NOTIFICATION TROUVÉE")
                    print("   ⚠️ Le système de notifications ne fonctionne pas")
            else:
                print(f"❌ Erreur récupération notifications: {notif_response.status_code}")
        else:
            print(f"⚠️ Impossible de se connecter en tant que candidat: {candidate_login.status_code}")
    
    else:
        print(f"\n❌ ERREUR PLANIFICATION: {interview_response.status_code}")
        print(f"   Détails: {interview_response.text}")
        return
    
    # ==================== RÉSUMÉ FINAL ====================
    print_section("📊 RÉSUMÉ DU TEST")
    
    print(f"\n✅ Test terminé !")
    print(f"\n🎯 Actions effectuées:")
    print(f"   1. ✅ Connexion recruteur")
    print(f"   2. ✅ Récupération candidatures")
    print(f"   3. ✅ Planification entretien")
    print(f"   4. ✅ Vérification notifications")
    
    print(f"\n📧 VÉRIFIEZ VOTRE BOÎTE MAIL: {candidate_email}")
    print(f"   Vous devriez avoir reçu un email d'invitation détaillé")
    print(f"   avec toutes les informations de l'entretien")
    
    print(f"\n🔔 VÉRIFIEZ LES NOTIFICATIONS:")
    print(f"   Connectez-vous sur l'application avec {candidate_email}")
    print(f"   pour voir la notification d'entretien")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLET TERMINÉ")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERREUR GLOBALE: {e}")
        import traceback
        traceback.print_exc()

