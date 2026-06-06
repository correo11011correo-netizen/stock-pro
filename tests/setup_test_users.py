import os
from src.core.global_db import GlobalDatabaseManager
from src.core.auth_service import AuthService
from src.commands.dispatcher import CommandDispatcher
from src.core.database import DatabaseManager
from src.core.stock_service import StockService
from src.core.sales_service import SalesService
from src.core.system_service import SystemService

# Configurar DATABASE_URL para conectar con Railway
os.environ["DATABASE_URL"] = "postgresql://postgres:ThHGlEAhaKKprgVhDbnaNaektrgZuIth@acela.proxy.rlwy.net:16919/railway"

def setup_users():
    print("🚀 Configurando usuarios de prueba en Railway...")
    
    # 1. Inicializar Infraestructura Global
    global_db = GlobalDatabaseManager()
    auth_service = AuthService(global_db)
    
    # 2. Crear Usuario Dueño
    db = DatabaseManager(schema_name="public")
    stock = StockService(db)
    sales = SalesService(db, stock)
    sys_svc = SystemService(db)
    
    dispatcher = CommandDispatcher(db, stock, sales, sys_svc, auth_service)
    
    # Crear Dueño
    try:
        res = dispatcher.execute("auth.register_owner", {
            "username": "dueno_test",
            "password": "Password123!",
            "business_name": "Test Store"
        })
        print(f"Result Dueño dueno_test: {res['status']}")
    except Exception as e:
        print(f"Aviso al crear dueño: {e}")

    # Crear Empleado (Usando el método directo del AuthService para evitar errores de dispatcher)
    try:
        # Buscar el tenant creado para el dueño
        owner_data = auth_service.global_db.fetch_one(
            "SELECT tenant_id FROM users WHERE username = 'dueno_test'", ()
        )
        if owner_data:
            tenant_id = owner_data["tenant_id"]
            res = auth_service.create_employee_account("empleado_test", "Password123!", tenant_id)
            print(f"Result Empleado empleado_test: {res['status']}")
        else:
            print("❌ Error: No se encontró el tenant del dueño.")
    except Exception as e:
        print(f"⚠️ Error al crear empleado: {e}")

    print("✅ Proceso de configuración finalizado.")

if __name__ == "__main__":
    setup_users()
