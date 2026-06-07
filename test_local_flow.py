
import requests
import json

BASE_URL = "http://localhost:8888/"

def test_flow():
    session = requests.Session()
    
    print("--- 1. Login ---")
    login_payload = {
        "command": "auth.login",
        "username": "asd",
        "password": "asd"
    }
    try:
        res = session.post(BASE_URL, json=login_payload)
        res.raise_for_status()
        data = res.json()
        
        payload = data.get('payload', {})
        if payload.get('status') == 'success':
            token = payload.get('token') or payload.get('user', {}).get('token') or data.get('token')
            if token:
                print(f"✅ Login successful. Token: {token}")
            else:
                print(f"❌ Login successful but no token found in response. Response: {data}")
                return
        else:
            print(f"❌ Login failed: {payload.get('message')}")
            return
    except Exception as e:
        print(f"💥 Error during login: {e}")
        return

    print("\n--- 2. Search Product ---")
    search_payload = {
        "command": "venta.search",
        "token": token,
        "search": "a" 
    }
    try:
        res = session.post(BASE_URL, json=search_payload)
        res.raise_for_status()
        data = res.json()
        payload = data.get('payload', {})
        
        if payload.get('status') == 'success' and payload.get('data'):
            products = payload.get('data')
            product = products[0]
            print(f"✅ Found {len(products)} products. Testing with: {product['nombre']} ({product['codigo']})")
        else:
            print(f"❌ Search failed or no products found: {payload.get('message')}")
            return
    except Exception as e:
        print(f"💥 Error during search: {e}")
        return

    print("\n--- 3. Add to Cart ---")
    add_payload = {
        "command": "venta.add",
        "token": token,
        "codigo": product['codigo']
    }
    try:
        res = session.post(BASE_URL, json=add_payload)
        res.raise_for_status()
        data = res.json()
        payload = data.get('payload', {})
        
        if payload.get('status') == 'success':
            print(f"✅ Product {product['nombre']} added to cart successfully!")
        else:
            print(f"❌ Add to cart failed: {payload.get('message')}")
    except Exception as e:
        print(f"💥 Error during add to cart: {e}")

if __name__ == '__main__':
    test_flow()
