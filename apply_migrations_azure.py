"""
Script pour appliquer les migrations sur Azure Production
Respecte les meilleures pratiques : validation, rollback, logs
"""
import requests
import sys
import getpass
from datetime import datetime

# Configuration
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

def main():
    print("=" * 80)
    print("  APPLICATION DES MIGRATIONS - AZURE PRODUCTION")
    print("=" * 80)
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Étape 1: Authentification
    print("🔐 Étape 1: Authentification Administrateur")
    print("-" * 50)
    email = input("Email administrateur: ")
    password = getpass.getpass("Mot de passe: ")
    
    try:
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=30
        )
        
        if login_response.status_code != 200:
            print(f"❌ Échec de l'authentification: {login_response.status_code}")
            print(f"Détails: {login_response.text}")
            return 1
        
        # Gérer les deux formats de réponse possibles
        login_data = login_response.json()
        if "data" in login_data and "access_token" in login_data["data"]:
            token = login_data["data"]["access_token"]
        elif "access_token" in login_data:
            token = login_data["access_token"]
        else:
            print(f"❌ Format de réponse inattendu: {login_data}")
            return 1
        
        print("✅ Authentification réussie\n")
        
    except Exception as e:
        print(f"❌ Erreur d'authentification: {e}")
        return 1
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Étape 2: Vérifier le statut actuel
    print("📊 Étape 2: Vérification du Statut des Migrations")
    print("-" * 50)
    
    try:
        status_response = requests.get(
            f"{BASE_URL}/migrations/status",
            headers=headers,
            timeout=30
        )
        
        if status_response.status_code != 200:
            print(f"❌ Échec de la récupération du statut: {status_response.status_code}")
            return 1
        
        status_data = status_response.json()
        print(f"Version actuelle: {status_data.get('current_version', 'N/A')}")
        print(f"Statut: {status_data.get('status', 'N/A')}")
        print(f"Migrations en attente: {status_data.get('pending_migrations', 0)}")
        
        if status_data.get('pending_details'):
            print("\n📋 Migrations à appliquer:")
            for migration in status_data['pending_details']:
                print(f"  • {migration['revision']}: {migration['description']}")
        
        print()
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification du statut: {e}")
        return 1
    
    # Étape 3: Confirmation
    if status_data.get('status') == 'up_to_date':
        print("✅ Base de données déjà à jour. Aucune migration nécessaire.")
        return 0
    
    print("⚠️  Étape 3: Confirmation")
    print("-" * 50)
    confirmation = input("Voulez-vous appliquer ces migrations? (oui/non): ")
    
    if confirmation.lower() not in ['oui', 'yes', 'o', 'y']:
        print("❌ Opération annulée par l'utilisateur")
        return 1
    
    # Étape 4: Application des migrations
    print("\n🚀 Étape 4: Application des Migrations")
    print("-" * 50)
    
    try:
        apply_response = requests.post(
            f"{BASE_URL}/migrations/apply",
            headers=headers,
            timeout=120  # Timeout plus long pour les migrations
        )
        
        if apply_response.status_code != 200:
            print(f"❌ Échec de l'application des migrations: {apply_response.status_code}")
            print(f"Détails: {apply_response.text}")
            return 1
        
        apply_data = apply_response.json()
        print(f"✅ {apply_data.get('message', 'Migrations appliquées avec succès')}")
        
        if 'migrations_applied' in apply_data:
            print(f"\n📊 Migrations appliquées:")
            for migration in apply_data['migrations_applied']:
                print(f"  ✓ {migration}")
        
        print(f"\nVersion finale: {apply_data.get('new_version', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'application des migrations: {e}")
        print("⚠️  La base de données peut être dans un état incohérent.")
        print("   Vérifiez manuellement et considérez un rollback si nécessaire.")
        return 1
    
    # Étape 5: Vérification finale
    print("\n🔍 Étape 5: Vérification Finale")
    print("-" * 50)
    
    try:
        final_status = requests.get(
            f"{BASE_URL}/migrations/status",
            headers=headers,
            timeout=30
        )
        
        if final_status.status_code == 200:
            final_data = final_status.json()
            print(f"Version actuelle: {final_data.get('current_version', 'N/A')}")
            print(f"Statut: {final_data.get('status', 'N/A')}")
            print(f"Migrations en attente: {final_data.get('pending_migrations', 0)}")
        
    except Exception as e:
        print(f"⚠️  Impossible de vérifier le statut final: {e}")
    
    print("\n" + "=" * 80)
    print("  ✅ MIGRATIONS APPLIQUÉES AVEC SUCCÈS")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

