import requests
import json

def simulate_api_call(command, data=None):
    url = "http://localhost:8888/"
    token = None # Simulando sesión no iniciada
    
    # Replica exacta de la lógica de app.js -> apiCall()
    payload = {
        "command": command,
        "token": token,
    }
    if data:
        payload.update(data)
        
    print(f"📤 ENVIANDO PAYLOAD: {json.dumps(payload)}")
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers={"Content-Type": "application/json"}
        )
        print(f"📩 RESPUESTA SERVIDOR: Status {response.status_code}")
        print(f"📄 CUERPO: {response.text}")
        return response.status_code, response.json()
    except Exception as e:
        print(f"❌ ERROR DE RED: {e}")
        return None, None

if __name__ == "__main__":
    print("--- TEST 1: Login (Simulando app.js) ---")
    # app.js envía: { username: user, password: pass }
    simulate_api_call("auth.login", {"username": "adrian", "password": "password123"})
    
    print("\n--- TEST 2: Registro (Simulando app.js) ---")
    # app.js envía: { business_name: biz, username: user, password: pass }
    simulate_api_call("auth.register_owner", {
        "business_name": "TestBiz", 
        "username": "testuser", 
        "password": "password123"
    })
