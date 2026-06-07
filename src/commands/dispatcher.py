from typing import Dict, Any, Callable
import logging
from ..core.database import DatabaseManager
from ..core.stock_service import StockService
from ..core.sales_service import SalesService
from ..core.system_service import SystemService

class CommandDispatcher:
    """
    Orquestador central del sistema.
    Traduce comandos de texto en acciones de servicio, validando permisos y licencias.
    """
    
    def __init__(self, db: DatabaseManager, stock_service: StockService, sales_service: SalesService, system_service: SystemService, auth_service=None):
        self.db = db
        self.stock_service = stock_service
        self.sales_service = sales_service
        self.system_service = system_service
        self.auth_service = auth_service
        
        # Import Service Initialization
        from ..core.import_service import ImportService
        from ..core.sentinel_service import SentinelService
        self.import_service = ImportService(stock_service)
        self.sentinel_service = SentinelService(db)
        
        self.logger = logging.getLogger("CommandDispatcher")
        
        # Mapa de comandos: "comando" -> (función, nivel_acceso, es_pro, llave_permiso)
        # Niveles de acceso: 'gratis', 'empleado', 'admin'
        self.commands_map: Dict[str, tuple] = {
            # --- AUTH ---
            "auth.login": (self._handle_auth_login, "gratis", False, None),
            "auth.register_owner": (self._handle_auth_register_owner, "gratis", False, None),
            "auth.logout": (self._handle_auth_logout, "gratis", False, None),
            "auth.validate_session": (self._handle_auth_validate_session, "gratis", False, None),

            # --- STOCK ---
            "stock.list": (self._handle_stock_list, "gratis", False, "perm_stock_read"),
            "stock.get": (self._handle_stock_get, "gratis", False, "perm_stock_read"),
            "stock.search": (self._handle_stock_search, "gratis", False, "perm_stock_read"),
            "stock.add": (self._handle_stock_add, "admin", False, "perm_stock_write"),
            "stock.edit": (self._handle_stock_edit, "admin", False, "perm_stock_write"),
            "stock.delete": (self._handle_stock_delete, "admin", False, "perm_stock_write"),
            "stock.update_qty": (self._handle_stock_update_qty, "empleado", False, "perm_stock_update"),
            "stock.import": (self._handle_stock_import, "admin", False, "perm_stock_write"),
            "stock.import.preview": (self._handle_stock_import_preview, "admin", False, "perm_stock_write"),
            "stock.import.commit": (self._handle_stock_import_commit, "admin", False, "perm_stock_write"),
            "stock.import.save_profile": (self._handle_stock_import_save_profile, "admin", False, "perm_stock_write"),
            
            # --- VENTAS ---
            "venta.nueva": (self._handle_venta_nueva, "empleado", False, "perm_sales_create"),
            "venta.add": (self._handle_venta_add, "empleado", False, "perm_sales_create"),
            "venta.search": (self._handle_venta_search, "empleado", False, "perm_sales_create"),
            "venta.cobrar": (self._handle_venta_cobrar, "empleado", False, "perm_sales_process"),
            "venta.cancelar": (self._handle_venta_cancelar, "empleado", False, "perm_sales_process"),
            
            # --- CAJA ---
            "caja.abrir": (self._handle_caja_abrir, "admin", False, "perm_cash_admin"),
            "caja.cerrar": (self._handle_caja_cerrar, "admin", False, "perm_cash_admin"),
            "caja.status": (self._handle_caja_status, "empleado", False, "perm_cash_read"),
            
            # --- ALIAS / USUARIOS ---
            "alias.add": (self._handle_alias_add, "admin", False, "perm_user_admin"),
            "alias.list": (self._handle_alias_list, "admin", False, "perm_user_admin"),
            "alias.delete": (self._handle_alias_delete, "admin", False, "perm_user_admin"),
            
            # --- GESTIÓN de PERSONAL ---
            "user.invite_employee": (self._handle_user_invite, "admin", False, "perm_user_admin"),
            "user.set_permission": (self._handle_user_set_perm, "admin", False, "perm_user_admin"),
            "user.revoke_access": (self._handle_user_revoke, "admin", False, "perm_user_admin"),
            "user.list": (self._handle_user_list, "admin", False, "perm_user_admin"),
            
            # --- REPORTES (PRO) ---
            "reporte.resumen": (self._handle_reporte_resumen, "admin", True, "perm_reports"),
            "reporte.top": (self._handle_reporte_top, "admin", True, "perm_reports"),
            "reporte.alertas": (self._handle_reporte_alertas, "admin", True, "perm_reports"),
            
            # --- SISTEMA ---
            "sys.theme.set": (self._handle_sys_theme_set, "gratis", False, "perm_sys_config"),
            "sys.lang.set": (self._handle_sys_lang_set, "gratis", False, "perm_sys_config"),
            "sys.export_csv": (self._handle_sys_export_csv, "admin", True, "perm_sys_export"),
            "sys.info": (self._handle_sys_info, "gratis", False, "perm_sys_read"),
            "logs.view": (self._handle_logs_view, "admin", False, "perm_sys_logs"),
            "debug.call": (self._handle_debug_call, "admin", False, "perm_debug"),
            "sys.subscription.update": (self._handle_subscription_update, "admin", False, "perm_sys_config"),
            "sys.sentinel.status": (self._handle_sentinel_status, "admin", False, "perm_sys_admin"),
            "sys.sentinel.update": (self._handle_sentinel_update, "admin", False, "perm_sys_admin"),
            "sys.sentinel.rollback": (self._handle_sentinel_rollback, "admin", False, "perm_sys_admin"),
            "sys.admin.users_list": (self._handle_admin_users_list, "admin", False, "perm_sys_admin"),
        }

    def execute(self, command_str: str, params: Dict[str, Any] = None, current_user_role: str = "empleado", is_pro: bool = False, user_permissions: set = None, user_id: str = None) -> Dict[str, Any]:
        """
        Ejecuta un comando validando permisos y licencia.
        Soporta PBAC (Permission-Based Access Control) y Acceso Maestro.
        """
        if params is None:
            params = {}
        if user_permissions is None:
            user_permissions = set()

        # 1. Buscar comando
        if command_str not in self.commands_map:
            return {"status": "error", "message": f"Comando '{command_str}' no reconocido."}

        handler, required_role, is_pro_feature, perm_key = self.commands_map[command_str]

        # 2. VALIDACIÓN MAESTRA (GOD MODE)
        # El usuario maestro o el rol SUPER_ADMIN tienen acceso total
        if (user_id and user_id.startswith("master_")) or current_user_role in ["MASTER", "SUPER_ADMIN"]:
            self.logger.info(f"GOD_MODE: Ejecutando {command_str} como Super Admin.")
            try:
                return handler(params)
            except Exception as e:
                self.logger.error(f"Exception in GOD_MODE {command_str}: {e}")
                return {"status": "error", "message": f"Error maestro: {str(e)}"}

        # 3. Validar Licencia PRO
        if is_pro_feature and not is_pro:
            return {"status": "error", "message": "Esta función es exclusiva de la versión PRO. Por favor, actualiza tu licencia."}

        # 4. Validar Acceso (PBAC)
        # El Dueño (OWNER) tiene acceso total a todo en su tenant
        if current_user_role == "OWNER":
            pass # Acceso total
        elif perm_key is None:
            pass # Comando público (ej. login, registro)
        else:
            # a) El rol 'admin' tiene acceso implícito a todo lo que no sea PRO
            if current_user_role == "admin":
                pass # Acceso concedido
            
            # b) Los 'empleados' deben tener la llave granular específica para operar
            elif current_user_role == "empleado":
                if perm_key not in user_permissions:
                    return {"status": "error", "message": f"Acceso denegado. Tu perfil de empleado no tiene el permiso necesario: {perm_key}."}
            
            # c) Para otros roles (ej. 'gratis'), verificamos la jerarquía básica
            else:
                if not self._check_role_permission(current_user_role, required_role):
                    return {"status": "error", "message": f"Permisos insuficientes. Se requiere rol: {required_role}."}
                
                # Incluso para roles básicos, si hay una llave específica, se valida
                if perm_key not in user_permissions:
                     return {"status": "error", "message": f"No tienes el permiso necesario ({perm_key}) para ejecutar esta acción."}

        # 5. Ejecutar Handler
        try:
            self.logger.info(f"Executing command: {command_str} | User Role: {current_user_role}")
            return handler(params)
        except Exception as e:
            self.logger.error(f"Exception executing {command_str}: {e}")
            return {"status": "error", "message": f"Error interno ejecutando comando: {str(e)}"}

    def _check_role_permission(self, user_role: str, required_role: str) -> bool:
        """
        Verifica la jerarquía de roles.
        MASTER > admin > empleado > gratis
        """
        hierarchy = {"MASTER": 4, "admin": 3, "empleado": 2, "gratis": 1}
        return hierarchy.get(user_role, 0) >= hierarchy.get(required_role, 0)

    # --- HANDLERS DE SINCRONIZACIÓN MÓVIL ---

    def _handle_sync_push(self, params):
        """Procesa la cola de eventos enviados desde la App Android/iOS."""
        user_id = params.get("user_id")
        events = params.get("events", [])
        
        if not user_id:
            return {"status": "error", "message": "Falta el user_id para sincronizar."}
        
        return self.sync_service.process_push_events(user_id, events)

    def _handle_sync_pull(self, params):
        """Entrega el stock actualizado para la caché local del móvil."""
        products = self.sync_service.get_stock_delta()
        return {"status": "success", "products": products}

    # --- HANDLERS DE AUTENTICACIÓN ---

    def _handle_auth_login(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado."}
        
        # Búsqueda exhaustiva de credenciales
        username = params.get("username") or params.get("user") or params.get("user_id")
        password = params.get("password") or params.get("pass") or params.get("pwd")
        
        if not username or not password:
            return {"status": "error", "message": "Usuario y contraseña son obligatorios."}
        
        return self.auth_service.login(username, password)

    def _handle_auth_register_owner(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado."}
        
        username = params.get("username") or params.get("user")
        password = params.get("password") or params.get("pass")
        biz_name = params.get("business_name") or params.get("biz_name") or params.get("business")
        
        if not all([username, password, biz_name]):
            return {"status": "error", "message": "Username, password y business_name son obligatorios."}
            
        return self.auth_service.create_owner_account(username, password, biz_name)

    def _handle_auth_logout(self, params):
        token = params.get("token")
        if not token:
            return {"status": "error", "message": "Token obligatorio para logout."}
        return self.auth_service.logout(token)

    def _handle_auth_validate_session(self, params):
        """Valida si un token de sesión es válido y devuelve los datos del usuario."""
        token = params.get("token") 
        if not token:
            return {"status": "error", "message": "Token no proporcionado para validación."}
        
        user = self.auth_service.validate_session(token)
        if user:
            return {"status": "success", "user": user}
        return {"status": "error", "message": "Sesión inválida o expirada."}

    def _handle_auth_me(self, params):
        token = params.get("token")
        if not token:
            return {"status": "error", "message": "Token no proporcionado."}
        user = self.auth_service.validate_session(token)
        if not user:
            return {"status": "error", "message": "Sesión no válida."}
        return {"status": "success", "user": user}

    # --- HANDLERS DE GESTIÓN de PERSONAL ---

    def _handle_user_invite(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado en el Dispatcher."}
        
        tenant_id = params.get("tenant_id")
        username = params.get("username")
        password = params.get("password")
        
        if not all([tenant_id, username, password]):
            return {"status": "error", "message": "Faltan parámetros: username, password y tenant_id son obligatorios."}
        
        return self.auth_service.create_employee_account(username, password, tenant_id)

    def _handle_user_set_perm(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado en el Dispatcher."}
        
        tenant_id = params.get("tenant_id")
        user_id = params.get("user_id")
        perm_key = params.get("permission_key")
        granted = params.get("granted", False)
        
        if not all([tenant_id, user_id, perm_key]):
            return {"status": "error", "message": "Faltan parámetros: tenant_id, user_id y permission_key son obligatorios."}
            
        return self.auth_service.set_user_permission(tenant_id, user_id, perm_key, granted)

    def _handle_user_revoke(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado en el Dispatcher."}
        
        user_id = params.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Falta el user_id."}
            
        return self.auth_service.revoke_user_access(user_id)

    def _handle_user_list(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado en el Dispatcher."}
        
        tenant_id = params.get("tenant_id")
        if not tenant_id:
            return {"status": "error", "message": "Falta el tenant_id."}
        
        if hasattr(self.auth_service, "list_users"):
            return self.auth_service.list_users(tenant_id)
        
        # ✅ FIX: Query correcta para PostgreSQL (con placeholders %s)
        query = "SELECT id, username, role, is_active, created_at FROM users WHERE tenant_id = %s ORDER BY username"
        users = self.auth_service.global_db.fetch_all(query, (tenant_id,))
        return {"status": "success", "data": [dict(u) for u in users]}

    # --- HANDLERS DE STOCK ---

    def _handle_stock_get(self, params):
        codigo = params.get("codigo")
        if not codigo:
            return {"status": "error", "message": "Falta el código del producto"}
        
        res = self.stock_service.get_product(codigo)
        return res

    def _handle_stock_list(self, params):
        return self.stock_service.list_products(
            filter_text=params.get("filter"), 
            category=params.get("category")
        )

    def _handle_stock_search(self, params):
        """🆕 NUEVO: Búsqueda de productos para autocompletado.
        Devuelve lista de productos que coincidan con el término de búsqueda (nombre o código).
        Sin cargar cantidad automáticamente.
        """
        search_term = params.get("search", "").strip()
        limit = params.get("limit", 10)
        
        if not search_term or len(search_term) < 1:
            return {"status": "success", "data": []}
        
        # Buscar por código O nombre
        query = """
            SELECT codigo, nombre, precio, cantidad, categoria 
            FROM products 
            WHERE LOWER(codigo) LIKE LOWER(%s) OR LOWER(nombre) LIKE LOWER(%s)
            LIMIT %s
        """
        search_pattern = f"%{search_term}%"
        results = self.db.fetch_all(query, (search_pattern, search_pattern, limit))
        
        return {
            "status": "success",
            "data": [dict(r) for r in results]
        }

    def _handle_stock_add(self, params):
        return self.stock_service.add_product(
            codigo=params.get("codigo"),
            nombre=params.get("nombre"),
            precio=params.get("precio"),
            cantidad=params.get("cantidad"),
            categoria=params.get("categoria"),
            es_peso=params.get("es_peso", False)
        )

    def _handle_stock_edit(self, params):
        return self.stock_service.add_product(
            codigo=params.get("codigo"),
            nombre=params.get("nombre"),
            precio=params.get("precio"),
            cantidad=params.get("cantidad"),
            categoria=params.get("categoria"),
            es_peso=params.get("es_peso", False)
        )

    def _handle_stock_delete(self, params):
        return self.stock_service.delete_product(params.get("codigo"))

    def _handle_stock_update_qty(self, params):
        return self.stock_service.update_stock(
            codigo=params.get("codigo"), 
            amount=params.get("amount")
        )

    def _handle_stock_import(self, params):
        file_path = params.get("file_path")
        mapping_id = params.get("mapping_id")
        custom_mapping = params.get("custom_mapping")
        
        if not file_path:
            return {"status": "error", "message": "El parámetro 'file_path' es obligatorio."}
            
        return self.import_service.import_stock(
            file_path=file_path, 
            mapping_id=mapping_id, 
            custom_mapping=custom_mapping
        )

    def _handle_stock_import_preview(self, params):
        file_path = params.get("file_path")
        mapping_id = params.get("mapping_id")
        custom_mapping = params.get("custom_mapping")
        
        if not file_path:
            return {"status": "error", "message": "El parámetro 'file_path' es obligatorio."}
            
        return self.import_service.preview_import(
            file_path=file_path, 
            mapping_id=mapping_id, 
            custom_mapping=custom_mapping
        )

    def _handle_stock_import_commit(self, params):
        data_list = params.get("data_list")
        if not data_list or not isinstance(data_list, list):
            return {"status": "error", "message": "El parámetro 'data_list' es obligatorio y debe ser una lista."}
            
        return self.import_service.commit_import(data_list)

    def _handle_stock_import_save_profile(self, params):
        """
        Guarda un mapeo de columnas personalizado como un perfil.
        """
        mapping_id = params.get("mapping_id")
        mapping = params.get("mapping")
        
        if not mapping_id or not mapping:
            return {"status": "error", "message": "Tanto 'mapping_id' como 'mapping' son obligatorios."}
        
        if not isinstance(mapping, dict):
            return {"status": "error", "message": "El mapeo debe ser un objeto (diccionario)."}
            
        return self.import_service.save_mapping_profile(mapping_id, mapping)

    # --- HANDLERS DE VENTAS ---

    def _handle_venta_nueva(self, params):
        return {"status": "success", "message": "Carrito de ventas inicializado."}

    def _handle_venta_add(self, params):
        res = self.stock_service.get_product(params.get("codigo"))
        if res["status"] == "success":
            return {"status": "success", "data": res["data"], "message": "Producto agregado al carrito."}
        return res

    def _handle_venta_search(self, params):
        """🆕 NUEVO: Búsqueda rápida de productos para ventas.
        Devuelve lista sin cargar automáticamente al carrito.
        """
        search_term = params.get("search", "").strip()
        limit = params.get("limit", 8)
        
        if not search_term or len(search_term) < 1:
            return {"status": "success", "data": []}
        
        # Buscar por código O nombre
        query = """
            SELECT codigo, nombre, precio, cantidad, categoria 
            FROM products 
            WHERE LOWER(codigo) LIKE LOWER(%s) OR LOWER(nombre) LIKE LOWER(%s)
            ORDER BY CASE 
                WHEN LOWER(codigo) LIKE LOWER(%s) THEN 0 
                ELSE 1 
            END,
            nombre ASC
            LIMIT %s
        """
        search_pattern = f"%{search_term}%"
        results = self.db.fetch_all(query, (search_pattern, search_pattern, search_pattern, limit))
        
        return {
            "status": "success",
            "data": [dict(r) for r in results]
        }

    def _handle_venta_cobrar(self, params):
        return self.sales_service.process_sale(
            cliente=params.get("cliente"),
            items=params.get("items"),
            metodo_pago=params.get("metodo_pago"),
            paga_con=params.get("paga_con"),
            alias=params.get("alias")
        )

    def _handle_venta_cancelar(self, params):
        return {"status": "success", "message": "Carrito vaciado."}

    # --- HANDLERS DE CAJA ---

    def _handle_caja_abrir(self, params):
        return self.sales_service.open_cash_box(params.get("monto_inicial"))

    def _handle_caja_cerrar(self, params):
        return self.sales_service.close_cash_box(params.get("monto_real"))

    def _handle_caja_status(self, params):
        return self.sales_service.get_cash_box_status()

    # --- HANDLERS DE REPORTES (PRO) ---

    def _handle_reporte_resumen(self, params):
        sales = self.db.fetch_all("SELECT SUM(total) as total FROM sales")
        total_facturado = sales[0]['total'] or 0
        ganancia_est = total_facturado * 0.3
        return {
            "status": "success", 
            "data": {
                "total_facturado": total_facturado,
                "ganancia_estimada": ganancia_est
            }
        }

    def _handle_reporte_top(self, params):
        limit = params.get("limit", 3)
        query = '''
            SELECT p.nombre, SUM(si.cantidad) as total_vendido
            FROM sale_items si
            JOIN products p ON si.product_codigo = p.codigo
            WHERE 1=1
            GROUP BY p.codigo
            ORDER BY total_vendido DESC
            LIMIT %s
        '''
        top = self.db.fetch_all(query, (limit,))
        return {"status": "success", "data": [dict(t) for t in top]}

    def _handle_reporte_alertas(self, params):
        return self.stock_service.get_low_stock()

    # --- HANDLERS DE SISTEMA ---

    def _handle_sys_theme_set(self, params):
        return self.system_service.set_setting("theme", params.get("value"))

    def _handle_sys_lang_set(self, params):
        return self.system_service.set_setting("lang", params.get("value"))

    def _handle_sys_export_csv(self, params):
        return self.system_service.export_inventory_to_csv()

    def _handle_sys_info(self, params):
        return self.system_service.get_system_info()

    def _handle_logs_view(self, params):
        limit = params.get("limit", 100)
        logs = self.db.fetch_all("SELECT * FROM audit WHERE id > 0 ORDER BY id DESC LIMIT %s", (limit,))
        return {"status": "success", "data": [dict(l) for l in logs]}

    # --- HANDLERS DE ALIAS ---

    def _handle_alias_add(self, params):
        return self.sales_service.add_alias(
            nombre=params.get("nombre"),
            limite=params.get("limite")
        )

    def _handle_alias_list(self, params):
        return self.sales_service.list_aliases()

    def _handle_alias_delete(self, params):
        return self.sales_service.delete_alias(params.get("alias_id"))

    def _handle_debug_call(self, params):
        service_name = params.get("service")
        method_name = params.get("method")
        args = params.get("args", {})

        services = {
            "stock": self.stock_service,
            "sales": self.sales_service,
            "system": self.system_service,
            "auth": self.auth_service
        }

        if service_name not in services:
            return {"status": "error", "message": f"Servicio '{service_name}' no encontrado."}

        service_obj = services[service_name]
        method = getattr(service_obj, method_name, None)

        if not method or not callable(method):
            return {"status": "error", "message": f"Método '{method_name}' no encontrado en {service_name}."}

        try:
            self.logger.info(f"AUDIT-DEBUG: Calling {service_name}.{method_name} with args {args}")
            result = method(**args)
            self.logger.info(f"AUDIT-DEBUG: {service_name}.{method_name} returned: {result}")
            return {"status": "success", "debug_result": result}
        except Exception as e:
            self.logger.error(f"AUDIT-DEBUG: Error calling {service_name}.{method_name}: {str(e)}")
            return {"status": "error", "exception": str(e)}

    def _handle_subscription_update(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado."}
        
        tenant_id = params.get("tenant_id")
        plan = params.get("plan")
        credits = params.get("credits", 0)
        
        if not tenant_id or not plan:
            return {"status": "error", "message": "Faltan parámetros obligatorios: tenant_id y plan."}
            
        return self.auth_service.update_subscription(tenant_id, plan, credits)

    def _handle_sentinel_status(self, params):
        return self.sentinel_service.get_sentinel_status()

    def _handle_sentinel_update(self, params):
        version = params.get("version")
        source = params.get("source")
        if not version or not source:
            return {"status": "error", "message": "Parámetros 'version' y 'source' son obligatorios."}
        return self.sentinel_service.request_action("UPDATE", {"version": version, "source": source})

    def _handle_sentinel_rollback(self, params):
        return self.sentinel_service.request_action("ROLLBACK")

    def _handle_admin_users_list(self, params):
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado."}
        
        self.logger.info("ADMIN_ACTION: Consulta global de usuarios ejecutada.")
        return self.auth_service.list_all_users_admin()

    def _handle_sys_admin_setup(self, params):
        """Handler para la configuración inicial del Master Admin."""
        if not self.auth_service:
            return {"status": "error", "message": "AuthService no configurado."}
        
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return {"status": "error", "message": "Usuario y contraseña son obligatorios."}
            
        return self.auth_service.create_master_account(username, password)
