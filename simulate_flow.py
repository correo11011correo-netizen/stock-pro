
import requests
import json

BASE_URL = "http://localhost:8888/"

def simulate():
    session = requests.Session()
    
    print("--- 1. Simulating Login ---")
    login_payload = {
        "command": "auth.login",
        "username": "asd",
        "password": "asd" # Assuming password is 'asd' based on user input
    }
    try:
        res = session.post(BASE_URL, json=login_payload)
        data = res.json()
        if data['payload']['status'] == 'success':
            token = data['payload']['user'].get('token') or data['payload'].get('token')
            # If token is not in payload, it might be handled by the session/cookie, 
            # but the app uses 'Authorization' header or 'token' in body.
            print(f"✅ Login successful. Token: {token}")
        else:
            print(f"❌ Login failed: {data['payload'].get('message')}")
            return
    except Exception as e:
        print(f"💥 Error during login: {e}")
        return

    # Note: For subsequent requests, the app usually expects the token in the body or Authorization header.
    # I'll use the 'token' in the body as seen in the RAW BODY logs.
    
    print("\n--- 2. Simulating Add Stock (Testing 'Missing Fields' Fix) ---")
    stock_payload = {
        "command": "stock.add",
        "token": token,
        "codigo": "PROD-TEST-01",
        "nombre": "Producto de Prueba",
        "precio": 150.50,
        "cantidad": 10,
        "categoria": "Electronica",
        "es_peso": False
    }
    try:
        res = session.post(BASE_URL, json=stock_payload)
        data = res.json()
        print(f"Result: {data['payload']}")
    except Exception as e:
        print(f"💥 Error adding stock: {e}")

    print("\n--- 3. Simulating Product Search ---")
    search_payload = {
        "command": "stock.list",
        "token": token,
        "filter": "Prueba"
    }
    try:
        res = session.post(BASE_URL, json=search_payload)
        data = res.json()
        print(f"Result: {data['payload']}")
    except Exception as e:
        print(f"💥 Error searching: {e}")

    print("\n--- 4. Simulating Sale Process ---")
    sale_payload = {
        "command": "venta.nueva", # This is just a trigger in app.js, but let's try a conceptual sale
        "token": token,
        "params": {
            "items": [
                {"codigo": "PROD-TEST-01", "cantidad": 1, "precio": 150.50}
            ],
            "total": 150.50
        }
    }
    # The actual endpoint for sales in the app is /api/sync/push with action 'venta.nueva'
    try:
        res = session.post(f"{BASE_URL}api/sync/push", json={
            "events": [{
                "action": "venta.nueva",
                "data": {
                    "items": [{"codigo": "PROD-TEST-01", "nombre": "Producto de Prueba", "precio": 150.50, "cantidad": 1, "subtotal": 150.50}],
                    "total": 150.50,
                    "user_id": "asd"
                }
            }]
        }, headers={"Authorization": token})
        data = res.json()
        print(f"Result: {data['payload']}")
    except Exception as e:
        print(f"💥 Error processing sale: {e}")

if __name__ == '__main__':
    simulate()
