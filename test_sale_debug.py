
import requests
import json

BASE_URL = "http://localhost:8888/"

def test_full_sale():
    session = requests.Session()
    
    print("--- 1. Login ---")
    login_payload = {
        "command": "auth.login",
        "username": "asd",
        "password": "asd"
    }
    try:
        res = session.post(BASE_URL, json=login_payload)
        data = res.json()
        payload = data.get('payload', {})
        token = payload.get('token') or payload.get('user', {}).get('token') or data.get('token')
        print(f"✅ Login successful. Token: {token}")
    except Exception as e:
        print(f"💥 Login failed: {e}")
        return

    print("\n--- 2. Search Product ---")
    search_payload = {
        "command": "venta.search",
        "token": token,
        "search": "a" 
    }
    try:
        res = session.post(BASE_URL, json=search_payload)
        payload = res.json().get('payload', {})
        products = payload.get('data')
        if not products:
            print("❌ No products found")
            return
        product = products[0]
        print(f"✅ Found: {product['nombre']} ({product['codigo']})")
    except Exception as e:
        print(f"💥 Search failed: {e}")
        return

    print("\n--- 3. Add to Cart ---")
    add_payload = {
        "command": "venta.add",
        "token": token,
        "codigo": product['codigo']
    }
    try:
        res = session.post(BASE_URL, json=add_payload)
        print(f"✅ Added to cart: {res.json().get('payload', {}).get('status')}")
    except Exception as e:
        print(f"💥 Add failed: {e}")
        return

    print("\n--- 4. Confirm Sale (Cobrar) ---")
    cobrar_payload = {
        "command": "venta.cobrar",
        "token": token,
        "params": {
            "cliente": "General",
            "items": [{"codigo": product['codigo'], "cantidad": 1}],
            "metodo_pago": "Efectivo",
            "paga_con": 1000, # Sufficient amount
            "alias": None
        }
    }
    # Note: Our apiCall in JS sends params and root fields mixed. Let's try both formats.
    # Try format 1: Params in root
    cobrar_payload_root = {
        "command": "venta.cobrar",
        "token": token,
        "cliente": "General",
        "items": [{"codigo": product['codigo'], "cantidad": 1}],
        "metodo_pago": "Efectivo",
        "paga_con": 1000,
        "alias": None
    }
    
    try:
        print("Trying root params format...")
        res = session.post(BASE_URL, json=cobrar_payload_root)
        result = res.json().get('payload', {})
        if result.get('status') == 'success':
            print(f"✅ SALE SUCCESSFUL! ID: {result.get('sale_id')}, Vuelto: {result.get('vuelto')}")
        else:
            print(f"❌ SALE FAILED: {result.get('message')}")
            print(f"Response: {result}")
    except Exception as e:
        print(f"💥 Error during cobrar: {e}")

if __name__ == '__main__':
    test_full_sale()
