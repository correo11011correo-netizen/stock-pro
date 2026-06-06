# Project Guidelines: Stock Pro (SaaS Multi-Tenant)

Este archivo es la fuente de verdad técnica para el desarrollo de Stock Pro. Cualquier cambio debe adherirse a estas reglas.

## 🏗️ 1. Arquitectura de Comandos (Dispatcher Pattern)
El sistema utiliza un `CommandDispatcher` como orquestador central. La UI nunca llama a los servicios directamente.

### Flujo de un nuevo comando:
1. **Lógica:** Implementar la función en el servicio correspondiente (`src/core/stock_service.py`, etc.).
2. **Handler:** Crear el método `_handle_comando` en `src/commands/dispatcher.py`.
3. **Mapeo:** Agregar al `commands_map` con la firma: 
   `"comando": (handler, rol_minimo, es_pro, llave_permiso)`

## 🛡️ 2. Modelo de Seguridad y Acceso (PBAC)
El sistema implementa un Control de Acceso Basado en Permisos (Permission-Based Access Control).

### Jerarquía de Roles:
`MASTER` (Acceso Global) $\rightarrow$ `admin` (Acceso Total Tenant) $\rightarrow$ `empleado` (Acceso Granular) $\rightarrow$ `gratis` (Básico).

### Reglas de Validación:
- **God Mode:** Usuarios `master_` o rol `MASTER` saltan todas las validaciones.
- **Permisos Granulares:** Los empleados requieren la llave específica (ej. `perm_stock_write`) para ejecutar acciones sensibles.
- **Licencias PRO:** Si un comando está marcado como `es_pro=True`, se valida que el tenant tenga un plan `PRO` o `ENTERPRISE`.

## 🗄️ 3. Estrategia de Datos (Multi-tenancy)
El sistema utiliza **Aislamiento por Esquemas** en PostgreSQL.

- **DB Global (`public`):** Almacena la tabla de `tenants`, `users` y `sessions`.
- **DB Tenant (`schema_name`):** Cada negocio tiene su propio esquema con tablas de `products`, `sales`, `audit`, etc.
- **Resolución:** El `WebServer` identifica el `tenant_id` del token y ejecuta `SET search_path TO schema_name, public` antes de cada consulta.

## 🔄 4. Sincronización Híbrida (Offline-First)
Para la App Móvil, se implementa un motor de sincronización bidireccional.

- **Push (Móvil $\rightarrow$ Servidor):** Los eventos offline se guardan en `IndexedDB` $\rightarrow$ se envían como lote al endpoint `/api/sync/push` $\rightarrow$ el `SyncService` los procesa secuencialmente.
- **Pull (Servidor $\rightarrow$ Móvil):** El móvil solicita el "delta" de stock mediante `/api/sync/pull` para actualizar su caché local.

## 🚀 5. Resiliencia (Sentinel Pattern)
El software debe ser capaz de actualizarse sin downtime.
- **Orquestador:** `SentinelService` gestiona las versiones.
- **Atomicidad:** Las actualizaciones se instalan en paralelo y se activan mediante el cambio de un enlace simbólico (`current` $\rightarrow$ `vX.Y.Z`).

## 🔍 6. Auditoría y Debugging
- **`debug.call`**: Comando maestro para validar funciones internas sin crear comandos públicos.
- **Trazabilidad:** Todas las importaciones y acciones críticas se registran en la tabla `audit` con prefijos específicos (`AUDIT-DEBUG`).
