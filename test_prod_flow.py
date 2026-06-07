
import requests
import json

BASE_URL = "https://bubbly-laughter-production-123a.up.railway.app/"

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
        
        # The API seems to return payload in a 'payload' field based on simulate_flow.py
        payload = data.get('payload', {})
        print(f"DEBUG: Login response payload: {payload}")
        
        if payload.get('status') == 'success':
            # Try different common token locations
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

    # The system uses 'token' in the request body for most commands
    
    print("\n--- 2. Search Product ---")
    # Try searching for something common or just any character to see if we get results
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
