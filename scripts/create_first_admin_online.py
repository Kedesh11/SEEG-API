import requests

API_URL = "https://seeg-backend-api.azurewebsites.net/api/v1/auth/create-first-admin"

response = requests.post(API_URL)

if response.status_code == 200:
    print("Admin créé avec succès :", response.json())
elif response.status_code == 400:
    print("Un administrateur existe déjà.")
else:
    print(f"Erreur {response.status_code}: {response.text}")
