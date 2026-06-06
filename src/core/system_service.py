from .database import DatabaseManager
import csv
import os
import logging
from datetime import datetime

class SystemService:
    """
    Servicio encargado de la administración del sistema, auditoría y configuraciones.
    Proporciona trazabilidad de acciones y persistencia de preferencias.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger("SystemService")
        self.version = "1.0.0-native"

    # --- SISTEMA DE AUDITORÍA (MIGración de registrarAuditoria) ---

    def log_event(self, usuario, accion, detalle):
        """
        Registra un evento en la tabla de auditoría.
        Este es el corazón de la trazabilidad del sistema.
        """
        try:
            query = "INSERT INTO audit (usuario, accion, detalle) VALUES (%s, %s, %s)"
            self.db.execute(query, (usuario, accion, detalle))
            # También lo enviamos al logger de Python para debug en tiempo real
            self.logger.info(f"AUDIT | User: {usuario} | Action: {accion} | Detail: {detalle}")
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error writing to audit log: {e}")
            return {"status": "error", "message": str(e)}

    # --- GESTIÓN DE CONFIGURACIONES (SISTEMA DE PREFERENCIAS) ---

    def set_setting(self, key, value):
        """Guarda una configuración en la base de datos (ej: tema, idioma)."""
        try:
            query = '''
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            '''
            self.db.execute(query, (key, str(value)))
            return {"status": "success", "message": f"Configuración {key} actualizada."}
        except Exception as e:
            self.logger.error(f"Error setting {key}: {e}")
            return {"status": "error", "message": str(e)}

    def get_setting(self, key, default=None):
        """Recupera una configuración específica."""
        query = "SELECT value FROM settings WHERE key = %s"
        res = self.db.fetch_one(query, (key,))
        if res:
            return {"status": "success", "value": res['value']}
        return {"status": "success", "value": default}

    # --- EXPORTACIÓN DE DATOS ---

    def export_inventory_to_csv(self):
        """
        Exporta el inventario actual a un archivo CSV.
        Copia la funcionalidad de exportación del original pero con datos de SQLite.
        """
        try:
            products = self.db.fetch_all("SELECT * FROM products ORDER BY nombre ASC")
            if not products:
                return {"status": "error", "message": "No hay productos para exportar."}

            # Resolver ruta de exportación (dinámica PC/Android)
            export_dir = "exports"
            if os.path.exists("/data/data/com.stockscan.app/files"):
                export_path = f"/data/data/com.stockscan.app/files/{export_dir}/inventory_export.csv"
            else:
                # En PC, buscamos la carpeta del proyecto
                cwd = os.getcwd()
                export_path = os.path.join(cwd, "exports", "inventory_export.csv")

            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            with open(export_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Cabeceras
                writer.writerow(['Código', 'Nombre', 'Precio', 'Cantidad', 'Categoría', 'Es Peso', 'Última Actualización'])
                
                for p in products:
                    writer.writerow([
                        p['codigo'], 
                        p['nombre'], 
                        p['precio'], 
                        p['cantidad'], 
                        p['categoria'], 
                        "SÍ" if p['es_peso'] else "NO", 
                        p['last_updated']
                    ])

            self.logger.info(f"Inventory exported successfully to {export_path}")
            return {"status": "success", "path": export_path, "message": "Inventario exportado a CSV."}
        except Exception as e:
            self.logger.error(f"Export Error: {e}")
            return {"status": "error", "message": str(e)}

    def get_system_info(self):
        """Retorna información básica del sistema."""
        return {
            "status": "success",
            "version": self.version,
            "timestamp": datetime.now().isoformat()
        }

