# 📦 Stock Pro

**Stock Pro** es un sistema de gestión de inventario y ventas profesional diseñado bajo un modelo **SaaS Multi-tenant**. Permite a múltiples negocios gestionar sus productos, ventas y personal en un entorno aislado y seguro, con soporte para operaciones híbridas (Online/Offline) a través de una aplicación móvil.

## 🚀 Características Principales

- **Aislamiento Total (Multi-tenancy):** Cada negocio posee su propio esquema de base de datos en PostgreSQL, garantizando que los datos nunca se mezclen.
- **Arquitectura de Comandos:** Implementa el *Dispatcher Pattern* para desacoplar la interfaz de la lógica de negocio.
- **Modo Híbrido Móvil:** App adaptable (Android/iOS/Web) con capacidad de realizar ventas offline y sincronizarse automáticamente al recuperar la conexión.
- **Seguridad Granular (PBAC):** Control de acceso basado en roles (`MASTER`, `admin`, `empleado`, `gratis`) y permisos específicos por función.
- **Resiliencia:** Implementación del *Sentinel Pattern* para actualizaciones atómicas y rollbacks instantáneos.

## 🛠️ Instalación y Configuración

### Requisitos
- Python 3.10+
- PostgreSQL (Recomendado Railway o instancia local)

### Configuración de Entorno
Crea un archivo `.env` o configura las variables de entorno en tu sistema:
```env
DATABASE_URL=postgres://user:password@host:port/dbname
PORT=8888
```

### Ejecución
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicia el sistema:
   ```bash
   python3 main.py
   ```

## 🌐 Accesos
- **Panel de Administración (Master):** `http://localhost:8888/admin`
- **App Móvil Híbrida:** `http://localhost:8888/apk/www/index.html`

## 🛡️ Licenciamiento
El sistema soporta planes **FREE** y **PRO**. Las funcionalidades PRO (como reportes avanzados y exportaciones masivas) se habilitan dinámicamente a través del Dispatcher basándose en el plan del tenant.
