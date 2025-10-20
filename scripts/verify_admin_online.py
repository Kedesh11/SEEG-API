import requests

API_URL = "https://seeg-backend-api.azurewebsites.net/api/v1/auth/login"
LOGIN_DATA = {
    "username": "sevankedesh11@gmail.com",
    "password": "Sevan@Seeg"
}

response = requests.post(API_URL, data=LOGIN_DATA)

if response.status_code == 200:
    print("Connexion admin OK :", response.json())
else:
    print(f"Erreur {response.status_code}: {response.text}")
