import os
import hashlib
import uuid
from src.core.global_db import GlobalDatabaseManager

def seed_master():
    print("🌱 Sembrando usuario MASTER para pruebas...")
    # Usamos la misma configuración que el servidor
    db = GlobalDatabaseManager()
    
    username = "123"
    password = "123"
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    user_id = "master_test_123"
    
    try:
        # Eliminar si ya existe para evitar conflictos
        db.execute("DELETE FROM users WHERE username = %s", (username,))
        
        # Insertar MASTER
        db.execute(
            "INSERT INTO users (id, username, password_hash, role, tenant_id) VALUES (%s, %s, %s, 'MASTER', NULL)",
            (user_id, username, pwd_hash)
        )
        print("✅ Usuario MASTER (123/123) creado exitosamente.")
    except Exception as e:
        print(f"❌ Error sembrando MASTER: {e}")

if __name__ == "__main__":
    seed_master()
