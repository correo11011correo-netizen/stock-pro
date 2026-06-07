import sqlite3
import logging
import json

class MockCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.last_row = None

    def execute(self, query, params=()):
        # Traducir placeholders de PostgreSQL (%s) a SQLite (?)
        query = query.replace("%s", "?")
        
        # Interceptar RETURNING id que usa PostgreSQL y simularlo para SQLite
        returning_id = False
        if "RETURNING id" in query:
            query = query.replace("RETURNING id", "")
            returning_id = True

        self.cursor.execute(query, params)
        
        if returning_id:
            self.last_row = (self.cursor.lastrowid,)
        else:
            self.last_row = None

    def fetchone(self):
        if self.last_row:
            val = self.last_row
            self.last_row = None
            return val
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

class MockConnection:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()

    def cursor(self):
        return MockCursor(self.conn.cursor())

# Mocking the database for Stock Pro local test
class MockDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE products (codigo TEXT PRIMARY KEY, nombre TEXT, precio REAL, cantidad INTEGER, categoria TEXT)')
        cursor.execute('CREATE TABLE sales (id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, cliente TEXT, metodo_pago TEXT, paga_con REAL, vuelto REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE sale_items (sale_id INTEGER, product_codigo TEXT, cantidad INTEGER, precio_unitario REAL)')
        
        # Seed data
        cursor.execute("INSERT INTO products VALUES ('P001', 'Coca Cola 1.5L', 1500.0, 10, 'Bebidas')")
        cursor.execute("INSERT INTO products VALUES ('P002', 'Pepsi 1.5L', 1400.0, 5, 'Bebidas')")
        self.conn.commit()

    def _get_connection(self):
        return MockConnection(self.conn)

    def fetch_all(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def execute(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.lastrowid

def test_sales_search_and_cart():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SALES_TEST")
    
    logger.info("🚀 Iniciando Test de Búsqueda y Venta de 2 Ítems...")
    
    db = MockDB()
    from src.core.stock_service import StockService
    from src.core.sales_service import SalesService
    from src.commands.dispatcher import CommandDispatcher
    
    stock_service = StockService(db)
    sales_service = SalesService(db, stock_service)
    # Mock System and Auth for dispatcher
    class MockS:
        def __getattr__(self, name): return lambda *a, **k: {"status": "success"}
    
    dispatcher = CommandDispatcher(db, stock_service, sales_service, MockS(), MockS())

    # 1. TEST DE BÚSQUEDA (Simulando autocompletado del frontend)
    logger.info("🧪 Paso 1: Buscando productos con término 'Cola'...")
    search_res = dispatcher.execute(
        "venta.search", 
        {"search": "Cola"}, 
        current_user_role="empleado", 
        user_permissions={"perm_sales_create"}
    )
    
    if search_res.get("status") == "success" and len(search_res.get("data", [])) > 0:
        logger.info(f"✅ ÉXITO: Se encontró {search_res['data'][0]['nombre']} correctamente.")
    else:
        logger.error(f"❌ FALLO: No se encontraron productos en la búsqueda. {search_res}")

    # 2. AGREGAR AL CARRITO (Simulando selección de 2 productos)
    logger.info("🧪 Paso 2: Agregando 2 productos al carrito...")
    # Producto 1: Coca Cola
    item1 = search_res["data"][0]
    # Producto 2: Pepsi (buscamos por código directo)
    item2_res = dispatcher.execute(
        "stock.get", 
        {"codigo": "P002"}, 
        current_user_role="empleado", 
        user_permissions={"perm_stock_read"}
    )
    item2 = item2_res["data"]

    cart = [
        {"codigo": item1["codigo"], "nombre": item1["nombre"], "precio": item1["precio"], "cantidad": 1, "subtotal": item1["precio"]},
        {"codigo": item2["codigo"], "nombre": item2["nombre"], "precio": item2["precio"], "cantidad": 1, "subtotal": item2["precio"]}
    ]
    
    logger.info(f"🛒 Carrito preparado con {len(cart)} productos.")
    for i in cart:
        logger.info(f"   - {i['nombre']} | Cantidad: {i['cantidad']} | Precio: ${i['precio']}")

    # 3. PROCESAR VENTA (Simulando botón Finalizar Venta)
    logger.info("🧪 Paso 3: Procesando el cobro de la venta...")
    total_venta = sum(i["subtotal"] for i in cart)
    
    sale_res = dispatcher.execute(
        "venta.cobrar", 
        {
            "items": cart,
            "metodo_pago": "efectivo",
            "paga_con": 3000.0
        },
        current_user_role="empleado",
        user_permissions={"perm_sales_process"}
    )

    if sale_res["status"] == "success":
        logger.info(f"✅ ÉXITO: Venta procesada. Total: ${total_venta}. Vuelto: ${sale_res.get('vuelto', 0)}")
    else:
        logger.error(f"❌ FALLO: Error al cobrar la venta. {sale_res}")

    # 4. VERIFICAR STOCK (Debería haber disminuido)
    logger.info("🧪 Paso 4: Verificando actualización de stock...")
    p1 = db.fetch_one("SELECT cantidad FROM products WHERE codigo = 'P001'")
    p2 = db.fetch_one("SELECT cantidad FROM products WHERE codigo = 'P002'")
    
    if p1["cantidad"] == 9 and p2["cantidad"] == 4:
        logger.info("✅ ÉXITO: El stock se actualizó correctamente tras vender ambos ítems.")
    else:
        logger.error(f"❌ FALLO: Stock incorrecto. P1: {p1['cantidad']}, P2: {p2['cantidad']}")

    logger.info("🏁 Test de flujo de ventas completado exitosamente.")

if __name__ == "__main__":
    test_sales_search_and_cart()
