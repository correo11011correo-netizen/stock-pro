import requests
import json
from datetime import datetime
import uuid

URL = "http://localhost:8888/"

def log_res(cmd, status, message):
    icon = "✅" if status == "success" else "❌"
    print(f"{icon} [{cmd}] -> Status: {status} | {message}")

def test_comprehensive_master_flow():
    print("🛡️  INICIANDO VALIDACIÓN EXHAUSTIVA DE PANEL MASTER")
    print("="*60)
    
    # 1. Setup de Master
    master_user = f"master_{datetime.now().strftime('%S%f')}"
    master_pass = "MasterSecret123!"
    
    print(f"🔑 Creando cuenta MASTER: {master_user}...")
    res_setup = requests.post(URL + "api/admin/setup", json={"username": master_user, "password": master_pass})
    if res_setup.status_code != 200:
        print(f"⚠️  Setup master: {res_setup.text}")
    else:
        print("✅ MASTER creado exitosamente.")

    # 2. Login Master
    print(f"🔑 Autenticando MASTER...")
    login_res = requests.post(URL, json={"command": "auth.login", "params": {"username": master_user, "password": master_pass}})
    data = login_res.json().get("payload", login_res.json())
    
    if data.get("status") != "success":
        print(f"❌ Error Login Master: {data.get('message')}")
        return

    token = data.get("token")
    headers = {"Authorization": token}
    print("✅ Sesión MASTER activa.\n")

    # ---------------------------------------------------------
    # 3. CREACIÓN DE UN TENANT PARA PRUEBAS (EL OBJETIVO)
    # ---------------------------------------------------------
    print("🏢 Creando Tenant de prueba para validaciones administrativas...")
    owner_user = f"owner_{uuid.uuid4().hex[:6]}"
    owner_pass = "OwnerPass123!"
    biz_name = "Test Corp Global"
    
    res_owner = requests.post(URL, json={
        "command": "auth.register_owner", 
        "params": {"username": owner_user, "password": owner_pass, "business_name": biz_name}
    }, headers=headers)
    
    owner_data = res_owner.json().get("payload", res_owner.json())
    if owner_data.get("status") != "success":
        print(f"❌ Error creando tenant: {owner_data.get('message')}")
        return
    
    tenant_id = owner_data.get("tenant_id")
    print(f"✅ Tenant creado: {tenant_id} ({biz_name})\n")

    # ---------------------------------------------------------
    # 4. PRUEBAS DE ADMINISTRACIÓN GLOBAL (Suscripciones y Créditos)
    # ---------------------------------------------------------
    print("💰 Probando Gestión de Suscripciones y Créditos...")
    
    # Elevar a plan PRO y sumar créditos
    res_sub = requests.post(URL, json={
        "command": "sys.subscription.update", 
        "params": {"tenant_id": tenant_id, "plan": "PRO", "credits": 100}
    }, headers=headers)
    
    sub_data = res_sub.json().get("payload", res_sub.json())
    log_res("sys.subscription.update", sub_data.get("status"), sub_data.get("message"))

    # ---------------------------------------------------------
    # 5. PRUEBAS DE GESTIÓN DE PERSONAL
    # ---------------------------------------------------------
    print("\n👥 Probando Gestión de Personal...")
    
    emp_user = f"emp_{uuid.uuid4().hex[:6]}"
    res_emp = requests.post(URL, json={
        "command": "user.invite_employee", 
        "params": {"username": emp_user, "password": "EmpPass123!", "tenant_id": tenant_id}
    }, headers=headers)
    
    emp_data = res_emp.json().get("payload", res_emp.json())
    log_res("user.invite_employee", emp_data.get("status"), emp_data.get("message"))
    
    user_id = emp_data.get("user_id")
    if user_id:
        # Asignar permiso de lectura de stock
        res_perm = requests.post(URL, json={
            "command": "user.set_permission", 
            "params": {"tenant_id": tenant_id, "user_id": user_id, "permission_key": "perm_stock_read", "granted": True}
        }, headers=headers)
        perm_data = res_perm.json().get("payload", res_perm.json())
        log_res("user.set_permission", perm_data.get("status"), perm_data.get("message"))

    # ---------------------------------------------------------
    # 6. PRUEBAS DE SISTEMA Y AUDITORÍA
    # ---------------------------------------------------------
    print("\n⚙️  Probando Comandos de Sistema...")
    
    sys_tests = [
        ("sys.info", {}),
        ("sys.admin.users_list", {}),
        ("logs.view", {"limit": 10}),
        ("sys.sentinel.status", {}),
    ]

    for cmd, params in sys_tests:
        res = requests.post(URL, json={"command": cmd, "params": params}, headers=headers)
        resp_data = res.json().get("payload", res.json())
        log_res(cmd, resp_data.get("status"), resp_data.get("message", "OK"))

    # ---------------------------------------------------------
    # 7. PRUEBAS DE DEBUG (God Mode)
    # ---------------------------------------------------------
    print("\n🛠️  Probando Debug Call (Acceso Directo a Servicios)...")
    
    debug_tests = [
        {"service": "auth", "method": "get_system_stats", "args": {}},
        {"service": "system", "method": "get_system_info", "args": {}},
    ]

    for dt in debug_tests:
        res = requests.post(URL, json={
            "command": "debug.call", 
            "params": {"service": dt["service"], "method": dt["method"], "args": dt["args"]}
        }, headers=headers)
        resp_data = res.json().get("payload", res.json())
        log_res(f"debug.{dt['service']}.{dt['method']}", resp_data.get("status"), "Datos recibidos" if resp_data.get("status") == "success" else resp_data.get("message"))

    print("\n" + "="*60)
    print("🏁 VALIDACIÓN COMPLETA FINALIZADA")
    print("="*60)

if __name__ == "__main__":
    test_comprehensive_master_flow()
