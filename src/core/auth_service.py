import os
import uuid
import hashlib
import logging
import json
from typing import Dict, Any, Optional
from .global_db import GlobalDatabaseManager

class AuthService:
    """
    Servicio de Autenticación y Gestión de Identidad.
    Coordina el acceso de usuarios, la validación de tokens 
    y la resolución de la base de datos del tenant.
    """
    
    def __init__(self, global_db: GlobalDatabaseManager):
        self.global_db = global_db
        self.logger = logging.getLogger("AuthService")
        # Cache de sesiones: {token: (user_data, expires_at)}
        self._session_cache = {}
        self._cache_ttl = 300 # 5 minutos de caché

    def _get_cached_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Retorna la sesión desde la caché si existe y no ha expirado."""
        if token in self._session_cache:
            user_data, expires_at = self._session_cache[token]
            from datetime import datetime, timezone
            if expires_at > datetime.now(timezone.utc):
                return user_data
            else:
                del self._session_cache[token]
        return None

    def _set_cached_session(self, token: str, user_data: Dict[str, Any], expires_at):
        """Almacena la sesión en la caché."""
        self._session_cache[token] = (user_data, expires_at)

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Valida la sesión usando caché primero, luego la DB."""
        if not token:
            return None

        # 1. Intentar obtener de la caché
        cached_user = self._get_cached_session(token)
        if cached_user:
            return cached_user

        try:
            from datetime import datetime, timezone
            session = self.global_db.fetch_one(
                "SELECT user_data, expires_at FROM sessions WHERE token = %s", 
                (token,)
            )
            if not session:
                return None

            user_data = session["user_data"]
            if isinstance(user_data, str):
                user_data = json.loads(user_data)

            expires_at = session["expires_at"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < datetime.now(timezone.utc):
                self.global_db.execute("DELETE FROM sessions WHERE token = %s", (token,))
                return None

            # 2. Guardar en caché para futuras peticiones
            self._set_cached_session(token, user_data, expires_at)
            return user_data
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return None

    def logout(self, token: str):
        """Elimina la sesión de la DB y de la caché."""
        try:
            if token in self._session_cache:
                del self._session_cache[token]
            self.global_db.execute("DELETE FROM sessions WHERE token = %s", (token,))
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return {"status": "error", "message": str(e)}

    def resolve_tenant_db(self, tenant_id: str) -> Optional[str]:

        """Busca el nombre del esquema de la base de datos para un tenant específico."""
        if not tenant_id:
            return None
        
        tenant = self.global_db.fetch_one(
            "SELECT schema_name FROM tenants WHERE id = %s", 
            (tenant_id,)
        )
        return tenant["schema_name"] if tenant else None

    def get_user_permissions(self, user_id: str, tenant_id: str) -> set:
        """
        Retorna el conjunto de permisos otorgados para un usuario en un tenant.
        """
        query = "SELECT permission_key FROM permissions WHERE user_id = %s AND tenant_id = %s AND granted = True"
        results = self.global_db.fetch_all(query, (user_id, tenant_id))
        return {row["permission_key"] for row in results}

    def set_user_permission(self, tenant_id: str, user_id: str, permission_key: str, granted: bool) -> Dict[str, Any]:
        """Asigna o revoca un permiso específico para un usuario en un tenant."""
        try:
            query = '''
                INSERT INTO permissions (tenant_id, user_id, permission_key, granted, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(tenant_id, user_id, permission_key) DO UPDATE SET
                    granted=excluded.granted,
                    updated_at=excluded.updated_at
            '''
            self.global_db.execute(query, (tenant_id, user_id, permission_key, granted))
            return {"status": "success", "message": f"Permiso {permission_key} {'otorgado' if granted else 'revocado'}."}
        except Exception as e:
            self.logger.error(f"Error setting permission: {e}")
            return {"status": "error", "message": str(e)}

    def revoke_user_access(self, user_id: str) -> Dict[str, Any]:
        """Elimina completamente a un usuario del sistema."""
        try:
            self.global_db.execute("DELETE FROM permissions WHERE user_id = %s", (user_id,))
            self.global_db.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return {"status": "success", "message": "Acceso del usuario revocado exitosamente."}
        except Exception as e:
            self.logger.error(f"Error revoking access: {e}")
            return {"status": "error", "message": str(e)}

    def create_owner_account(self, username, password, business_name) -> Dict[str, Any]:
        """
        Crea un nuevo dueño y su respectiva instancia de negocio (Tenant) en PostgreSQL.
        Valida que el usuario no exista antes de crearlo.
        """
        try:
            # 1. VALIDAR que el usuario NO existe
            existing_user = self.global_db.fetch_one(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            
            if existing_user:
                self.logger.warning(f"Intento de crear usuario duplicado: {username}")
                return {
                    "status": "error", 
                    "message": f"El usuario '{username}' ya existe. Intenta con otro nombre."
                }
            
            user_id = str(uuid.uuid4())[:8]
            tenant_id = f"tenant_{user_id}"
            # En Postgres, el esquema debe empezar por letra y no tener caracteres especiales complicados
            schema_name = f"schema_{user_id}"
            
            # 2. Insertar Tenant con su esquema asignado
            self.global_db.execute(
                "INSERT INTO tenants (id, owner_id, schema_name, business_name, plan, credits) VALUES (%s, %s, %s, %s, %s, %s)",
                (tenant_id, user_id, schema_name, business_name, "FREE", 10)
            )

            # --- INICIALIZACIÓN DEL ESQUEMA DEL TENANT ---
            # Creamos las tablas del cliente inmediatamente después de crear el tenant
            try:
                from .database import DatabaseManager
                tenant_db = DatabaseManager(schema_name=schema_name)
                tenant_db._init_db()
            except Exception as e:
                self.logger.error(f"Error inicializando DB del tenant {tenant_id}: {e}")
            # ---------------------------------------------

            # 3. Insertar Usuario como OWNER
            self.global_db.execute(
                "INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                (user_id, username, self._hash_password(password), "OWNER", tenant_id)
            )


            self.logger.info(f"Nuevo dueño creado: {username} para negocio {business_name} (Schema: {schema_name})")
            return {
                "status": "success", 
                "user_id": user_id, 
                "tenant_id": tenant_id, 
                "schema_name": schema_name
            }
        except Exception as e:
            self.logger.error(f"Error creando cuenta de dueño en Postgres: {e}")
            return {"status": "error", "message": str(e)}

    def create_employee_account(self, username, password, tenant_id) -> Dict[str, Any]:
        """Crea un usuario con rol EMPLOYEE vinculado a un negocio existente."""
        try:
            # VALIDAR que el usuario NO existe
            existing_user = self.global_db.fetch_one(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            
            if existing_user:
                self.logger.warning(f"Intento de crear usuario duplicado: {username}")
                return {
                    "status": "error", 
                    "message": f"El usuario '{username}' ya existe. Intenta con otro nombre."
                }
            
            user_id = str(uuid.uuid4())[:8]
            self.global_db.execute(
                "INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                (user_id, username, self._hash_password(password), "EMPLOYEE", tenant_id)
            )
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            self.logger.error(f"Error creando cuenta de empleado: {e}")
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # MÉTODOS DE ADMINISTRACIÓN MAESTRA (MASTER ROLE)
    # =========================================================================

    def delete_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Elimina un tenant y todos sus usuarios asociados. Acceso exclusivo MASTER."""
        try:
            # 1. Eliminar usuarios asociados
            self.global_db.execute("DELETE FROM users WHERE tenant_id = %s", (tenant_id,))
            # 2. Eliminar permisos asociados
            self.global_db.execute("DELETE FROM permissions WHERE tenant_id = %s", (tenant_id,))
            # 3. Eliminar el tenant
            self.global_db.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
            
            self.logger.info(f"Tenant eliminado: {tenant_id}")
            return {"status": "success", "message": f"El negocio {tenant_id} ha sido eliminado permanentemente."}
        except Exception as e:
            self.logger.error(f"Error deleting tenant: {e}")
            return {"status": "error", "message": str(e)}

    def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza la información de un usuario (username, role, etc). Acceso exclusivo MASTER."""
        try:
            # Validar que el usuario existe
            user = self.global_db.fetch_one("SELECT id FROM users WHERE id = %s", (user_id,))
            if not user:
                return {"status": "error", "message": f"Usuario {user_id} no encontrado."}
            
            if "username" in data:
                # Validar que el nuevo username no esté tomado por otro
                existing = self.global_db.fetch_one(
                    "SELECT id FROM users WHERE username = %s AND id != %s", 
                    (data["username"], user_id)
                )
                if existing:
                    return {"status": "error", "message": "El nombre de usuario ya está en uso."}
                self.global_db.execute("UPDATE users SET username = %s WHERE id = %s", (data["username"], user_id))
            
            if "role" in data:
                self.global_db.execute("UPDATE users SET role = %s WHERE id = %s", (data["role"], user_id))
            
            if "tenant_id" in data:
                self.global_db.execute("UPDATE users SET tenant_id = %s WHERE id = %s", (data["tenant_id"], user_id))

            self.logger.info(f"Usuario actualizado: {user_id} con datos {data}")
            return {"status": "success", "message": "Usuario actualizado correctamente."}
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return {"status": "error", "message": str(e)}

    def set_user_permission_master(self, user_id: str, perm_key: str, granted: bool) -> Dict[str, Any]:
        """Asigna un permiso a un usuario buscando automáticamente su tenant. Acceso exclusivo MASTER."""
        try:
            user = self.global_db.fetch_one("SELECT tenant_id FROM users WHERE id = %s", (user_id,))
            if not user or not user["tenant_id"]:
                return {"status": "error", "message": "El usuario no tiene un tenant asociado."}
            
            return self.set_user_permission(user["tenant_id"], user_id, perm_key, granted)
        except Exception as e:
            self.logger.error(f"Error setting permission master: {e}")
            return {"status": "error", "message": str(e)}

    def create_master_account(self, username: str, password: str) -> Dict[str, Any]:

        """
        Crea una cuenta de administrador maestro (MASTER).
        Solo puede existir un usuario MASTER. No tiene tenant asociado.
        """
        try:
            existing = self.global_db.fetch_one(
                "SELECT id FROM users WHERE role = 'MASTER'", ()
            )
            if existing:
                return {"status": "error", "message": "Ya existe una cuenta MASTER en el sistema."}

            existing_user = self.global_db.fetch_one(
                "SELECT id FROM users WHERE username = %s", (username,)
            )
            if existing_user:
                return {"status": "error", "message": f"El usuario '{username}' ya existe."}

            user_id = "master_" + str(uuid.uuid4())[:8]
            # MASTER no tiene tenant_id — insertamos con tenant_id NULL
            self.global_db.execute(
                "INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (%s, %s, %s, 'MASTER', NULL)",
                (user_id, username, self._hash_password(password))
            )
            self.logger.info(f"Cuenta MASTER creada: {username} (id={user_id})")
            return {"status": "success", "user_id": user_id, "username": username, "role": "MASTER"}
        except Exception as e:
            self.logger.error(f"Error creando cuenta MASTER: {e}")
            return {"status": "error", "message": str(e)}

    def get_all_tenants(self, page: int = 1, per_page: int = 20, search: str = "") -> Dict[str, Any]:
        """Lista todos los tenants con información de suscripción. Acceso exclusivo MASTER."""
        try:
            offset = (page - 1) * per_page
            if search:
                query = """
                    SELECT t.*, 
                           COUNT(u.id) FILTER (WHERE u.role != 'MASTER') as user_count
                    FROM tenants t
                    LEFT JOIN users u ON u.tenant_id = t.id
                    WHERE t.business_name ILIKE %s OR t.plan ILIKE %s
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT %s OFFSET %s
                """
                pattern = f"%{search}%"
                rows = self.global_db.fetch_all(query, (pattern, pattern, per_page, offset))
                count_row = self.global_db.fetch_one(
                    "SELECT COUNT(*) as total FROM tenants WHERE business_name ILIKE %s OR plan ILIKE %s",
                    (pattern, pattern)
                )
            else:
                query = """
                    SELECT t.*, 
                           COUNT(u.id) FILTER (WHERE u.role != 'MASTER') as user_count
                    FROM tenants t
                    LEFT JOIN users u ON u.tenant_id = t.id
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT %s OFFSET %s
                """
                rows = self.global_db.fetch_all(query, (per_page, offset))
                count_row = self.global_db.fetch_one("SELECT COUNT(*) as total FROM tenants", ())

            total = count_row["total"] if count_row else 0
            return {
                "status": "success",
                "data": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": max(1, -(-total // per_page))  # ceiling division
            }
        except Exception as e:
            self.logger.error(f"Error listing tenants: {e}")
            return {"status": "error", "message": str(e)}

    def update_tenant_subscription(self, tenant_id: str, plan: str, credits: int = 0) -> Dict[str, Any]:
        """Actualiza el plan y créditos de un tenant. Acceso exclusivo MASTER."""
        try:
            tenant = self.global_db.fetch_one("SELECT id FROM tenants WHERE id = %s", (tenant_id,))
            if not tenant:
                return {"status": "error", "message": f"Tenant '{tenant_id}' no encontrado."}
            self.global_db.execute(
                "UPDATE tenants SET plan = %s, credits = credits + %s WHERE id = %s",
                (plan, credits, tenant_id)
            )
            self.logger.info(f"Suscripción actualizada: tenant={tenant_id}, plan={plan}, +{credits} créditos.")
            return {"status": "success", "message": f"Plan actualizado a {plan} con +{credits} créditos."}
        except Exception as e:
            self.logger.error(f"Error updating tenant subscription: {e}")
            return {"status": "error", "message": str(e)}

    def suspend_user(self, user_id: str, suspend: bool = True) -> Dict[str, Any]:
        """Suspende o reactiva una cuenta de usuario. Acceso exclusivo MASTER."""
        try:
            user = self.global_db.fetch_one("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
            if not user:
                return {"status": "error", "message": f"Usuario '{user_id}' no encontrado."}
            if user["role"] == "MASTER":
                return {"status": "error", "message": "No se puede suspender la cuenta MASTER."}
            self.global_db.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (not suspend, user_id)
            )
            action = "suspendido" if suspend else "reactivado"
            self.logger.info(f"Usuario {user['username']} ({user_id}) {action}.")
            return {"status": "success", "message": f"Usuario {user['username']} {action} exitosamente."}
        except Exception as e:
            self.logger.error(f"Error suspending user: {e}")
            return {"status": "error", "message": str(e)}

    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas globales del sistema en una sola consulta optimizada. Acceso exclusivo MASTER."""
        try:
            query = '''
                SELECT 
                    (SELECT COUNT(*) FROM users WHERE role != 'MASTER') as total_users,
                    (SELECT COUNT(*) FROM tenants) as total_tenants,
                    (SELECT COUNT(*) FROM users WHERE is_active = TRUE AND role != 'MASTER') as active_users,
                    (SELECT COUNT(*) FROM users WHERE is_active = FALSE) as suspended_users
            '''
            main_stats = self.global_db.fetch_one(query)
            
            # Estas dos consultas requieren resultados en lista, se mantienen separadas pero optimizadas
            plan_breakdown = self.global_db.fetch_all(
                "SELECT plan, COUNT(*) as count FROM tenants GROUP BY plan ORDER BY count DESC", ()
            )
            recent_tenants = self.global_db.fetch_all(
                "SELECT business_name, plan, created_at FROM tenants ORDER BY created_at DESC LIMIT 5", ()
            )
            
            return {
                "status": "success",
                "data": {
                    "total_users": main_stats["total_users"] if main_stats else 0,
                    "total_tenants": main_stats["total_tenants"] if main_stats else 0,
                    "active_users": main_stats["active_users"] if main_stats else 0,
                    "suspended_users": main_stats["suspended_users"] if main_stats else 0,
                    "plan_breakdown": [dict(r) for r in plan_breakdown],
                    "recent_tenants": [dict(r) for r in recent_tenants]
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {"status": "error", "message": str(e)}

    def log_admin_action(self, admin_id: str, action: str, details: str = "") -> Dict[str, Any]:
        """Registra una acción de administración en el audit log."""
        try:
            self.global_db.execute(
                "INSERT INTO admin_logs (admin_id, action, details) VALUES (%s, %s, %s)",
                (admin_id, action, details)
            )
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error logging admin action: {e}")
            return {"status": "error", "message": str(e)}

    def get_admin_logs(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Retorna el historial de acciones administrativas con paginación."""
        try:
            offset = (page - 1) * per_page
            rows = self.global_db.fetch_all(
                """
                SELECT al.*, u.username as admin_username
                FROM admin_logs al
                LEFT JOIN users u ON u.id = al.admin_id
                ORDER BY al.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset)
            )
            count_row = self.global_db.fetch_one("SELECT COUNT(*) as total FROM admin_logs", ())
            total = count_row["total"] if count_row else 0
            return {
                "status": "success",
                "data": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": max(1, -(-total // per_page))
            }
        except Exception as e:
            self.logger.error(f"Error fetching admin logs: {e}")
            return {"status": "error", "message": str(e)}

    def get_all_users_paginated(self, page: int = 1, per_page: int = 30, search: str = "") -> Dict[str, Any]:
        """Lista todos los usuarios del sistema con paginación. Acceso exclusivo MASTER."""
        try:
            offset = (page - 1) * per_page
            if search:
                query = """
                    SELECT u.id, u.username, u.role, u.tenant_id, u.is_active, u.created_at,
                           t.business_name, t.plan
                    FROM users u
                    LEFT JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.role != 'MASTER' AND (u.username ILIKE %s OR t.business_name ILIKE %s)
                    ORDER BY t.business_name ASC, u.username ASC
                    LIMIT %s OFFSET %s
                """
                pattern = f"%{search}%"
                rows = self.global_db.fetch_all(query, (pattern, pattern, per_page, offset))
                count_row = self.global_db.fetch_one(
                    """SELECT COUNT(*) as total FROM users u
                       LEFT JOIN tenants t ON u.tenant_id = t.id
                       WHERE u.role != 'MASTER' AND (u.username ILIKE %s OR t.business_name ILIKE %s)""",
                    (pattern, pattern)
                )
            else:
                query = """
                    SELECT u.id, u.username, u.role, u.tenant_id, u.is_active, u.created_at,
                           t.business_name, t.plan
                    FROM users u
                    LEFT JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.role != 'MASTER'
                    ORDER BY t.business_name ASC, u.username ASC
                    LIMIT %s OFFSET %s
                """
                rows = self.global_db.fetch_all(query, (per_page, offset))
                count_row = self.global_db.fetch_one(
                    "SELECT COUNT(*) as total FROM users WHERE role != 'MASTER'", ()
                )
            total = count_row["total"] if count_row else 0
            return {
                "status": "success",
                "data": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": max(1, -(-total // per_page))
            }
        except Exception as e:
            self.logger.error(f"Error listing users: {e}")
            return {"status": "error", "message": str(e)}

    def get_tenant_detail(self, tenant_id: str) -> Dict[str, Any]:
        """Retorna detalles completos de un tenant incluyendo sus usuarios."""
        try:
            tenant = self.global_db.fetch_one(
                "SELECT * FROM tenants WHERE id = %s", (tenant_id,)
            )
            if not tenant:
                return {"status": "error", "message": f"Tenant '{tenant_id}' no encontrado."}
            users = self.global_db.fetch_all(
                "SELECT id, username, role, is_active, created_at FROM users WHERE tenant_id = %s ORDER BY role, username",
                (tenant_id,)
            )
            return {
                "status": "success",
                "data": {
                    "tenant": dict(tenant),
                    "users": [dict(u) for u in users]
                }
            }
        except Exception as e:
            self.logger.error(f"Error fetching tenant detail: {e}")
            return {"status": "error", "message": str(e)}

    def verify_feature(self, tenant_id: str, feature_id: str) -> bool:
        """
        Verifica si un tenant tiene una licencia activa para una funcionalidad específica.
        Consulta la tabla 'entitlements' en la DB Global.
        """
        if not tenant_id or not feature_id:
            return False
        try:
            from datetime import datetime, timezone
            query = 'SELECT status, expires_at FROM entitlements WHERE tenant_id = %s AND feature_id = %s'
            res = self.global_db.fetch_one(query, (tenant_id, feature_id))
            
            if not res or res['status'] != 'active':
                return False
            
            expires_at = res['expires_at']
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at and expires_at < datetime.now(timezone.utc):
                # Auto-revoke on expiration
                self.global_db.execute(
                    "UPDATE entitlements SET status = 'suspended' WHERE tenant_id = %s AND feature_id = %s",
                    (tenant_id, feature_id)
                )
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error verifying feature {feature_id} for tenant {tenant_id}: {e}")
            return False

    def update_subscription(self, tenant_id: str, new_plan: str, additional_credits: int = 0) -> Dict[str, Any]:
        """Actualiza el plan de suscripción y añade créditos a un tenant."""
        try:
            # Actualizar plan y sumar créditos
            self.global_db.execute(
                "UPDATE tenants SET plan = %s, credits = credits + %s WHERE id = %s",
                (new_plan, additional_credits, tenant_id)
            )
            self.logger.info(f"Suscripción actualizada para {tenant_id}: {new_plan}, +{additional_credits} créditos.")
            return {"status": "success", "message": f"Plan actualizado a {new_plan} exitosamente."}
        except Exception as e:
            self.logger.error(f"Error updating subscription: {e}")
            return {"status": "error", "message": str(e)}
