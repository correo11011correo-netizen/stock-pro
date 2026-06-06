# Guía de Instalación y Uso: App Web PWA Stock Pro

Esta guía describe cómo desplegar e instalar la versión híbrida (PWA) de Stock Pro.

## 🚀 Despliegue
La App Web se sirve desde la ruta `/appweb/index.html` del servidor principal.

### Requisitos del Servidor
- Puerto `8888` abierto.
- Variable de entorno `DATABASE_URL` configurada (Railway).
- Acceso a la carpeta `src/ui/appweb/`.

## 📲 Instalación en el Dispositivo (Android/Chrome)
1. Abra el navegador Chrome en su dispositivo.
2. Acceda a `http://<IP_SERVIDOR>:8888/appweb/index.html`.
3. Una vez cargada la página, Chrome detectará el `manifest.json` y el `sw.js`.
4. Aparecerá un banner de **"Agregar a la pantalla de inicio"**. Haga clic en él.
5. Ahora la aplicación aparecerá en su menú de apps como una aplicación nativa.

## 🛠️ Funcionamiento Híbrido

### Modo Online (Luz Azul)
- **Login**: Requiere conexión obligatoria para validar el rol y el token.
- **Admin**: El acceso a los módulos de gestión (Inventario, Usuarios) requiere conexión activa.
- **Sincronización**: Al presionar `Sync`, la app descarga el stock más reciente del servidor.

### Modo Offline (Luz Roja)
- **Ventas**: Puede realizar ventas sin internet. Estas se guardan en una cola local (`IndexedDB`).
- **Stock**: La búsqueda de productos funciona instantáneamente usando la caché local.
- **Resiliencia**: Al recuperar la conexión, presione `Sync` para subir todas las ventas pendientes al servidor.

## 🔑 Credenciales de Prueba (Entorno Dev)
- **Dueño**: `dueno_test` / `Password123!`
- **Empleado**: `empleado_test` / `Password123!`
