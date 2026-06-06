from .database import DatabaseManager
import logging
from typing import Dict, Any

class SentinelService:
    """
    Servicio de interfaz para el Sistema Sentinel.
    Permite que la aplicación solicite acciones al orquestador maestro (Sentinel)
    mediante una cola de comandos en la base de datos global.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger("SentinelService")
        self._init_command_table()

    def _init_command_table(self):
        """Crea la tabla de comandos para el Sentinel si no existe."""
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS sentinel_commands (
                id SERIAL PRIMARY KEY,
                command TEXT NOT NULL,
                params TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    def request_action(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Envía una solicitud de acción al proceso Sentinel.
        Como el Sentinel es el padre, el hijo (app) escribe la orden en la DB.
        """
        try:
            import json
            params_json = json.dumps(params) if params else None
            self.db.execute(
                "INSERT INTO sentinel_commands (command, params) VALUES (%s, %s)",
                (command, params_json)
            )
            self.logger.info(f"Solicitud enviada al Sentinel: {command}")
            return {"status": "success", "message": f"Solicitud {command} enviada al Sentinel."}
        except Exception as e:
            self.logger.error(f"Error solicitando acción al Sentinel: {e}")
            return {"status": "error", "message": str(e)}

    def get_sentinel_status(self) -> Dict[str, Any]:
        """Consulta el estado de los comandos enviados al Sentinel."""
        commands = self.db.fetch_all(
            "SELECT * FROM sentinel_commands ORDER BY created_at DESC LIMIT 10"
        )
        return {"status": "success", "data": [dict(c) for c in commands]}

