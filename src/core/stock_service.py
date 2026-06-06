from .database import DatabaseManager
import logging
from typing import List, Dict, Any

class StockService:
    """
    Servicio de negocio para la gestión de productos e inventario.
    Encapsula la lógica de validación y manipulación de datos de stock.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger("StockService")

    def add_product(self, codigo, nombre, precio, cantidad, categoria, es_peso=False):
        """
        Agrega un producto al inventario. 
        Si el código ya existe, se actualiza el producto (Upsert).
        """
        try:
            # Validaciones básicas
            if not codigo or not nombre or precio is None:
                return {"status": "error", "message": "Código, nombre y precio son obligatorios."}

            query = '''
                INSERT INTO products (codigo, nombre, precio, cantidad, categoria, es_peso)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre=excluded.nombre,
                    precio=excluded.precio,
                    cantidad=excluded.cantidad,
                    categoria=excluded.categoria,
                    es_peso=excluded.es_peso,
                    last_updated=CURRENT_TIMESTAMP
            '''
            params = (codigo, nombre, precio, cantidad, categoria, True if es_peso else False)
            self.db.execute(query, params)
            
            self.logger.info(f"Producto procesado: {nombre} ({codigo})")
            return {"status": "success", "message": f"Producto {nombre} guardado correctamente."}
        except Exception as e:
            self.logger.error(f"Error adding product {codigo}: {e}")
            return {"status": "error", "message": str(e)}

    def get_product(self, codigo):
        """Obtiene los detalles de un producto específico."""
        query = "SELECT * FROM products WHERE codigo = %s"
        product = self.db.fetch_one(query, (codigo,))
        if product:
            return {"status": "success", "data": dict(product)}
        return {"status": "error", "message": "Producto no encontrado."}

    def list_products(self, filter_text=None, category=None):
        """
        Retorna la lista de productos con filtros opcionales.
        Mantiene la coherencia con la funcionalidad de búsqueda del repo original.
        """
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if filter_text:
            query += " AND (nombre LIKE %s OR codigo LIKE %s)"
            params.extend([f"%{filter_text}%", f"%{filter_text}%"])
        
        if category:
            query += " AND categoria = %s"
            params.append(category)
            
        query += " ORDER BY nombre ASC"
        
        products = self.db.fetch_all(query, tuple(params))
        return {"status": "success", "data": [dict(p) for p in products]}

    def update_stock(self, codigo, amount):
        """
        Actualiza la cantidad de stock. 
        'amount' puede ser positivo (entrada) o negativo (salida/venta).
        """
        try:
            # Primero verificamos si el producto existe
            product = self.get_product(codigo)
            if product["status"] == "error":
                return product

            current_qty = product["data"]["cantidad"]
            new_qty = current_qty + amount

            if new_qty < 0:
                return {"status": "error", "message": f"Stock insuficiente. Disponible: {current_qty}"}

            query = "UPDATE products SET cantidad = %s, last_updated = CURRENT_TIMESTAMP WHERE codigo = %s"
            self.db.execute(query, (new_qty, codigo))
            
            self.logger.info(f"Stock actualizado: {codigo} | Cambio: {amount} | Nuevo Total: {new_qty}")
            return {"status": "success", "message": f"Stock actualizado. Nuevo total: {new_qty}"}
        except Exception as e:
            self.logger.error(f"Error updating stock for {codigo}: {e}")
            return {"status": "error", "message": str(e)}

    def delete_product(self, codigo):
        """Elimina un producto del inventario."""
        try:
            query = "DELETE FROM products WHERE codigo = %s"
            self.db.execute(query, (codigo,))
            return {"status": "success", "message": "Producto eliminado correctamente."}
        except Exception as e:
            self.logger.error(f"Error deleting product {codigo}: {e}")
            return {"status": "error", "message": str(e)}

    def get_low_stock(self, threshold=5):
        """
        Retorna productos cuyo stock es inferior al umbral definido.
        Copia la lógica de alertas del original.
        """
        query = "SELECT * FROM products WHERE cantidad < %s ORDER BY cantidad ASC"
        products = self.db.fetch_all(query, (threshold,))
        return {"status": "success", "data": [dict(p) for p in products]}

    def bulk_add_products(self, products_list: List[Dict[str, Any]]):
        """
        Agrega múltiples productos en una sola transacción.
        Optimiza drásticamente la velocidad de importación.
        """
        try:
            query = '''
                INSERT INTO products (codigo, nombre, precio, cantidad, categoria, es_peso)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre=excluded.nombre,
                    precio=excluded.precio,
                    cantidad=excluded.cantidad,
                    categoria=excluded.categoria,
                    es_peso=excluded.es_peso,
                    last_updated=CURRENT_TIMESTAMP
            '''
            
            params_list = []
            for p in products_list:
                params_list.append((
                    p.get('codigo'),
                    p.get('nombre'),
                    p.get('precio'),
                    p.get('cantidad'),
                    p.get('categoria'),
                    True if p.get('es_peso') else False
                ))
            
            # Usamos el gestor de DB para ejecutar masivamente
            # Necesitamos que DatabaseManager tenga un método execute_many
            if hasattr(self.db, 'execute_many'):
                self.db.execute_many(query, params_list)
            else:
                # Fallback: iterar (menos eficiente pero seguro)
                for params in params_list:
                    self.db.execute(query, params)
            
            self.logger.info(f"Bulk import completed: {len(products_list)} products processed.")
            return {"status": "success", "message": f"Se procesaron {len(products_list)} productos masivamente."}
        except Exception as e:
            self.logger.error(f"Error in bulk_add_products: {e}")
            return {"status": "error", "message": str(e)}

