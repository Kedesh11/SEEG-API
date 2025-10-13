"""
Script pour vérifier que les données utilisateur sont complètes pour l'email de réinitialisation
"""
import requests
import json

API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

# Credentials admin
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def check_user_data():
    print("\n🔍 VÉRIFICATION DES DONNÉES UTILISATEUR")
    print("=" * 60)
    
    # 1. Connexion admin
    print("\n🔐 Connexion avec le compte admin...")
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            token = result["access_token"]
            user_data = result.get("user", {})
            
            print("✅ Connexion réussie")
            print("\n📊 DONNÉES UTILISATEUR RÉCUPÉRÉES :")
            print("=" * 60)
            
            # Afficher les données importantes pour l'email
            print(f"\n📧 Email: {user_data.get('email')}")
            print(f"👤 Prénom: {user_data.get('first_name')}")
            print(f"👤 Nom: {user_data.get('last_name')}")
            print(f"⚥  Sexe: {user_data.get('sexe')}")
            print(f"📱 Téléphone: {user_data.get('phone')}")
            print(f"🆔 ID: {user_data.get('id')}")
            print(f"🎭 Rôle: {user_data.get('role')}")
            
            # Vérifier si les données nécessaires pour la salutation sont présentes
            print("\n✅ VALIDATION POUR EMAIL DE RÉINITIALISATION :")
            print("=" * 60)
            
            first_name = user_data.get('first_name')
            last_name = user_data.get('last_name')
            sexe = user_data.get('sexe')
            
            if not first_name or not last_name:
                print("⚠️  ATTENTION : Prénom ou Nom manquant")
                print("   → La salutation sera générique : 'Bonjour'")
            elif not sexe:
                print("⚠️  Sexe non renseigné")
                print(f"   → La salutation sera : '{first_name} {last_name}'")
            elif sexe == 'M':
                print(f"✅ Salutation complète : 'Monsieur {first_name} {last_name}'")
            elif sexe == 'F':
                print(f"✅ Salutation complète : 'Madame {first_name} {last_name}'")
            else:
                print(f"⚠️  Sexe invalide : {sexe}")
                print(f"   → La salutation sera : '{first_name} {last_name}'")
            
            # Test de l'email de réinitialisation avec cet utilisateur
            print("\n\n📧 TEST EMAIL DE RÉINITIALISATION")
            print("=" * 60)
            
            test_email = "pendysevan11@gmail.com"
            print(f"\n📤 Envoi de l'email de réinitialisation à : {test_email}")
            
            reset_data = {"email": test_email}
            reset_response = requests.post(
                f"{API_BASE_URL}/api/v1/auth/forgot-password",
                json=reset_data,
                timeout=15
            )
            
            if reset_response.status_code == 200:
                print("✅ Email envoyé avec succès")
                print("\n📋 L'email devrait contenir :")
                
                if sexe == 'M' and first_name and last_name:
                    expected_salutation = f"Monsieur {first_name} {last_name}"
                elif sexe == 'F' and first_name and last_name:
                    expected_salutation = f"Madame {first_name} {last_name}"
                elif first_name and last_name:
                    expected_salutation = f"{first_name} {last_name}"
                else:
                    expected_salutation = "Bonjour"
                
                print(f"   • Salutation : '{expected_salutation},'")
                print("   • Lien de réinitialisation personnalisé")
                print("   • Instructions de sécurité")
                
                print("\n⏳ Vérifiez votre boîte mail pour confirmer")
                print("   → Recherchez la salutation personnalisée")
                
            else:
                print(f"❌ Erreur {reset_response.status_code}")
                print(f"Détails: {reset_response.text}")
                
        else:
            print(f"❌ Échec de connexion : {response.status_code}")
            print(f"Détails: {response.text}")
    
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    check_user_data()
    
    print("\n" + "=" * 60)
    print("✅ VÉRIFICATION TERMINÉE")
    print("=" * 60)

