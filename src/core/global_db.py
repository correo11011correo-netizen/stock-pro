from psycopg2 import pool, extras
import os
import logging

class GlobalDatabaseManager:
    """
    Gestor de la base de datos maestra.
    Contiene la tabla de usuarios, tenants y permisos globales.
    Usa el esquema 'public' por defecto.
    """
    def __init__(self):
        self.logger = logging.getLogger("GlobalDatabaseManager")
        self.db_url = os.environ.get("DATABASE_URL")
        if not self.db_url:
            self.logger.critical("DATABASE_URL no encontrada.")
            raise Exception("Error: Railway DATABASE_URL no configurada.")
        
        try:
            self.pool = pool.ThreadedConnectionPool(1, 20, dsn=self.db_url)
            self.logger.info("Global Database Pool inicializado.")
        except Exception as e:
            self.logger.critical(f"Error inicializando el pool de la DB global: {e}")
            raise e

        self._init_global_db()

    def _get_connection(self):
        return self.pool.getconn()

    def _return_connection(self, conn):
        self.pool.putconn(conn)

    def _init_global_db(self):
        """Crea las tablas maestras en el esquema public."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # 1. Tabla de Tenants (Negocios)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tenants (
                        id TEXT PRIMARY KEY,
                        owner_id TEXT,
                        schema_name TEXT UNIQUE NOT NULL,
                        business_name TEXT,
                        plan TEXT DEFAULT 'FREE',
                        credits INTEGER DEFAULT 10,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 2. Tabla de Usuarios
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        tenant_id TEXT REFERENCES tenants(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 3. Tabla de Permisos Granulares
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS permissions (
                        tenant_id TEXT REFERENCES tenants(id),
                        user_id TEXT REFERENCES users(id),
                        permission_key TEXT,
                        granted BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (tenant_id, user_id, permission_key)
                    )
                ''')
                # 4. Migración: columna is_active en users (suspensión de cuentas)
                cursor.execute('''
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
                ''')
                # Backfill: asegurar que filas existentes sin valor tengan is_active = TRUE
                cursor.execute('''
                    UPDATE users SET is_active = TRUE WHERE is_active IS NULL
                ''')

                # 5. Tabla de Logs de Administración (auditoría de acciones MASTER)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admin_logs (
                        id SERIAL PRIMARY KEY,
                        admin_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 6. Tabla de Sesiones (Persistencia para multi-process/Railway)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        token TEXT PRIMARY KEY,
                        user_data JSONB NOT NULL,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                    )
                ''')
                
                # Índice en token para acelerar la validación de sesión
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token)')
                
                # 7. Tabla de Configuración de Bots de WhatsApp (SaaS Multi-tenant)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_bot_settings (
                        tenant_id TEXT PRIMARY KEY REFERENCES tenants(id),
                        whatsapp_token TEXT NOT NULL,
                        phone_id TEXT NOT NULL,
                        verify_token TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 8. Tabla de Entitlements (Licencias de funcionalidades)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS entitlements (
                        id SERIAL PRIMARY KEY,
                        tenant_id TEXT REFERENCES tenants(id),
                        feature_id TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP WITH TIME ZONE,
                        UNIQUE(tenant_id, feature_id)
                    )
                ''')

                # --- OPTIMIZACIONES DE RENDIMIENTO (ÍNDICES) ---
                # Acelerar login y búsqueda de usuarios por tenant
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id)')
                # Acelerar búsqueda de tenants por nombre o plan
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tenants_business_name ON tenants (business_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants (plan)')

                # Migración: convertir columna expires_at a TIMESTAMP WITH TIME ZONE si existe como naive
                cursor.execute('''
                    ALTER TABLE sessions
                        ALTER COLUMN expires_at TYPE TIMESTAMP WITH TIME ZONE
                        USING expires_at AT TIME ZONE 'UTC'
                ''')
                # Índice en expires_at para acelerar la limpieza de sesiones expiradas
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at)
                ''')

                conn.commit()
                self.logger.info("Global Database initialized successfully in schema 'public'.")
            self._return_connection(conn)
        except Exception as e:
            self.logger.error(f"Error initializing global DB: {e}")
            raise e

    def execute(self, query, params=()):
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
            self._return_connection(conn)
            return True
        except Exception as e:
            self.logger.error(f"Global execute error: {e}")
            return None

    def fetch_one(self, query, params=()):
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                res = cursor.fetchone()
            self._return_connection(conn)
            return res
        except Exception as e:
            self.logger.error(f"Global fetch_one error: {e}")
            return None

    def fetch_all(self, query, params=()):
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                res = cursor.fetchall()
            self._return_connection(conn)
            return res
        except Exception as e:
            self.logger.error(f"Global fetch_all error: {e}")
            return []
