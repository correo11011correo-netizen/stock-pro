import os
from src.core.global_db import GlobalDatabaseManager
from src.core.database import DatabaseManager
from src.core.stock_service import StockService

os.environ["DATABASE_URL"] = "postgresql://postgres:ThHGlEAhaKKprgVhDbnaNaektrgZuIth@acela.proxy.rlwy.net:16919/railway"

def seed_products():
    print("📦 Sembrando productos de prueba en el tenant...")
    global_db = GlobalDatabaseManager()
    
    # Buscamos el tenant de dueno_test
    tenant = global_db.fetch_one("SELECT schema_name FROM tenants t JOIN users u ON t.id = u.tenant_id WHERE u.username = 'dueno_test'", ())
    if not tenant:
        print("❌ Error: No se encontró el tenant para dueno_test.")
        return

    schema = tenant["schema_name"]
    print(f"Sembrando en esquema: {schema}")
    
    db = DatabaseManager(schema_name=schema)
    stock_svc = StockService(db)
    
    products = [
        {"codigo": "P001", "nombre": "Laptop Gamer", "precio": 1200.00, "cantidad": 10},
        {"codigo": "P002", "nombre": "Mouse Optico", "precio": 25.00, "cantidad": 50},
        {"codigo": "P003", "nombre": "Teclado Mecanico", "precio": 80.00, "cantidad": 30},
    ]
    
    for p in products:
        try:
            stock_svc.update_stock(p["codigo"], p["cantidad"])
            # Forzamos la inserción del nombre y precio si no existen (usando el db manager directamente)
            db.execute(
                "INSERT INTO products (codigo, nombre, precio, cantidad) VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO UPDATE SET nombre=excluded.nombre, precio=excluded.precio, cantidad=excluded.cantidad",
                (p["codigo"], p["nombre"], p["precio"], p["cantidad"])
            )
            print(f"✅ Producto {p['codigo']} sembrado.")
        except Exception as e:
            print(f"⚠️ Error sembrando {p['codigo']}: {e}")

    print("🏁 Sembrado completado.")

if __name__ == "__main__":
    seed_products()
