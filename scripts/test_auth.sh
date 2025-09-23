#!/bin/bash

echo "🔐 Test d'authentification API..."

# Test de création d'utilisateur
echo "📝 Création d'un utilisateur de test..."
SIGNUP_RESPONSE=$(curl -s -X POST "https://seeg-backend-api.azurewebsites.net/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@seeg-talentsource.com",
    "password": "Test123!",
    "first_name": "Test",
    "last_name": "User"
  }')

echo "Signup Response: $SIGNUP_RESPONSE"

# Test de connexion
echo "🔑 Tentative de connexion..."
LOGIN_RESPONSE=$(curl -s -X POST "https://seeg-backend-api.azurewebsites.net/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@seeg-talentsource.com",
    "password": "Test123!"
  }')

echo "Login Response: $LOGIN_RESPONSE"

# Extraire le token si disponible
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ ! -z "$TOKEN" ]; then
    echo "✅ Token obtenu: ${TOKEN:0:50}..."
    
    # Test d'un endpoint protégé
    echo "🔒 Test d'un endpoint protégé..."
    PROTECTED_RESPONSE=$(curl -s -X GET "https://seeg-backend-api.azurewebsites.net/api/v1/users/me" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "Protected endpoint response: $PROTECTED_RESPONSE"
else
    echo "❌ Échec de l'authentification"
fi
