import psycopg2
from psycopg2 import pool, extras
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

class DatabaseManager:
    """
    Gestor de persistencia de datos optimizado para PostgreSQL en Railway.
    Implementa aislamiento total mediante Schemas dinámicos por negocio.
    """
    
    def __init__(self, schema_name="public"):
        self.schema_name = schema_name
        self.logger = logging.getLogger("DatabaseManager")
        
        # Configuración de conexión desde variables de entorno de Railway
        self.db_url = os.environ.get("DATABASE_URL")
        if not self.db_url:
            self.logger.critical("DATABASE_URL no encontrada en las variables de entorno.")
            raise Exception("Error: Railway DATABASE_URL no configurada.")

        # Usamos un Pool de conexiones para evitar abrir/cerrar conexiones constantemente
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20, dsn=self.db_url
            )
            self.logger.info(f"PostgreSQL Pool inicializado para el esquema: {self.schema_name}")
        except Exception as e:
            self.logger.critical(f"Error conectando al Pool de PostgreSQL: {e}")
            raise e


    def _get_connection(self):
        """Obtiene una conexión del pool y configura el esquema actual."""
        conn = self.pool.getconn()
        # Guardamos el esquema actual en el objeto de conexión para evitar SET search_path redundantes
        if not hasattr(conn, '_current_schema') or conn._current_schema != self.schema_name:
            with conn.cursor() as cursor:
                cursor.execute(f"SET search_path TO {self.schema_name}, public")
            conn._current_schema = self.schema_name
        return conn

    def _return_connection(self, conn):
        """Devuelve la conexión al pool."""
        self.pool.putconn(conn)

    def _init_db(self):
        """Crea el esquema y las tablas necesarias si no existen."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # 1. Crear esquema dinámico para el cliente
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
                
                # 2. Tabla de Productos
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.products (
                        codigo TEXT PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        precio NUMERIC(12, 2) NOT NULL,
                        cantidad NUMERIC(12, 3) DEFAULT 0,
                        categoria TEXT,
                        es_peso BOOLEAN DEFAULT FALSE,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 3. Tabla de Ventas
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.sales (
                        id SERIAL PRIMARY KEY,
                        total NUMERIC(12, 2) NOT NULL,
                        cliente TEXT,
                        metodo_pago TEXT,
                        paga_con NUMERIC(12, 2),
                        vuelto NUMERIC(12, 2),
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 4. Detalle de Ventas
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.sale_items (
                        id SERIAL PRIMARY KEY,
                        sale_id INTEGER REFERENCES {self.schema_name}.sales(id),
                        product_codigo TEXT REFERENCES {self.schema_name}.products(codigo),
                        cantidad NUMERIC(12, 3),
                        subtotal NUMERIC(12, 2)
                    )
                ''')
                
                # 5. Auditoría
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.audit (
                        id SERIAL PRIMARY KEY,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        usuario TEXT,
                        accion TEXT,
                        detalle TEXT
                    )
                ''')
                
                # 6. Caja y Turnos
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.cash_box (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        abierta BOOLEAN DEFAULT FALSE,
                        efectivo_inicial NUMERIC(12, 2) DEFAULT 0,
                        ventas_efectivo NUMERIC(12, 2) DEFAULT 0,
                        ventas_digital NUMERIC(12, 2) DEFAULT 0,
                        hora_apertura TIMESTAMP,
                        hora_cierre TIMESTAMP,
                        monto_cierre_real NUMERIC(12, 2)
                    )
                ''')
                cursor.execute(f"INSERT INTO {self.schema_name}.cash_box (id, abierta) VALUES (1, FALSE) ON CONFLICT DO NOTHING")
                
                # 7. Alias de Clientes
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.aliases (
                        id TEXT PRIMARY KEY,
                        nombre TEXT UNIQUE NOT NULL,
                        limite NUMERIC(12, 2) DEFAULT 0,
                        acumulado NUMERIC(12, 2) DEFAULT 0
                    )
                ''')
                
                # 8. Configuraciones
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                
                conn.commit()
                self.logger.info(f"PostgreSQL DB initialized for schema: {self.schema_name}")
            self._return_connection(conn)
        except Exception as e:
            self.logger.error(f"Critical Error initializing Postgres DB: {e}")
            raise e

    def execute(self, query, params=()):
        """Ejecuta una consulta (INSERT, UPDATE, DELETE)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.fetchone()[0] if cursor.description and len(cursor.description) == 1 else None
        except Exception as e:
            self.logger.error(f"Query Error: {query} | Params: {params} | Error: {e}")
            conn.rollback()
            return None
        finally:
            self._return_connection(conn)

    def execute_many(self, query, params_list):
        """Ejecuta una consulta múltiples veces."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"ExecuteMany Error: {query} | Error: {e}")
            conn.rollback()
            return None
        finally:
            self._return_connection(conn)

    def fetch_one(self, query, params=()):
        """Retorna una sola fila como diccionario."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"FetchOne Error: {query} | Error: {e}")
            return None
        finally:
            self._return_connection(conn)

    def fetch_all(self, query, params=()):
        """Retorna todas las filas como lista de diccionarios."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"FetchAll Error: {query} | Error: {e}")
            return []
        finally:
            self._return_connection(conn)
