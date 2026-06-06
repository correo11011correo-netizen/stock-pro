# Architecture Documentation: Stock Pro

## 1. Visión General
Stock Pro es un sistema SaaS diseñado para la gestión de inventarios en entornos multi-tenant. Su núcleo es un orquestador de comandos que garantiza la seguridad y el aislamiento de datos.

## 2. Modelo de Datos y Multi-tenancy
El sistema implementa la estrategia de **Esquemas Dinámicos**.

### Estructura de DB
- **Esquema `public` (Global):**
    - `tenants`: Registro de negocios, sus planes y esquemas asociados.
    - `users`: Usuarios globales con sus roles y relación con un tenant.
ightarrow$ llaves de permiso.
    - `sessions`: Tokens de acceso activos.
- **Esquema `tenant_X` (Local):**
    - `products`: Inventario específico del negocio.
    - `sales` / `sale_items`: Historial de transacciones.
    - `audit`: Log de acciones internas del negocio.
    - `cash_box`: Estado de la caja diaria.

### Aislamiento
El `DatabaseManager` configura el `search_path` de PostgreSQL al inicio de cada conexión, asegurando que las consultas `SELECT * FROM products` se dirijan automáticamente al esquema del cliente activo.

## 3. Flujo de Seguridad y Autorización
Cada petición sigue este camino de validación:
1. **Autenticación:** El `WebServer` valida el token en la tabla `sessions`.
2. **Resolución de Contexto:** Se obtiene el `tenant_id` y el `rol` del usuario.
3. **Dispatcher Validation:**
ightarrow$ Error 404.
ightarrow$ Ejecutar (God Mode).
ightarrow$ Error 403.
    - ¿El rol es suficiente? (Jerarquía: MASTER > admin > empleado > gratis).
ightarrow$ Error 403.
4. **Ejecución:** El handler del Dispatcher invoca el método del servicio correspondiente.

## 4. Motor de Sincronización Híbrido (PWA & Mobile Sync)
El sistema permite la operación offline mediante un modelo de **Eventual Consistency**, implementando una Progressive Web App (PWA) instalable.

### Infraestructura Frontend
- **Service Worker**: Gestiona el caché de assets estáticos y garantiza que la aplicación sea accesible sin conexión.
- **IndexedDB (LocalDB)**: Almacena la caché de productos, la sesión del usuario y una cola de eventos pendientes (`sync_queue`).

### Flujo Offline $\rightarrow$ Online (Push)
1. La App registra una acción (ej. `venta.nueva`) en la cola de `IndexedDB`.
2. Al detectar internet o solicitar sincronización, la app envía el lote de eventos al endpoint `/api/sync/push`.
3. El `SyncService` procesa los eventos secuencialmente en el servidor.
4. Si un evento falla, se reporta en la respuesta para su resolución manual o automática.

### Flujo Online $\rightarrow$ Offline (Pull)
1. La App solicita el estado actual del stock mediante `/api/sync/pull`.
2. El servidor devuelve el estado actualizado de los productos.
3. La App actualiza la `IndexedDB` local, permitiendo búsquedas y ventas instantáneas sin red.

## 5. Resiliencia y Sentinel Pattern
El software está envuelto en un orquestador que gestiona el ciclo de vida:
- **Heartbeats:** Monitoreo constante de la salud del servidor.
- **Sentinel Service:** Gestión de versiones y despliegues.
- **Actualizaciones Atómicas:** Las nuevas versiones se despliegan en carpetas separadas y se activan mediante el cambio de un enlace simbólico, permitiendo rollbacks instantáneos si se detectan errores en la nueva versión.
