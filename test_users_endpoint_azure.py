"""
Script de test pour l'endpoint GET /users/{user_id} sur Azure
==============================================================
Teste l'endpoint en production pour identifier l'erreur 500
"""
import asyncio
import httpx
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

# Credentials pour se connecter (à adapter selon votre compte test)
TEST_CREDENTIALS = {
    "email": "admin@seeg-gabon.com",  # Adapter avec vos credentials
    "password": "votre_mot_de_passe"   # Adapter avec votre mot de passe
}

async def test_users_endpoint():
    """
    Test complet de l'endpoint GET /users/{user_id}.
    """
    print("\n" + "="*80)
    print("🧪 TEST ENDPOINT GET /users/{user_id} - PRODUCTION AZURE")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # ========================================================================
        # ÉTAPE 1: Connexion et récupération du token
        # ========================================================================
        print("\n📝 ÉTAPE 1: Connexion à l'API...")
        print(f"   URL: {API_BASE_URL}/api/v1/auth/login")
        
        try:
            login_response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json=TEST_CREDENTIALS
            )
            
            if login_response.status_code != 200:
                print(f"❌ Erreur connexion: {login_response.status_code}")
                print(f"   Réponse: {login_response.text}")
                print("\n💡 Conseil: Vérifiez vos credentials dans TEST_CREDENTIALS")
                return
            
            login_data = login_response.json()
            access_token = login_data["access_token"]
            user_info = login_data.get("user", {})
            current_user_id = user_info.get("id")
            
            print(f"✅ Connexion réussie")
            print(f"   Utilisateur: {user_info.get('email')}")
            print(f"   Rôle: {user_info.get('role')}")
            print(f"   User ID: {current_user_id}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la connexion: {e}")
            return
        
        # Headers avec authentification
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # ========================================================================
        # ÉTAPE 2: Test GET /users/me (profil actuel)
        # ========================================================================
        print("\n📝 ÉTAPE 2: Test GET /users/me...")
        print(f"   URL: {API_BASE_URL}/api/v1/users/me")
        
        try:
            me_response = await client.get(
                f"{API_BASE_URL}/api/v1/users/me",
                headers=headers
            )
            
            print(f"   Status: {me_response.status_code}")
            
            if me_response.status_code == 200:
                print(f"✅ GET /users/me fonctionne")
                me_data = me_response.json()
                print(f"   Données: {json.dumps(me_data, indent=2, ensure_ascii=False)[:300]}...")
            else:
                print(f"❌ Erreur {me_response.status_code}")
                print(f"   Réponse: {me_response.text[:500]}")
        
        except Exception as e:
            print(f"❌ Erreur GET /users/me: {e}")
        
        # ========================================================================
        # ÉTAPE 3: Test GET /users/{user_id} (endpoint problématique)
        # ========================================================================
        if current_user_id:
            print("\n📝 ÉTAPE 3: Test GET /users/{user_id}...")
            print(f"   URL: {API_BASE_URL}/api/v1/users/{current_user_id}")
            
            try:
                user_response = await client.get(
                    f"{API_BASE_URL}/api/v1/users/{current_user_id}",
                    headers=headers
                )
                
                print(f"   Status: {user_response.status_code}")
                
                if user_response.status_code == 200:
                    print(f"✅ GET /users/{{user_id}} fonctionne")
                    user_data = user_response.json()
                    print(f"   Données reçues:")
                    print(json.dumps(user_data, indent=2, ensure_ascii=False)[:500])
                    print("\n🎉 ENDPOINT FONCTIONNEL !")
                    
                elif user_response.status_code == 500:
                    print(f"❌ ERREUR 500 - Internal Server Error")
                    print(f"\n📋 Détails de l'erreur:")
                    try:
                        error_data = user_response.json()
                        print(json.dumps(error_data, indent=2, ensure_ascii=False))
                    except:
                        print(user_response.text)
                    
                    print("\n🔍 Analyse possible:")
                    print("   1. Problème de désérialisation (from_orm)")
                    print("   2. Erreur dans UserResponse ou CandidateProfileResponse")
                    print("   3. Problème de chargement du profil candidat")
                    print("   4. Version ancienne déployée avec bug")
                    
                else:
                    print(f"⚠️ Code inattendu: {user_response.status_code}")
                    print(f"   Réponse: {user_response.text[:500]}")
            
            except Exception as e:
                print(f"❌ Exception lors du test: {e}")
                import traceback
                traceback.print_exc()
        
        # ========================================================================
        # ÉTAPE 4: Test GET /users (liste des utilisateurs)
        # ========================================================================
        print("\n📝 ÉTAPE 4: Test GET /users/ (liste)...")
        print(f"   URL: {API_BASE_URL}/api/v1/users/?limit=5")
        
        try:
            users_response = await client.get(
                f"{API_BASE_URL}/api/v1/users/?limit=5",
                headers=headers
            )
            
            print(f"   Status: {users_response.status_code}")
            
            if users_response.status_code == 200:
                print(f"✅ GET /users/ fonctionne")
                users_data = users_response.json()
                total = users_data.get("total", 0)
                print(f"   Total utilisateurs: {total}")
                
                # Tester sur le premier utilisateur de la liste
                if users_data.get("data") and len(users_data["data"]) > 0:
                    first_user_id = users_data["data"][0].get("id")
                    print(f"\n   Test sur premier utilisateur: {first_user_id}")
                    
                    user_test_response = await client.get(
                        f"{API_BASE_URL}/api/v1/users/{first_user_id}",
                        headers=headers
                    )
                    
                    print(f"   Status: {user_test_response.status_code}")
                    
                    if user_test_response.status_code == 200:
                        print(f"   ✅ Fonctionne sur premier utilisateur")
                    else:
                        print(f"   ❌ Erreur {user_test_response.status_code}")
                        print(f"   Réponse: {user_test_response.text[:300]}")
            else:
                print(f"❌ Erreur {users_response.status_code}")
        
        except Exception as e:
            print(f"❌ Erreur GET /users/: {e}")
    
    print("\n" + "="*80)
    print("🏁 TEST TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    print("💡 Ce script teste l'endpoint GET /users/{user_id} sur Azure")
    print("   API: https://seeg-backend-api.azurewebsites.net")
    print("\n⚠️  IMPORTANT: Modifiez TEST_CREDENTIALS avec vos credentials valides")
    print("   (ligne 14-17 du script)")
    
    asyncio.run(test_users_endpoint())

