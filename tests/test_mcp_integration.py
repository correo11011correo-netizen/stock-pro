import sqlite3
import uuid
import logging
from datetime import datetime, timedelta, timezone

# Mocking GlobalDatabaseManager to use SQLite for local testing
class MockGlobalDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # Tenants
        cursor.execute('''
            CREATE TABLE tenants (
                id TEXT PRIMARY KEY,
                owner_id TEXT,
                schema_name TEXT UNIQUE NOT NULL,
                business_name TEXT,
                plan TEXT DEFAULT 'FREE',
                credits INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Users
        cursor.execute('''
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                tenant_id TEXT REFERENCES tenants(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        # Entitlements (The core of the Master Control Plane)
        cursor.execute('''
            CREATE TABLE entitlements (
                tenant_id TEXT REFERENCES tenants(id),
                feature_id TEXT,
                status TEXT,
                expires_at TIMESTAMP,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tenant_id, feature_id)
            )
        ''')
        # Sessions
        cursor.execute('''
            CREATE TABLE sessions (
                token TEXT PRIMARY KEY,
                user_data TEXT,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        self.conn.commit()

    def execute(self, query, params=()):
        # Convert %s to ? for SQLite
        query = query.replace("%s", "?")
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return None

    def fetch_one(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def fetch_all(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

# Integration Test Suite
def test_master_control_plane():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MCP_TEST")
    
    logger.info("🚀 Starting Master Control Plane Integration Test...")
    
    # 1. Setup Environment
    db = MockGlobalDB()
    from src.core.auth_service import AuthService
    from src.commands.dispatcher import CommandDispatcher
    
    auth = AuthService(db)
    # Mock other services for the dispatcher
    class MockService:
        def __init__(self, name): 
            self.name = name
        def __getattr__(self, item): 
            def mock_method(*args, **kwargs):
                if item == "fetch_all":
                    return [{"total": 0}] # Return a list to satisfy sales[0] access
                if item == "fetch_one":
                    return {"id": "1", "total": 0}
                return {"status": "success", "data": {}, "message": f"Mock {item} executed in {self.name}"}
            return mock_method

    dispatcher = CommandDispatcher(
        db=MockService("DB"), 
        stock_service=MockService("Stock"), 
        sales_service=MockService("Sales"), 
        system_service=MockService("System"), 
        auth_service=auth
    )

    # 2. Create a Test Tenant
    tenant_id = "tenant_test_123"
    owner_id = "user_test_123"
    db.execute("INSERT INTO tenants (id, owner_id, schema_name, business_name, plan) VALUES (?, ?, ?, ?, ?)", 
               (tenant_id, owner_id, "schema_test", "Test Business", "FREE"))
    db.execute("INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (?, ?, ?, ?, ?)", 
               (owner_id, "testuser", "hash", "OWNER", tenant_id))

    # -------------------------------------------------------------------------
    # TEST 1: Blocked Access (No License)
    # -------------------------------------------------------------------------
    logger.info("🧪 Test 1: Verifying that PRO features are BLOCKED without license...")
    # 'reporte.resumen' is marked as es_pro=True in dispatcher.py
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=owner_id)
    
    if res.get("status") == "error" and "versión PRO" in res.get("message", ""):
        logger.info("✅ SUCCESS: PRO feature blocked as expected.")
    else:
        logger.error(f"❌ FAILURE: PRO feature was NOT blocked. Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 2: Grant License -> Access Granted
    # -------------------------------------------------------------------------
    logger.info("🧪 Test 2: Granting 'stock_pro_core' license and verifying access...")
    
    # Simulate LicenseManager granting license
    db.execute("INSERT INTO entitlements (tenant_id, feature_id, status) VALUES (?, ?, ?)", 
               (tenant_id, "stock_pro_core", "active"))
    
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=owner_id)
    
    if res.get("status") == "success":
        logger.info("✅ SUCCESS: Access granted after license activation.")
    else:
        logger.error(f"❌ FAILURE: Access still blocked after granting license. Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 3: Revoke License -> Access Blocked
    # -------------------------------------------------------------------------
    logger.info("🧪 Test 3: Revoking license and verifying immediate block...")
    
    db.execute("UPDATE entitlements SET status = 'suspended' WHERE tenant_id = ? AND feature_id = ?", 
               (tenant_id, "stock_pro_core"))
    
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=owner_id)
    
    if res.get("status") == "error" and "versión PRO" in res.get("message", ""):
        logger.info("✅ SUCCESS: Access blocked immediately after revocation.")
    else:
        logger.error(f"❌ FAILURE: Access was NOT blocked after revocation. Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 4: WhatsApp Hub Access (Simulated)
    # -------------------------------------------------------------------------
    logger.info("🧪 Test 4: Simulating WhatsApp Hub access enforcement...")
    
    # Simulation of what happens in WhatsApp Hub's validate_session()
    def simulate_whatsapp_validate(user_data):
        if user_data.get("role") == "MASTER": return True
        tenant_id = user_data.get("tenant_id")
        ent = db.fetch_one("SELECT status FROM entitlements WHERE tenant_id = ? AND feature_id = ?", (tenant_id, "whatsapp_hub_core"))
        return ent and ent["status"] == "active"

    # User without WA license
    user_data_no_wa = {"id": owner_id, "username": "testuser", "role": "OWNER", "tenant_id": tenant_id}
    if not simulate_whatsapp_validate(user_data_no_wa):
        logger.info("✅ SUCCESS: WhatsApp Hub access denied without license.")
    else:
        logger.error("❌ FAILURE: WhatsApp Hub access granted without license.")

    # Grant WA license
    db.execute("INSERT INTO entitlements (tenant_id, feature_id, status) VALUES (?, ?, ?)", 
               (tenant_id, "whatsapp_hub_core", "active"))
    
    if simulate_whatsapp_validate(user_data_no_wa):
        logger.info("✅ SUCCESS: WhatsApp Hub access granted after license activation.")
    else:
        logger.error("❌ FAILURE: WhatsApp Hub access denied even with active license.")

    logger.info("🏁 All Master Control Plane local tests completed.")

if __name__ == "__main__":
    test_master_control_plane()
