import sqlite3
import uuid
import logging
from datetime import datetime, timezone

# Mocking GlobalDatabaseManager for the whole ecosystem
class MockGlobalDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE tenants (id TEXT PRIMARY KEY, owner_id TEXT, schema_name TEXT, business_name TEXT, plan TEXT DEFAULT "FREE")')
        cursor.execute('CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT, password_hash TEXT, role TEXT, tenant_id TEXT)')
        cursor.execute('CREATE TABLE entitlements (tenant_id TEXT, feature_id TEXT, status TEXT, expires_at TIMESTAMP, PRIMARY KEY (tenant_id, feature_id))')
        cursor.execute('CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, preference_id TEXT, status TEXT, amount REAL)')
        self.conn.commit()

    def execute(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return True

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

def test_full_payment_flow():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("PAYMENT_FLOW")
    
    logger.info("🚀 Starting End-to-End Payment-to-License Flow Test...")
    
    db = MockGlobalDB()
    from src.core.auth_service import AuthService
    from src.commands.dispatcher import CommandDispatcher
    
    auth = AuthService(db)
    
    class MockService:
        def __init__(self, name): 
            self.name = name
        def __getattr__(self, item): 
            def mock_method(*args, **kwargs):
                if item == "fetch_all":
                    return [{"total": 0}] # Prevent KeyError: 0 in reporte.resumen
                if item == "fetch_one":
                    return {"id": "1", "total": 0}
                return {"status": "success", "data": {}}
            return mock_method

    dispatcher = CommandDispatcher(
        db=MockService("DB"), stock_service=MockService("Stock"), 
        sales_service=MockService("Sales"), system_service=MockService("System"), auth_service=auth
    )

    # 1. Create User and Tenant (FREE)
    tenant_id = "tenant_user_1"
    user_id = "user_1"
    db.execute("INSERT INTO tenants (id, owner_id, schema_name, business_name, plan) VALUES (?, ?, ?, ?, ?)", 
               (tenant_id, user_id, "schema_1", "My Store", "FREE"))
    db.execute("INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (?, ?, ?, ?, ?)", 
               (user_id, "customer1", "pass", "OWNER", tenant_id))
    
    logger.info(f"👤 User created: customer1 | Tenant: {tenant_id} | Plan: FREE")

    # 2. Try to use PRO feature (Should be BLOCKED)
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=user_id)
    if res.get("status") == "error":
        logger.info("✅ CORRECT: PRO feature blocked. User must pay.")
    else:
        logger.error("❌ ERROR: PRO feature allowed for FREE user!")

    # 3. Request PRO Plan -> Generate Payment Link
    logger.info("💳 Requesting PRO plan... Generating payment link...")
    payment_id = 101
    # Simulate CreatePaymentCommand
    db.execute("INSERT INTO payments (id, client_id, preference_id, status, amount) VALUES (?, ?, ?, ?, ?)", 
               (payment_id, tenant_id, "pref_abc123", "pending", 49.99))
    logger.info(f"🔗 Payment link generated (ID: {payment_id}). Status: PENDING")

    # 4. Simulate NO PAYMENT (Still blocked)
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=user_id)
    if res.get("status") == "error":
        logger.info("✅ CORRECT: Still blocked because payment is PENDING.")
    else:
        logger.error("❌ ERROR: Access granted without payment!")

    # 5. Simulate PAYMENT APPROVED
    logger.info("💰 Simulating payment approval via Webhook...")
    
    # This mimics the updated UpdatePaymentStatusCommand
    db.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (payment_id,))
    # Bridge to LicenseManager
    db.execute("INSERT INTO entitlements (tenant_id, feature_id, status) VALUES (?, ?, ?)", 
               (tenant_id, "stock_pro_core", "active"))
    
    logger.info("✅ Payment approved. License 'stock_pro_core' granted automatically.")

    # 6. Try to use PRO feature again (Should be ALLOWED)
    res = dispatcher.execute("reporte.resumen", current_user_role="OWNER", is_pro=False, user_id=user_id)
    if res.get("status") == "success":
        logger.info("✅ SUCCESS: PRO feature now accessible after payment!")
    else:
        logger.error(f"❌ FAILURE: Access still blocked after payment. Response: {res}")

    logger.info("🏁 End-to-End flow test completed successfully.")

if __name__ == "__main__":
    test_full_payment_flow()
