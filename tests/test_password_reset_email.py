"""
Script de test pour vérifier l'envoi d'email de réinitialisation de mot de passe
"""
import requests
import json
import time

API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

def test_password_reset_email():
    print("\n📧 TEST EMAIL DE RÉINITIALISATION DE MOT DE PASSE")
    print("=" * 60)
    
    # Email de test (admin)
    test_email = "pendysevan11@gmail.com"
    
    print(f"\n📤 Envoi de la demande de réinitialisation pour : {test_email}")
    print("-" * 60)
    
    # 1. Demande de réinitialisation de mot de passe
    reset_data = {
        "email": test_email
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/forgot-password",
            json=reset_data,
            timeout=15
        )
        
        print(f"\n📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Requête acceptée par l'API")
            print(f"\n📝 Réponse: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            print("\n" + "=" * 60)
            print("⏳ VÉRIFICATION MANUELLE REQUISE")
            print("=" * 60)
            print(f"\n📧 Veuillez vérifier votre boîte mail : {test_email}")
            print("\n✅ Ce que vous devriez recevoir :")
            print("   • Expéditeur : SEEG Recrutement")
            print("   • Sujet : Réinitialisation de votre mot de passe")
            print("   • Contenu : Email HTML avec un lien de réinitialisation")
            print("   • Lien format : https://[URL]/reset-password?token=...")
            
            print("\n📋 Points à vérifier :")
            print("   1. L'email arrive bien dans la boîte de réception")
            print("   2. Le formatage HTML est correct")
            print("   3. La salutation personnalisée est présente")
            print("   4. Le lien de réinitialisation fonctionne")
            print("   5. Les instructions de sécurité sont claires")
            
            print("\n⏱️  Délai d'attente : ~30 secondes à 2 minutes")
            print("\n💡 Si vous ne recevez pas l'email :")
            print("   • Vérifiez les spams/indésirables")
            print("   • Vérifiez la configuration SMTP dans Azure")
            print("   • Consultez les logs : az webapp log tail --name seeg-backend-api --resource-group seeg-rg")
            
        elif response.status_code == 404:
            print("❌ Utilisateur non trouvé")
            print(f"Détails: {response.text}")
        else:
            print(f"❌ Erreur {response.status_code}")
            print(f"Détails: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Détails: {e.response.text if hasattr(e.response, 'text') else str(e.response)}")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


def test_password_reset_flow():
    """
    Test complet du flow de réinitialisation (si un token valide est disponible)
    """
    print("\n\n🔄 TEST FLOW COMPLET DE RÉINITIALISATION")
    print("=" * 60)
    
    test_email = "pendysevan11@gmail.com"
    
    # 1. Demande de reset
    print("\n1️⃣ Étape 1: Demande de réinitialisation")
    reset_data = {"email": test_email}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/forgot-password",
            json=reset_data,
            timeout=15
        )
        
        if response.status_code == 200:
            print("✅ Email de réinitialisation envoyé")
            
            print("\n2️⃣ Étape 2: Récupération du token")
            print("⏳ Veuillez récupérer le token dans l'email reçu...")
            print("\n💡 Format du lien: https://[URL]/reset-password?token=VOTRE_TOKEN")
            print("   Copiez uniquement la partie après 'token='")
            
            # Demander le token à l'utilisateur
            print("\n" + "=" * 60)
            print("Pour tester le reset complet, vous devrez :")
            print("1. Récupérer le token de l'email")
            print("2. Appeler manuellement:")
            print(f"   POST {API_BASE_URL}/api/v1/auth/reset-password")
            print("   Body: {{")
            print('     "token": "VOTRE_TOKEN",')
            print('     "new_password": "NouveauMotDePasse123!"')
            print("   }")
            
        else:
            print(f"❌ Échec étape 1: {response.status_code}")
            print(f"Détails: {response.text}")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    # Test principal
    test_password_reset_email()
    
    # Attendre un peu
    print("\n" + "=" * 60)
    time.sleep(2)
    
    # Test flow complet (informatif)
    test_password_reset_flow()
    
    print("\n" + "=" * 60)
    print("✅ TEST TERMINÉ")
    print("=" * 60)
    print("\n📌 RÉSUMÉ:")
    print("   • La requête API a été envoyée")
    print("   • Vérifiez votre email pour confirmer la réception")
    print("   • Consultez les logs Azure si nécessaire")
    print("\n")

