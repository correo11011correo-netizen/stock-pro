from .database import DatabaseManager
from .stock_service import StockService
import logging
from datetime import datetime

class SalesService:
    """
    Servicio de negocio para la gestión de ventas y control de caja.
    Maneja el flujo desde el carrito hasta la liquidación contable.
    """
    
    def __init__(self, db: DatabaseManager, stock_service: StockService):
        self.db = db
        self.stock_service = stock_service
        self.logger = logging.getLogger("SalesService")

    # --- GESTIÓN DE CAJA (CASH BOX) ---

    def open_cash_box(self, monto_inicial):
        """Inicia el turno de caja con un monto de efectivo inicial."""
        try:
            query = '''
                UPDATE cash_box SET 
                    abierta = true, 
                    efectivo_inicial = %s, 
                    ventas_efectivo = 0, 
                    ventas_digital = 0, 
                    hora_apertura = CURRENT_TIMESTAMP,
                    hora_cierre = NULL,
                    monto_cierre_real = NULL
                WHERE id = 1
            '''
            self.db.execute(query, (monto_inicial,))
            self.logger.info(f"Caja abierta con monto inicial: ${monto_inicial}")
            return {"status": "success", "message": "Caja abierta correctamente."}
        except Exception as e:
            self.logger.error(f"Error opening cash box: {e}")
            return {"status": "error", "message": str(e)}

    def close_cash_box(self, monto_real):
        """Cierra el turno de caja y registra el monto real final."""
        try:
            # Obtener estado actual para auditoría
            estado = self.db.fetch_one("SELECT * FROM cash_box WHERE id = 1")
            if not estado or not estado['abierta']:
                return {"status": "error", "message": "La caja no está abierta."}

            query = '''
                UPDATE cash_box SET 
                    abierta = false, 
                    hora_cierre = CURRENT_TIMESTAMP,
                    monto_cierre_real = %s
                WHERE id = 1
            '''
            self.db.execute(query, (monto_real,))
            
            # Calcular diferencia
            esperado = estado['efectivo_inicial'] + estado['ventas_efectivo']
            diferencia = monto_real - esperado
            
            self.logger.info(f"Caja cerrada. Real: ${monto_real}, Esperado: ${esperado}, Dif: ${diferencia}")
            return {
                "status": "success", 
                "message": "Caja cerrada correctamente.",
                "resumen": {
                    "esperado": esperado,
                    "real": monto_real,
                    "diferencia": diferencia
                }
            }
        except Exception as e:
            self.logger.error(f"Error closing cash box: {e}")
            return {"status": "error", "message": str(e)}

    def get_cash_box_status(self):
        """Retorna el estado actual de la caja."""
        status = self.db.fetch_one("SELECT * FROM cash_box WHERE id = 1")
        return {"status": "success", "data": dict(status) if status else None}

    # --- PROCESO DE VENTAS ---

    def process_sale(self, cliente, items, metodo_pago, paga_con=0, alias=None):
        """
        Procesa una venta completa usando los métodos estables del DatabaseManager.
        """
        try:
            self.logger.info(f"📊 Iniciando proceso de venta. Items: {len(items)}, Método: {metodo_pago}")
            
            total_venta = 0
            processed_items = []
            
            for item in items:
                res = self.stock_service.get_product(item['codigo'])
                if res["status"] == "error":
                    return {"status": "error", "message": f"Producto {item['codigo']} no encontrado."}
                
                p = res["data"]
                if p['cantidad'] < item['cantidad']:
                    return {
                        "status": "error", 
                        "message": f"Stock insuficiente para {p['nombre']}. Disponible: {p['cantidad']}, Solicitado: {item['cantidad']}"
                    }

                subtotal = p['precio'] * item['cantidad']
                total_venta += subtotal
                processed_items.append({
                    "codigo": p['codigo'],
                    "cantidad": item['cantidad'],
                    "subtotal": subtotal
                })

            if metodo_pago == "Transferencia" and alias:
                alias_data = self.db.fetch_one("SELECT * FROM aliases WHERE nombre = %s", (alias,))
                if alias_data:
                    if (alias_data['acumulado'] or 0) + total_venta > alias_data['limite']:
                        return {"status": "error", "message": f"Límite excedido para el alias {alias}."}
                else:
                    return {"status": "error", "message": "Alias no registrado."}

            vuelto = 0
            if metodo_pago == "Efectivo":
                if paga_con < total_venta:
                    return {"status": "error", "message": "Monto insuficiente para pago en efectivo."}
                vuelto = paga_con - total_venta

            # Usamos execute() para evitar WinError 233 (manejo interno de pool)
            sale_id = self.db.execute('''
                INSERT INTO sales (total, cliente, metodo_pago, paga_con, vuelto)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (total_venta, cliente, metodo_pago, paga_con, vuelto))
            
            if not sale_id:
                return {"status": "error", "message": "Error al registrar la venta en la base de datos."}

            for pi in processed_items:
                self.db.execute('''
                    INSERT INTO sale_items (sale_id, product_codigo, cantidad, subtotal)
                    VALUES (%s, %s, %s, %s)
                ''', (sale_id, pi['codigo'], pi['cantidad'], pi['subtotal']))
            
            if metodo_pago == "Efectivo":
                self.db.execute("UPDATE cash_box SET ventas_efectivo = ventas_efectivo + %s WHERE id = 1", (total_venta,))
            else:
                self.db.execute("UPDATE cash_box SET ventas_digital = ventas_digital + %s WHERE id = 1", (total_venta,))
            
            if metodo_pago == "Transferencia" and alias:
                self.db.execute("UPDATE aliases SET acumulado = acumulado + %s WHERE nombre = %s", (total_venta, alias))

            for pi in processed_items:
                self.stock_service.update_stock(pi['codigo'], -pi['cantidad'])

            return {
                "status": "success", 
                "message": "Venta procesada exitosamente.",
                "sale_id": sale_id,
                "vuelto": vuelto
            }

        except Exception as e:
            self.logger.error(f"❌ Critical error processing sale: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # --- GESTIÓN DE ALIAS ---

    def add_alias(self, nombre, limite):
        """Crea un nuevo alias con un límite de crédito/recaudación."""
        try:
            self.logger.info(f"➕ Creando alias: {nombre} con límite: ${limite}")
            
            # Generar un ID simple
            import uuid
            alias_id = str(uuid.uuid4())[:8]
            
            self.logger.debug(f"   ID generado: {alias_id}")
            
            self.db.execute(
                "INSERT INTO aliases (id, nombre, limite, acumulado) VALUES (%s, %s, %s, 0)", 
                (alias_id, nombre, limite)
            )
            
            self.logger.info(f"✅ Alias creado exitosamente: {alias_id}")
            return {"status": "success", "message": f"Alias {nombre} creado."}
        except Exception as e:
            self.logger.error(f"❌ Error creando alias: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def delete_alias(self, alias_id):
        """Elimina un alias del sistema."""
        try:
            self.logger.info(f"🗑️ Eliminando alias: {alias_id}")
            self.db.execute("DELETE FROM aliases WHERE id = %s", (alias_id,))
            self.logger.info(f"✅ Alias eliminado: {alias_id}")
            return {"status": "success", "message": "Alias eliminado."}
        except Exception as e:
            self.logger.error(f"❌ Error eliminando alias: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def list_aliases(self):
        """Retorna todos los alias y sus consumos."""
        try:
            self.logger.info(f"📥 Listando alias...")
            aliases = self.db.fetch_all("SELECT * FROM aliases")
            self.logger.info(f"✅ {len(aliases)} alias encontrados")
            return {"status": "success", "data": [dict(a) for a in aliases]}
        except Exception as e:
            self.logger.error(f"❌ Error listando alias: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
