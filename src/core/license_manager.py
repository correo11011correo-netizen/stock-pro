import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from .global_db import GlobalDatabaseManager

class LicenseManager:
    """
    Motor de Gestión de Licencias y Entitlements.
    Centraliza la concesión, revocación y verificación de funcionalidades
    a través de todo el ecosistema (Stock Pro, WhatsApp Hub, etc.).
    """
    
    def __init__(self, global_db: GlobalDatabaseManager):
        self.global_db = global_db
        self.logger = logging.getLogger("LicenseManager")

    def grant_feature(self, tenant_id: str, feature_id: str, duration_days: Optional[int] = None, admin_id: str = "SYSTEM") -> Dict[str, Any]:
        """
        Otorga una funcionalidad a un tenant. 
        Si duration_days es None, la licencia es perpetua.
        """
        try:
            expires_at = None
            if duration_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
            
            query = '''
                INSERT INTO entitlements (tenant_id, feature_id, status, expires_at)
                VALUES (%s, %s, 'active', %s)
                ON CONFLICT (tenant_id, feature_id) 
                DO UPDATE SET 
                    status = 'active', 
                    expires_at = EXCLUDED.expires_at,
                    granted_at = CURRENT_TIMESTAMP
            '''
            self.global_db.execute(query, (tenant_id, feature_id, expires_at))
            
            # Log de auditoría
            self.log_action(admin_id, tenant_id, feature_id, "GRANT", "SUCCESS", f"Licencia otorgada por {duration_days if duration_days else 'perpetuo'} días.")
            
            return {"status": "success", "message": f"Feature {feature_id} otorgada a {tenant_id}."}
        except Exception as e:
            self.logger.error(f"Error granting feature {feature_id} to {tenant_id}: {e}")
            self.log_action("SYSTEM", tenant_id, feature_id, "GRANT", "ERROR", str(e))
            return {"status": "error", "message": str(e)}

    def revoke_feature(self, tenant_id: str, feature_id: str, admin_id: str = "SYSTEM") -> Dict[str, Any]:
        """
        Revoca una funcionalidad cambiando su estado a 'suspended'.
        """
        try:
            query = "UPDATE entitlements SET status = 'suspended' WHERE tenant_id = %s AND feature_id = %s"
            self.global_db.execute(query, (tenant_id, feature_id))
            
            self.log_action(admin_id, tenant_id, feature_id, "REVOKE", "SUCCESS", "Funcionalidad suspendida.")
            return {"status": "success", "message": f"Feature {feature_id} revocada para {tenant_id}."}
        except Exception as e:
            self.logger.error(f"Error revoking feature {feature_id} from {tenant_id}: {e}")
            self.log_action("SYSTEM", tenant_id, feature_id, "REVOKE", "ERROR", str(e))
            return {"status": "error", "message": str(e)}

    def verify_feature(self, tenant_id: str, feature_id: str) -> bool:
        """
        Verifica si un tenant tiene una licencia activa y no expirada para una funcionalidad.
        Este método es el corazón de la seguridad del ecosistema.
        """
        try:
            query = '''
                SELECT status, expires_at 
                FROM entitlements 
                WHERE tenant_id = %s AND feature_id = %s
            '''
            res = self.global_db.fetch_one(query, (tenant_id, feature_id))
            
            if not res:
                return False
            
            if res['status'] != 'active':
                return False
            
            if res['expires_at']:
                # Verificar si ha expirado (usando UTC para Railway)
                from datetime import datetime, timezone
                if res['expires_at'] < datetime.now(timezone.utc):
                    # Auto-suspender si expiró
                    self.revoke_feature(tenant_id, feature_id, admin_id="SYSTEM_EXPIRATION")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error verifying feature {feature_id} for {tenant_id}: {e}")
            return False

    def audit_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Retorna todas las funcionalidades y sus estados para un tenant.
        """
        try:
            query = "SELECT feature_id, status, expires_at FROM entitlements WHERE tenant_id = %s"
            results = self.global_db.fetch_all(query, (tenant_id,))
            return [dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error auditing tenant {tenant_id}: {e}")
            return []

    def log_action(self, admin_id: str, tenant_id: str, feature_id: str, action: str, status: str, detail: str):
        """
        Registra la acción en la tabla de admin_logs para auditoría profesional.
        """
        try:
            # Formato: [ACTION] FEATURE: feature_id | DETAIL: detail
            log_detail = f"[{action}] FEATURE: {feature_id} | STATUS: {status} | DETAIL: {detail}"
            query = "INSERT INTO admin_logs (admin_id, action, details) VALUES (%s, %s, %s)"
            self.global_db.execute(query, (admin_id, "LICENSE_MGMT", log_detail))
        except Exception as e:
            self.logger.error(f"Error writing to admin_logs: {e}")
