from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

VAULT_URL = "https://seeg-api.vault.azure.net/"
SECRET_NAME = "WEBHOOK-ADMIN-TOKEN"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)

secret = client.get_secret(SECRET_NAME)
print(f"{SECRET_NAME} = {secret.value}")
