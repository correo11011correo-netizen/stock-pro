import sys
import os
import logging

# Configurar logging para ver la salida en consola
logging.basicConfig(level=logging.INFO)

# Asegurar que el root del proyecto esté en el path
sys.path.append(os.getcwd())

from src.core.database import DatabaseManager
from src.core.stock_service import StockService
from src.core.import_service import ImportService

def run_test():
    print("--- Iniciando Test de Importación Universal ---")
    
    # Inicializar dependencias
    db = DatabaseManager(db_path="projects/stock-scan-python/data/stock_pro.db")
    stock_service = StockService(db)
    import_service = ImportService(stock_service)

    # 1. Ejecutar importación usando el perfil 'pos_generic_excel'
    print("\n1. Ejecutando import_stock...")
    result = import_service.import_stock(
        file_path="projects/stock-scan-python/data/test_stock.csv",
        mapping_id="pos_generic_excel"
    )
    print(f"Resultado: {result}")

    # 2. Verificar productos en la DB
    print("\n2. Verificando productos insertados...")
    products = db.fetch_all("SELECT * FROM products WHERE codigo IN ('A1', 'A2', 'A3')")
    for p in products:
        print(f"Producto: {p['codigo']} | {p['nombre']} | Precio: {p['precio']} | Peso: {p['es_peso']}")

    # 3. Verificar logs de auditoría (Trazabilidad)
    print("\n3. Verificando Logs de Auditoría (Tabla 'audit')...")
    # Buscamos los logs relacionados con la importación
    logs = db.fetch_all("SELECT id, accion, detalle FROM audit WHERE accion LIKE 'IMPORT%' ORDER BY id DESC LIMIT 20")
    for l in logs:
        print(f"[{l['id']}] {l['accion']} -> {l['detalle']}")


if __name__ == "__main__":
    run_test()
