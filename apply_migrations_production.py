"""
Script pour appliquer les migrations sur Azure via l'endpoint API
"""
import requests
import time
import sys

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# Credentials admin
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def login():
    """Se connecter en tant qu'admin"""
    print("🔐 Connexion admin...")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Connexion réussie!")
        print(f"   Réponse: {data}")
        
        # Essayer différents formats de réponse
        if "data" in data and isinstance(data["data"], dict) and "access_token" in data["data"]:
            token = data["data"]["access_token"]
        elif "access_token" in data:
            token = data["access_token"]
        else:
            print(f"❌ Format de réponse inattendu")
            print(data)
            sys.exit(1)
        
        return token
    else:
        print(f"❌ Erreur connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)

def check_migration_status(token):
    """Vérifier le statut des migrations"""
    print("\n📊 Vérification du statut des migrations...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/migrations/status",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Statut: {data.get('status')}")
        print(f"   Version actuelle: {data.get('current_version', 'Aucune')}")
        print(f"   Migrations totales: {data.get('total_migrations')}")
        print(f"   Migrations en attente: {data.get('pending_migrations')}")
        
        if data.get('pending_details'):
            print("\n📋 Migrations en attente:")
            for migration in data['pending_details']:
                print(f"   - {migration['revision']}: {migration['description']}")
        
        return data
    else:
        print(f"❌ Erreur statut: {response.status_code}")
        print(response.text)
        return None

def apply_migrations(token):
    """Appliquer les migrations"""
    print("\n🚀 Application des migrations...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/migrations/apply",
        headers=headers,
        timeout=120  # Timeout long pour les migrations
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Migrations appliquées avec succès!")
        print(f"   Message: {data.get('message')}")
        print(f"   Version finale: {data.get('current_version')}")
        print(f"   Migrations appliquées: {data.get('applied_migrations')}/{data.get('total_migrations')}")
        
        if data.get('results'):
            print("\n📋 Détails des migrations:")
            for result in data['results']:
                status_icon = "✅" if result['status'] == 'success' else "❌"
                print(f"   {status_icon} {result['revision']}: {result.get('message')}")
                if result['status'] == 'success':
                    print(f"      Exécutées: {result.get('executed')}, Ignorées: {result.get('skipped')}")
                else:
                    print(f"      Erreur: {result.get('error')}")
        
        return True
    else:
        print(f"❌ Erreur application: {response.status_code}")
        print(response.text)
        return False

def test_access_requests(token):
    """Tester que l'endpoint access-requests fonctionne maintenant"""
    print("\n🧪 Test de l'endpoint access-requests...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/access-requests/",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        print("✅ L'endpoint access-requests fonctionne!")
        data = response.json()
        print(f"   Demandes d'accès: {data.get('data', {}).get('total', 0)}")
        return True
    else:
        print(f"❌ Erreur test: {response.status_code}")
        print(response.text[:500])
        return False

def main():
    print("=" * 70)
    print("APPLICATION DES MIGRATIONS - AZURE PRODUCTION")
    print("=" * 70)
    
    # 1. Connexion
    token = login()
    
    # 2. Vérifier le statut
    status = check_migration_status(token)
    
    if not status:
        print("\n❌ Impossible de vérifier le statut")
        sys.exit(1)
    
    # 3. Appliquer les migrations si nécessaire
    if status.get('pending_migrations', 0) > 0:
        if apply_migrations(token):
            print("\n⏳ Attente de 5 secondes...")
            time.sleep(5)
            
            # 4. Tester l'endpoint
            test_access_requests(token)
        else:
            print("\n❌ Échec de l'application des migrations")
            sys.exit(1)
    else:
        print("\n✅ Aucune migration en attente")
        
        # Tester quand même l'endpoint
        test_access_requests(token)
    
    print("\n" + "=" * 70)
    print("🎉 TERMINÉ!")
    print("=" * 70)

if __name__ == "__main__":
    main()

