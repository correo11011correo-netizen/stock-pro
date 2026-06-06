import psycopg2
import os

# URL de la base de datos proporcionada por el usuario
DB_URL = "postgresql://postgres:ThHGlEAhaKKprgVhDbnaNaektrgZuIth@acela.proxy.rlwy.net:16919/railway"

def reset_master():
    print("🧹 Iniciando limpieza de cuenta MASTER en producción...")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cursor:
            # Buscamos si existe un MASTER
            cursor.execute("SELECT username FROM users WHERE role = 'MASTER'")
            master = cursor.fetchone()
            
            if master:
                print(f"🗑️ Eliminando usuario MASTER actual: {master[0]}")
                cursor.execute("DELETE FROM users WHERE role = 'MASTER'")
                conn.commit()
                print("✅ Cuenta MASTER eliminada exitosamente.")
            else:
                print("ℹ️ No se encontró ninguna cuenta MASTER para eliminar.")
                
        conn.close()
    except Exception as e:
        print(f"❌ Error durante el reset: {e}")

if __name__ == "__main__":
    reset_master()
