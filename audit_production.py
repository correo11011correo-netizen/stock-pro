import requests
import json
import uuid
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_URL = "https://stock-scan-python-production.up.railway.app"
TEST_USER = f"audit_admin_{uuid.uuid4().hex[:6]}"
TEST_PASS = "AuditPass2026!"
TEST_BIZ = "Audit Test Store"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("ProdAudit")

class ProdAuditSuite:
    def __init__(self):
        self.token = None
        self.tenant_id = None
        self.results = []

    def log_result(self, test_name, success, message=""):
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        self.results.append({"test": test_name, "status": status, "msg": message})
        logger.info(f"{status} | {test_name} {f'({message})' if message else ''}")

    def api_call(self, command, params=None, headers=None):
        if params is None: params = {}
        if headers is None: headers = {}
        
        if self.token:
            headers['Authorization'] = self.token

        payload = {
            "command": command,
            "params": params
        }
        
        try:
            # Railway usa HTTPS, requests lo maneja automáticamente
            response = requests.post(BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("payload", response.json())
            return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_all(self):
        logger.info(f"🚀 Iniciando Auditoría de Producción en {BASE_URL}")
        
        # 1. AUTH FLOW
        # Registro de Dueño
        res = self.api_call("auth.register_owner", {"username": TEST_USER, "password": TEST_PASS, "business_name": TEST_BIZ})
        if res.get("status") == "success":
            self.log_result("Registro de Dueño", True)
        else:
            self.log_result("Registro de Dueño", False, res.get("message"))
            return # Detener si no podemos registrarnos

        # Login
        res = self.api_call("auth.login", {"username": TEST_USER, "password": TEST_PASS})
        if res.get("status") == "success" and "token" in res:
            self.token = res["token"]
            self.log_result("Login de Dueño", True)
        else:
            self.log_result("Login de Dueño", False, res.get("message"))
            return

        # 2. STOCK FLOW
        # Agregar producto
        prod = {"codigo": "AUDIT01", "nombre": "Producto Test", "precio": 100.0, "cantidad": 10, "categoria": "General"}
        res = self.api_call("stock.add", prod)
        self.log_result("Agregar Producto", res.get("status") == "success", res.get("message"))

        # Consultar producto
        res = self.api_call("stock.get", {"codigo": "AUDIT01"})
        self.log_result("Consultar Producto", res.get("status") == "success", res.get("message"))

        # Actualizar cantidad
        res = self.api_call("stock.update_qty", {"codigo": "AUDIT01", "amount": 5})
        self.log_result("Actualizar Stock", res.get("status") == "success", res.get("message"))

        # 3. SALES FLOW
        # Abrir Caja
        res = self.api_call("caja.abrir", {"monto_inicial": 1000})
        self.log_result("Abrir Caja", res.get("status") == "success", res.get("message"))

        # Venta
        sale_items = [{"codigo": "AUDIT01", "cantidad": 2}]
        res = self.api_call("venta.cobrar", {
            "cliente": "Cliente Test",
            "items": sale_items,
            "metodo_pago": "efectivo",
            "paga_con": 250,
            "alias": None
        })
        self.log_result("Procesar Venta", res.get("status") == "success", res.get("message"))

        # Validar que el stock bajó (10 + 5 - 2 = 13)
        res = self.api_call("stock.get", {"codigo": "AUDIT01"})
        if res.get("status") == "success":
            qty = res["data"].get("cantidad")
            self.log_result("Consistencia de Stock Post-Venta", qty == 13, f"Cantidad encontrada: {qty}")
        else:
            self.log_result("Consistencia de Stock Post-Venta", False, "No se pudo obtener el stock")

        # 4. SYSTEM & PRO FLOW
        # Info del sistema
        res = self.api_call("sys.info")
        self.log_result("Consulta Info Sistema", res.get("status") == "success")

        # Reportes (Debería fallar si el plan es FREE por defecto)
        res = self.api_call("reporte.resumen")
        if res.get("status") == "error" and "PRO" in res.get("message", ""):
            self.log_result("Validación Bloqueo PRO", True, "Acceso denegado correctamente")
        else:
            self.log_result("Validación Bloqueo PRO", False, "El sistema permitió acceso a reporte PRO en plan FREE")

        # 5. SECURITY FLOW
        # Intento de comando sin token
        res = self.api_call("stock.list", headers={}) # Forzar sin token
        if "Sesión no válida" in res.get("message", ""):
            self.log_result("Seguridad: Bloqueo sin Token", True)
        else:
            self.log_result("Seguridad: Bloqueo sin Token", False, res.get("message"))

        # Resumen Final
        print("\n" + "="*50)
        print(f"RESUMEN DE AUDITORÍA - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*50)
        passed = sum(1 for r in self.results if r["status"] == "✅ PASÓ")
        total = len(self.results)
        for r in self.results:
            print(f"{r['status']} | {r['test']}: {r['msg']}")
        print("="*50)
        print(f"RESULTADO FINAL: {passed}/{total} pruebas pasaron.")
        print("="*50)

if __name__ == "__main__":
    suite = ProdAuditSuite()
    suite.run_all()
