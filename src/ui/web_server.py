import json
import logging
import os
import mimetypes
import email
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from threading import Thread
from datetime import datetime
from decimal import Decimal
from email.parser import BytesParser
from ..commands.dispatcher import CommandDispatcher

class DecimalEncoder(json.JSONEncoder):
    """Encoder personalizado para serializar Decimal y datetime a tipos JSON-compatibles."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class WebAPIHandler(BaseHTTPRequestHandler):
    """
    Handler de API y Servidor de Archivos Estáticos.
    Conecta el Frontend HTML con el Command Dispatcher y sirve la UI.
    Soporta multi-tenancy mediante la resolución dinámica de bases de datos.
    """
    
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def log_message(self, format, *args):
        """Override to prevent OSError [Errno 5] when running in background."""
        logging.info(format % args)

    def _json_response(self, data, status=200):
        """Estandariza todas las respuestas JSON de la API."""
        response = {
            "timestamp": datetime.now().isoformat(),
            "payload": data
        }
        self._set_headers(status)
        self.wfile.write(json.dumps(response, cls=DecimalEncoder).encode())

    def do_OPTIONS(self):
        self._set_headers()

    def _require_master(self):
        """Valida que el token de la petición pertenezca a un usuario MASTER.
        Retorna (user_session, None) si es válido, o (None, error_response) si no."""
        token = self.headers.get('Authorization')
        user_session = self.auth_service.validate_session(token)
        if not user_session:
            return None, {"status": "error", "message": "Sesión no válida o expirada."}
        if user_session.get("role") != "MASTER":
            return None, {"status": "error", "message": "Acceso denegado. Se requiere rol MASTER."}
        return user_session, None

    def do_GET(self):
        logging.info(f"📩 GET Request: {self.path}")
        ui_dir = os.path.dirname(__file__)
        
        # Normalizar ruta: eliminar query strings para la comprobación de archivos estáticos
        clean_path = self.path.split('?')[0]

        # --- APP WEB PWA (Nueva versión híbrida) ---
        if clean_path.startswith('/appweb'):
            rel_path = clean_path.replace('/appweb/', '').lstrip('/')
            if not rel_path or rel_path == '':
                file_path = os.path.join(ui_dir, "appweb", "index.html")
            else:
                file_path = os.path.join(ui_dir, "appweb", rel_path)
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    mime_type, _ = mimetypes.guess_type(file_path)
                    content = Path(file_path).read_bytes()
                    self.send_response(200)
                    self.send_header('Content-type', mime_type or 'application/octet-stream')
                    self.send_header('Content-Length', len(content))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    logging.error(f"Error sirviendo appweb {file_path}: {e}")
                    self.send_error(500, f"Error interno: {e}")
                    return

        # --- ADMIN DASHBOARD (serve HTML) ---

            if clean_path == '/admin' or clean_path == '/admin/' or (clean_path.startswith('/admin/') and not clean_path.startswith('/api/')):
                # Si es /admin o una subruta no-API, servimos el dashboard
                file_path = os.path.join(ui_dir, "admin_dashboard.html")
                if os.path.exists(file_path):
                    try:
                        content = Path(file_path).read_bytes()
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', len(content))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception as e:
                        self.send_error(500, f"Error interno: {e}")
                        return
                else:
                    self.send_error(404, "Admin dashboard no encontrado")
                    return

        # --- ADMIN API (GET endpoints, all require MASTER role) ---

        # --- ADMIN API (GET endpoints, all require MASTER role) ---

        # --- ADMIN API (GET endpoints, all require MASTER role) ---
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        def qs_int(key, default):
            return int(qs[key][0]) if key in qs else default

        def qs_str(key, default=""):
            return qs[key][0] if key in qs else default

        if path.startswith('/api/admin/'):
            user_session, err = self._require_master()
            if err:
                return self._json_response(err, 403)

            admin_id = user_session["id"]

            # GET /api/admin/dashboard
            if path == '/api/admin/dashboard':
                result = self.auth_service.get_system_stats()
                self.auth_service.log_admin_action(admin_id, "VIEW_DASHBOARD", "")
                return self._json_response(result)

            # GET /api/admin/tenants
            if path == '/api/admin/tenants':
                page = qs_int('page', 1)
                per_page = qs_int('per_page', 20)
                search = qs_str('search')
                result = self.auth_service.get_all_tenants(page=page, per_page=per_page, search=search)
                return self._json_response(result)

            # GET /api/admin/tenants/{tenant_id}
            if path.startswith('/api/admin/tenants/') and len(path.split('/')) == 5:
                tenant_id = path.split('/')[-1]
                result = self.auth_service.get_tenant_detail(tenant_id)
                return self._json_response(result)

            # GET /api/admin/users
            if path == '/api/admin/users':
                page = qs_int('page', 1)
                per_page = qs_int('per_page', 30)
                search = qs_str('search')
                result = self.auth_service.get_all_users_paginated(page=page, per_page=per_page, search=search)
                return self._json_response(result)

            # GET /api/admin/audit-logs
            if path == '/api/admin/audit-logs':
                page = qs_int('page', 1)
                per_page = qs_int('per_page', 50)
                result = self.auth_service.get_admin_logs(page=page, per_page=per_page)
                return self._json_response(result)

            return self._json_response({"status": "error", "message": "Endpoint admin no encontrado."}, 404)

        if self.path == '/':
            file_path = os.path.join(ui_dir, "index.html")
        else:
            # Soporte para descarga de archivos CSV
            if self.path.startswith('/download/') and self.path.endswith('.csv'):
                # El path viene como /download/home/adrian/...
                abs_path = self.path.replace('/download/', '', 1)
                if os.path.exists(abs_path) and os.path.isfile(abs_path):
                    try:
                        content = Path(abs_path).read_bytes()
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/csv')
                        self.send_header('Content-Disposition', f'attachment; filename={os.path.basename(abs_path)}')
                        self.send_header('Content-Length', len(content))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception as e:
                        logging.error(f"Error sirviendo CSV {abs_path}: {e}")
                        self.send_error(500, f"Error interno: {e}")
                        return
            
            rel_path = self.path.lstrip('/')
            if rel_path.startswith('src/ui/'):
                rel_path = rel_path.replace('src/ui/', '', 1)
            file_path = os.path.join(ui_dir, rel_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                content = Path(file_path).read_bytes()
                self.send_response(200)
                self.send_header('Content-type', mime_type or 'application/octet-stream')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                logging.error(f"Error sirviendo archivo {file_path}: {e}")
                self.send_error(500, f"Error interno: {e}")
                return

        if self.path == '/api/config':
            res = self.dispatcher.execute("sys.info")
            return self._json_response(res)
        
        if self.path == '/api/health':
            return self._json_response({"status": "healthy", "server": "StockScan-API", "version": "2.0"})
        
        self.send_error(404, "Endpoint o archivo no encontrado")

    def do_POST(self):
        # --- LOGGING DE PETICIONES POST ---
        from urllib.parse import urlparse
        parsed_post = urlparse(self.path)
        post_path = parsed_post.path
        content_type = self.headers.get('Content-Type', '')
        
        # 🔐 LOG: Extrae y loguea el token recibido
        token = self.headers.get('Authorization', '')
        token_preview = f"Token: {token[:20]}..." if token else "Sin token"
        logging.info(f"📩 POST Request: {post_path} | Content-Type: {content_type} | {token_preview}")

        # 1. Leer el cuerpo de la petición UNA SOLA VEZ
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length)
            # 🔍 DEBUG EXTREMO: Loguear exactamente qué llega del cliente
            logging.info(f"RAW BODY RECEIVED: {raw_body.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logging.exception(f"Error leyendo cuerpo de petición POST: {e}")
            return self._json_response({"status": "error", "message": "Error al leer el cuerpo de la petición"}, 400)

        # 2. Parsear datos según el Content-Type
        data = {}
        if 'application/json' in content_type:
            try:
                if raw_body:
                    data = json.loads(raw_body.decode('utf-8'))
            except json.JSONDecodeError as e:
                logging.exception(f"JSONDecodeError en {post_path}: {e}")
                return self._json_response({"status": "error", "message": "JSON inválido"}, 400)

        command = data.get("command")
        params = data.get("params", {})
        
        # 🔍 DEBUG DETALLADO
        logging.debug(f"📦 DATA RECIBIDA: command='{command}' | params={params}")

        # --- MANEJO DE ARCHIVOS (UPLOAD) ---
        # Este endpoint requiere el cuerpo crudo (bytes) y multipart/form-data
        if post_path == '/api/upload':
            try:
                if 'multipart/form-data' not in content_type:
                    return self._json_response({"status": "error", "message": "Content-Type debe ser multipart/form-data"}, 400)
                
                if not raw_body:
                    return self._json_response({"status": "error", "message": "Cuerpo de petición vacío"}, 400)

                parser = BytesParser()
                msg = parser.parsebytes(
                    f"Content-Type: {content_type}\r\n\r\n".encode() + raw_body
                )
                
                file_item = None
                for part in msg.get_payload():
                    if part.get_filename():
                        file_item = part
                        break
                
                if not file_item:
                    return self._json_response({"status": "error", "message": "No se recibió ningún archivo válido."}, 400)
                
                filename_orig = file_item.get_filename()
                content = file_item.get_payload(decode=True)
                
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                upload_dir = os.path.join(base_dir, "data", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                
                filename = f"upload_{int(datetime.now().timestamp())}_{filename_orig}"
                full_path = os.path.join(upload_dir, filename)
                
                with open(full_path, 'wb') as f:
                    f.write(content)
                
                logging.info(f"Archivo subido exitosamente: {full_path}")
                return self._json_response({"status": "success", "path": full_path})
            except Exception as e:
                logging.exception(f"Error en upload: {e}")
                return self._json_response({"status": "error", "message": str(e)}, 500)

        # --- SYNC API ---
        if post_path == '/api/sync/push':
            user_session = self.auth_service.validate_session(token)
            if not user_session:
                logging.warning(f"🚨 Sync push: Sesión inválida. Token: {token[:20] if token else 'VACÍO'}...")
                return self._json_response({"status": "error", "message": "Sesión inválida"}, 401)
            
            try:
                result = self.dispatcher.execute("sync.push", {
                    "user_id": user_session["id"],
                    "events": data.get("events", [])
                }, current_user_role=user_session["role"])
                return self._json_response(result)
            except Exception as e:
                logging.exception(f"Error en sync push: {e}")
                return self._json_response({"status": "error", "message": str(e)}, 500)

        # --- PUBLIC AUTH ENDPOINTS (No requieren token) ---
        
        # 🔍 DIAGNOSTIC: Evaluar si es comando auth
        if command:
            logging.debug(f"🔎 Evaluando comando: '{command}' en POST {post_path}")
        
        if post_path == '/' and command == 'auth.login':
            logging.info(f"🔐 [LOGIN] Procesando solicitud de login en POST /")
            try:
                # Extracción robusta de credenciales
                username = None
                password = None
                
                if isinstance(data, dict):
                    username = data.get("username") or params.get("username")
                    password = data.get("password") or params.get("password")
                
                logging.debug(f"🔑 [LOGIN] username='{username}' | password_received={bool(password)}")
                
                if not username or not password:
                    logging.warning(f"❌ [LOGIN] Credenciales incompletas: username='{username}' | password={bool(password)}")
                    return self._json_response({"status": "error", "message": "Usuario y contraseña requeridos"}, 400)
                
                logging.info(f"📝 [LOGIN] Intentando login para usuario: {username}")
                result = self.dispatcher.execute("auth.login", {"username": username, "password": password})
                
                logging.debug(f"📊 [LOGIN] Resultado dispatcher: {result}")
                
                if result.get("status") == "success":
                    logging.info(f"✅ [LOGIN] Login exitoso para usuario: {username} | Token generado")
                    return self._json_response(result, 200)
                else:
                    logging.warning(f"❌ [LOGIN] Login rechazado para {username}: {result.get('message')}")
                    return self._json_response(result, 401)
            except Exception as e:
                logging.exception(f"💥 [LOGIN] Excepción durante login: {e}")
                return self._json_response({"status": "error", "message": str(e)}, 500)

        if post_path == '/' and command == 'auth.register_owner':
            logging.info(f"📝 [REGISTER] Procesando solicitud de registro en POST /")
            try:
                # Extracción robusta de credenciales
                username = None
                password = None
                biz_name = None
                
                if isinstance(data, dict):
                    username = data.get("username") or params.get("username")
                    password = data.get("password") or params.get("password")
                    biz_name = data.get("business_name") or params.get("business_name")
                
                logging.debug(f"📊 [REGISTER] username='{username}' | password_received={bool(password)} | business_name='{biz_name}'")
                
                if not all([username, password, biz_name]):
                    logging.warning(f"❌ [REGISTER] Campos incompletos: username={bool(username)}, password={bool(password)}, biz_name={bool(biz_name)}")
                    return self._json_response({"status": "error", "message": "Faltan campos requeridos"}, 400)
                
                logging.info(f"📝 [REGISTER] Intentando crear negocio: {biz_name} | usuario: {username}")
                result = self.dispatcher.execute("auth.register_owner", {
                    "username": username, 
                    "password": password, 
                    "business_name": biz_name
                })
                
                logging.debug(f"📊 [REGISTER] Resultado dispatcher: {result}")
                
                if result.get("status") == "success":
                    logging.info(f"✅ [REGISTER] Negocio registrado exitosamente: {biz_name}")
                else:
                    logging.warning(f"❌ [REGISTER] Registro fallido: {result.get('message')}")
                    
                return self._json_response(result)
            except Exception as e:
                logging.exception(f"💥 [REGISTER] Excepción durante registro: {e}")
                return self._json_response({"status": "error", "message": str(e)}, 500)

        if post_path == '/api/auth/login':
            logging.info(f"🔐 [API-LOGIN] Procesando solicitud de login en POST /api/auth/login")
            try:
                # ✅ FIX: Buscar en data o params
                username = data.get("username") or params.get("username")
                password = data.get("password") or params.get("password")
                
                logging.debug(f"🔑 [API-LOGIN] username='{username}' | password_received={bool(password)}")
                
                if not username or not password:
                    logging.warning(f"❌ [API-LOGIN] Credenciales incompletas")
                    return self._json_response({"status": "error", "message": "Usuario y contraseña requeridos"}, 400)
                
                logging.info(f"📝 [API-LOGIN] Intentando login para usuario: {username}")
                result = self.dispatcher.execute("auth.login", {"username": username, "password": password})
                
                if result.get("status") == "success":
                    logging.info(f"✅ [API-LOGIN] Login exitoso para usuario: {username}")
                    return self._json_response(result, 200)
                else:
                    logging.warning(f"❌ [API-LOGIN] Login fallido para {username}")
                    return self._json_response(result, 401)
            except Exception as e:
                logging.exception(f"💥 [API-LOGIN] Excepción: {e}")
                return self._json_response({"status": "error", "message": str(e)}, 500)

        if post_path == '/api/admin/setup':
            logging.info(f"📝 [SETUP] Procesando solicitud de setup en POST /api/admin/setup")
            username = data.get("username") or params.get("username")
            password = data.get("password") or params.get("password")
            biz_name = data.get("business_name") or params.get("business_name")
            
            logging.debug(f"📊 [SETUP] Datos: username={username}, biz_name={biz_name}")
            
            res = self.dispatcher.execute("auth.register_owner", {
                "username": username, 
                "password": password, 
                "business_name": biz_name
            })
            return self._json_response(res)

        # --- FLUJO DE COMANDOS GENERALES (Requieren Sesión) ---
        if not command:
            logging.warning(f"❌ POST {post_path}: Comando no especificado")
            return self._json_response({"status": "error", "message": "Comando no especificado"}, 400)

        logging.debug(f"🔎 [AUTH] Validando token para comando: {command}")
        user_session = self.auth_service.validate_session(token)
        
        if not user_session:
            logging.warning(f"🚨 [AUTH] Comando '{command}': Sesión inválida. Token recibido: {token[:20] if token else 'VACÍO'}...")
            return self._json_response({"status": "error", "message": "Sesión no válida o expirada. Por favor, inicie sesión."}, 401)

        logging.info(f"✅ [AUTH] Comando '{command}' válido para usuario: {user_session.get('username', 'Unknown')}")

        try:
            # EXCEPCIÓN PARA COMANDOS GLOBALES DE ADMINISTRACIÓN
            if command.startswith('sys.admin.'):
                logging.debug(f"🎯 Ejecutando comando admin: {command}")
                result = self.dispatcher.execute(
                    command, 
                    params, 
                    current_user_role=user_session["role"], 
                    is_pro=True, 
                    user_id=user_session["id"]
                )
                return self._json_response(result)

            # Resolución Dinámica de la Base de Datos del Tenant
            if user_session.get("role") == "MASTER":
                logging.debug(f"🎯 Ejecutando comando MASTER: {command}")
                result = self.dispatcher.execute(
                    command, 
                    params, 
                    current_user_role="MASTER", 
                    is_pro=True,
                    user_id=user_session["id"]
                )
                return self._json_response(result)

            tenant_id = user_session["tenant_id"]
            logging.debug(f"🏢 Resolviendo DB para tenant: {tenant_id}")
            schema_name = self.auth_service.resolve_tenant_db(tenant_id)
            
            if not schema_name:
                logging.error(f"❌ No se pudo resolver schema para tenant: {tenant_id}")
                return self._json_response({"status": "error", "message": "No se pudo localizar la base de datos del negocio."}, 500)

            is_pro_user = (user_session.get("plan") == "PRO" or user_session.get("plan") == "ENTERPRISE")
            tenant_dispatcher = self.server_instance._get_tenant_dispatcher(tenant_id, schema_name)

            logging.debug(f"🎯 Ejecutando comando para tenant '{tenant_id}': {command}")
            result = tenant_dispatcher.execute(
                command, 
                params, 
                current_user_role=user_session["role"], 
                is_pro=is_pro_user,
                user_permissions=self.auth_service.get_user_permissions(user_session["id"], tenant_id),
                user_id=user_session["id"]
            )
            return self._json_response(result)
        except Exception as e:
            logging.exception(f"💥 [EXEC] Error processing command {command}: {e}")
            return self._json_response({"status": "error", "message": str(e)}, 500)

class WebServer:
    def __init__(self, dispatcher: CommandDispatcher, auth_service, port=8888):
        self.dispatcher = dispatcher
        self.auth_service = auth_service
        self.port = port
        self.server = None
        self.tenant_dispatchers = {}

    def _get_tenant_dispatcher(self, tenant_id, schema_name):
        """Obtiene o crea un CommandDispatcher específico para un tenant."""
        if tenant_id in self.tenant_dispatchers:
            return self.tenant_dispatchers[tenant_id]

        logging.info(f"Creando nuevo dispatcher para tenant {tenant_id} (Schema: {schema_name})")
        from ..core.database import DatabaseManager
        from ..core.stock_service import StockService
        from ..core.sales_service import SalesService
        from ..core.system_service import SystemService

        try:
            db = DatabaseManager(schema_name=schema_name)
            db._init_db()
            
            stock_service = StockService(db)
            sales_service = SalesService(db, stock_service)
            system_service = SystemService(db)
            
            dispatcher = CommandDispatcher(
                db=db, 
                stock_service=stock_service, 
                sales_service=sales_service, 
                system_service=system_service,
                auth_service=self.auth_service
            )
            
            self.tenant_dispatchers[tenant_id] = dispatcher
            return dispatcher
        except Exception as e:
            logging.exception(f"Error creando dispatcher para tenant {tenant_id}: {e}")
            raise e

    def _create_handler(self):
        outer_self = self
        class HandlerWithContext(WebAPIHandler):
            dispatcher = outer_self.dispatcher
            auth_service = outer_self.auth_service
            server_instance = outer_self
        return HandlerWithContext

    def start(self):
        handler_class = self._create_handler()
        self.server = ThreadingHTTPServer(("0.0.0.0", self.port), handler_class)
        logging.info(f"🌐 Servidor API iniciado en puerto {self.port} (Modo Multi-hilo)")
        self.server.serve_forever()

    def stop(self):
        if self.server: self.server.shutdown()
