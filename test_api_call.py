import requests
import json

url = "http://localhost:8888/"
payload = {
    "command": "auth.register_owner",
    "params": {
        "username": "admin_test",
        "password": "Password123!",
        "business_name": "Tienda de Prueba"
    }
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
