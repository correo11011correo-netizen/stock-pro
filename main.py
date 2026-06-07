import logging
import sys
import os
from dotenv import load_dotenv
from src.core.database import DatabaseManager
from src.core.global_db import GlobalDatabaseManager
from src.core.auth_service import AuthService
from src.core.stock_service import StockService
from src.core.sales_service import SalesService
from src.core.system_service import SystemService
from src.commands.dispatcher import CommandDispatcher
from src.ui.web_server import WebServer

def setup_logging():
    """Configura el sistema de logging profesional."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuración del log para archivo (DEBUG)
    file_handler = logging.FileHandler(os.path.join(log_dir, "system.log"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

    # Configuración del log para consola/Render (INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

    logging.basicConfig(
        level=logging.DEBUG, # Nivel global de logging
        handlers=[file_handler, stream_handler]
    )

    # Captura global de excepciones no manejadas
    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # No registrar KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Excepción no manejada:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_unhandled_exception
    logging.info("Logging system initialized.")

def main():
    """
    Punto de entrada principal del Sistema de Stock y Escaneo.
    Orquestra la carga de todos los componentes en orden.
    """
    load_dotenv()
    setup_logging()
    logger = logging.getLogger("Main")
    logger.info("🚀 Iniciando Sistema de Stock y Escaneo (Multi-Tenant)...")

    try:
        # 1. Inicializar Infraestructura Global
        global_db = GlobalDatabaseManager()
        auth_service = AuthService(global_db)
        logger.info("✅ Infraestructura Global y Auth Service cargados.")

        # 2. Inicializar Base de Datos y Servicios por Defecto (Modo Fallback/Admin)
        # Estos se usan para configuraciones globales o cuando no hay sesión activa
        db = DatabaseManager()
        stock_service = StockService(db)
        sales_service = SalesService(db, stock_service)
        system_service = SystemService(db)
        
        # 3. Inicializar Orquestador de Comandos (Dispatcher)
        dispatcher = CommandDispatcher(
            db=db, 
            stock_service=stock_service, 
            sales_service=sales_service, 
            system_service=system_service,
            auth_service=auth_service
        )
        logger.info("✅ Command Dispatcher operativo.")

        # 4. Inicializar Interfaz de Usuario (Web Server)
        # Ahora pasamos auth_service para que el servidor gestione las sesiones y tenants
        port = int(os.environ.get("PORT", 8888))
        web_server = WebServer(
            dispatcher=dispatcher, 
            auth_service=auth_service, 
            port=port
        )
        web_server.start()
        logger.info(f"✅ Servidor Web iniciado en puerto {port}")

        logger.info("🌟 SISTEMA COMPLETAMENTE OPERATIVO")
        logger.info(f"🔐 Panel de Administración disponible en: http://0.0.0.0:{port}/admin")
        logger.info("   → Para crear la cuenta MASTER por primera vez, visita /admin y usa 'Configuración Inicial'.")
        logger.info("   → O llama a: auth_service.create_master_account(username, password)")
        logger.info("Presione Ctrl+C para detener el servidor.")

    except KeyboardInterrupt:
        logger.info("🛑 Deteniendo el sistema...")
        if 'web_server' in locals():
            web_server.stop()
        sys.exit(0)
    except Exception as e:
        logger.critical(f"❌ Error fatal durante el arranque: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
