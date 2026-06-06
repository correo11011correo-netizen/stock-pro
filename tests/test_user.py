import requests
import json
from datetime import datetime
import uuid

URL = "http://localhost:8888/"

def log_res(step, status, message):
    icon = "✅" if status == "success" else "❌"
    print(f"{icon} [{step}] -> {message}")

def test_user_lifecycle():
    print("👤 INICIANDO VALIDACIÓN DE CICLO DE VIDA DE USUARIO")
    print("="*60)
    
    # 1. Registro de Dueño (OWNER)
    username = f"biz_owner_{uuid.uuid4().hex[:6]}"
    password = "OwnerPass123!"
    biz_name = f"My Store {uuid.uuid4().hex[:4]}"
    
    print(f"📝 Registrando negocio: {biz_name}...")
    res_reg = requests.post(URL, json={
        "command": "auth.register_owner", 
        "params": {"username": username, "password": password, "business_name": biz_name}
    })
    data_reg = res_reg.json().get("payload", res_reg.json())
    
    if data_reg.get("status") != "success":
        print(f"❌ Error en registro: {data_reg.get('message')}")
        return
    
    tenant_id = data_reg.get("tenant_id")
    print(f"✅ Negocio creado: {tenant_id}
")

    # 2. Login
    print(f"🔑 Autenticando usuario {username}...")
    res_login = requests.post(URL, json={
        "command": "auth.login", 
        "params": {"username": username, "password": password}
    })
    data_login = res_login.json().get("payload", res_login.json())
    
    if data_login.get("status") != "success":
        print(f"❌ Error en login: {data_login.get('message')}")
        return
    
    token = data_login.get("token")
    headers = {"Authorization": token}
    print("✅ Sesión activa.
")

    # 3. Gestión de Stock (Añadir Producto)
    print("📦 Probando Gestión de Stock...")
    prod_codigo = f"PROD_{uuid.uuid4().hex[:4].upper()}"
    res_stock = requests.post(URL, json={
        "command": "stock.add", 
        "params": {
            "codigo": prod_codigo,
            "nombre": "Producto de Prueba",
            "precio": 150.0,
            "cantidad": 10,
            "categoria": "General"
        }
    }, headers=headers)
    data_stock = res_stock.json().get("payload", res_stock.json())
    log_res("stock.add", data_stock.get("status"), f"Producto {prod_codigo} añadido")

    # 4. Flujo de Venta
    print("
💰 Probando Flujo de Ventas...")
    
    # 4.1 Crear venta
    res_v_new = requests.post(URL, json={"command": "venta.nueva", "params": {}}, headers=headers)
    log_res("venta.nueva", res_v_new.json().get("payload", res_v_new.json()).get("status"), "Carrito creado")

    # 4.2 Añadir producto a la venta
    res_v_add = requests.post(URL, json={
        "command": "venta.add", 
        "params": {"codigo": prod_codigo}
    }, headers=headers)
    log_res("venta.add", res_v_add.json().get("payload", res_v_add.json()).get("status"), f"Añadido {prod_codigo}")

    # 4.3 Cobrar la venta
    res_v_pay = requests.post(URL, json={
        "command": "venta.cobrar", 
        "params": {
            "cliente": "Cliente Test",
            "items": [{"codigo": prod_codigo, "cantidad": 1}],
            "metodo_pago": "Efectivo",
            "paga_con": 200.0
        }
    }, headers=headers)
    data_pay = res_v_pay.json().get("payload", res_v_pay.json())
    log_res("venta.cobrar", data_pay.get("status"), f"Venta cobrada. Vuelto: {data_pay.get('data', {}).get('vuelto')}")

    print("
" + "="*60)
    print("🏁 VALIDACIÓN DE USUARIO FINAL FINALIZADA")
    print("="*60)

if __name__ == "__main__":
    test_user_lifecycle()
