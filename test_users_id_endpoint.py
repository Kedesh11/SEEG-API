"""
Test spécifique de l'endpoint GET /users/{user_id} en production
=================================================================
"""
import asyncio
import httpx
import json

API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

async def test_users_id_endpoint():
    """
    Test l'endpoint GET /users/{user_id} qui retourne une erreur 500.
    """
    print("\n" + "="*80)
    print("🧪 TEST ENDPOINT: GET /api/v1/users/{user_id}")
    print("="*80)
    print(f"\nAPI: {API_BASE_URL}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print("\n📝 ÉTAPE 1: Connexion avec utilisateur existant...")
        
        login_data = {
            "email": "sevankedesh11@gmail.com",
            "password": "Sevan@Seeg"
        }
        
        try:
            login_response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json=login_data
            )
            
            print(f"   Status connexion: {login_response.status_code}")
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                access_token = login_result.get("access_token")
                user_info = login_result.get("user", {})
                test_user_id = user_info.get("id")
                
                print(f"   ✅ Connexion réussie")
                print(f"   Email: {user_info.get('email')}")
                print(f"   Rôle: {user_info.get('role')}")
                print(f"   User ID: {test_user_id}")
                
                # Maintenant testons l'endpoint problématique
                headers = {"Authorization": f"Bearer {access_token}"}
                
                print(f"\n📝 ÉTAPE 2: Test GET /users/{test_user_id}...")
                print(f"   URL: {API_BASE_URL}/api/v1/users/{test_user_id}")
                
                user_response = await client.get(
                    f"{API_BASE_URL}/api/v1/users/{test_user_id}",
                    headers=headers
                )
                
                print(f"   Status: {user_response.status_code}")
                
                if user_response.status_code == 200:
                    print(f"\n✅✅✅ SUCCÈS ! L'endpoint fonctionne !")
                    user_data = user_response.json()
                    print(f"\n📊 Données reçues:")
                    print(json.dumps(user_data, indent=2, ensure_ascii=False))
                    
                elif user_response.status_code == 500:
                    print(f"\n❌❌❌ ERREUR 500 CONFIRMÉE")
                    print(f"\n📋 Détails de l'erreur:")
                    print(user_response.text)
                    
                    print(f"\n🔍 DIAGNOSTIC:")
                    print(f"   Cause probable: Utilisation de from_orm() (Pydantic v1)")
                    print(f"   Au lieu de: model_validate() (Pydantic v2)")
                    print(f"   Fichier: app/api/v1/endpoints/users.py ligne ~221")
                    print(f"\n   Solution: Redéployer avec le code corrigé")
                    
                else:
                    print(f"\n⚠️  Status inattendu: {user_response.status_code}")
                    print(f"   Réponse: {user_response.text[:300]}")
            
            elif login_response.status_code == 401:
                print(f"   ❌ Credentials invalides")
                print(f"   Réponse: {login_response.text[:200]}")
                print(f"\n   💡 Vérifiez l'email et le mot de passe")
                
            else:
                print(f"   ❌ Erreur connexion: {login_response.status_code}")
                print(f"   Réponse: {login_response.text[:300]}")
        
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("🏁 TEST TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    print("\n💡 Ce script teste spécifiquement GET /users/{user_id}")
    print("   Il crée un utilisateur de test temporaire pour obtenir un token")
    asyncio.run(test_users_id_endpoint())

