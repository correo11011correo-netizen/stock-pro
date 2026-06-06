import logging
from typing import List, Dict, Any
from src.core.database import DatabaseManager
from src.core.stock_service import StockService
from src.core.sales_service import SalesService

class SyncService:
    """
    Servicio encargado de la sincronización bidireccional con dispositivos móviles.
    Procesa colas de eventos offline y genera deltas de actualización de stock.
    """
    def __init__(self, db: DatabaseManager, stock_service: StockService, sales_service: SalesService):
        self.db = db
        self.stock_service = stock_service
        self.sales_service = sales_service
        self.logger = logging.getLogger("SyncService")

    def process_push_events(self, user_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Procesa una lista de eventos enviados desde el dispositivo móvil.
        """
        processed_count = 0
        errors = []

        for event in events:
            action = event.get("action")
            data = event.get("data")
            
            try:
                if action == "venta.nueva":
                    # Adaptamos la data de la app al formato de SalesService
                    # En una implementación real, validaríamos el stock disponible aquí
                    result = self.sales_service.process_sale(
                        cliente="Cliente Móvil",
                        items=data.get("items", []),
                        metodo_pago="Efectivo (Offline)",
                        paga_con=0, # Se ajustaría según la data
                        alias=None
                    )
                    if result["status"] == "error":
                        errors.append(f"Venta fallida: {result['message']}")
                    else:
                        processed_count += 1
                
                elif action == "stock.update":
                    # Actualización de stock manual desde el móvil
                    self.stock_service.update_stock(
                        codigo=data.get("codigo"),
                        amount=data.get("amount")
                    )
                    processed_count += 1
                
                else:
                    errors.append(f"Acción no soportada: {action}")
            
            except Exception as e:
                self.logger.error(f"Error procesando evento {action}: {e}")
                errors.append(f"Error crítico en {action}: {str(e)}")

        return {
            "status": "success" if not errors else "partial_success",
            "processed": processed_count,
            "errors": errors
        }

    def get_stock_delta(self) -> List[Dict[str, Any]]:
        """
        Retorna la lista de productos actualizada para que la app actualice su caché.
        En una versión optimizada, solo enviaría los productos modificados desde la última sync.
        """
        products = self.stock_service.list_products()
        if products["status"] == "success":
            # Simplificamos la data para el móvil
            return [
                {
                    "codigo": p["codigo"],
                    "nombre": p["nombre"],
                    "precio": p["precio"],
                    "cantidad": p["cantidad"]
                }
                for p in products["data"]
            ]
        return []
