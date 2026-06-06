# 🧪 Suite de Pruebas de Stock Pro

Este directorio contiene las herramientas de validación para asegurar el correcto funcionamiento de la API, el sistema de permisos y los flujos de negocio.

## 🚀 Requisitos Previos

Para ejecutar cualquier test, el servidor debe estar activo localmente:
```bash
export DATABASE_URL="tu_url_de_postgresql"
python3 main.py
```

## 🖥️ Pruebas de Interfaz (UI Diagnostic)
Utiliza Playwright para simular la interacción de un usuario real en el navegador.

- **`test_ui_master.py`**: Ejecuta un flujo completo en el panel administrativo. 
    - **Modo Diagnóstico**: Mide la latencia (ms) de cada acción.
    - **Detección de Bugs**: Captura el estado del DOM y toma capturas de pantalla (`debug_failure.png`) cuando un elemento no aparece o una acción falla.
    - **Validación de Flujos**: Prueba el Setup Master $\rightarrow$ Login $\rightarrow$ Dashboard $\rightarrow$ Suscripciones $\rightarrow$ Usuarios.

**Ejecución:**
```bash
python3 tests/test_ui_master.py
```

### ⏱️ Análisis de Latencias
El script de UI reporta el tiempo exacto de respuesta del sistema:
- **Carga de Página**: Tiempo de respuesta del servidor web.
- **Acciones End-to-End**: Tiempo desde el clic hasta que la UI refleja el cambio (incluyendo viaje al servidor y respuesta de la DB).


## 📋 Matriz de Comandos Validados

| Componente | Comando | Validado en | Tipo |
| :--- | :--- | :--- | :--- |
| **Auth** | `auth.login` | `test_master`, `test_user` | Público |
| **Auth** | `auth.register_owner` | `test_user` | Público |
| **Stock** | `stock.add` | `test_user` | Owner/Admin |
| **Ventas** | `venta.cobrar` | `test_user` | Empleado/Admin |
| **Sist.** | `sys.subscription.update` | `test_master` | MASTER |
| **Sist.** | `sys.admin.users_list` | `test_master` | MASTER |
| **Sist.** | `debug.call` | `test_master` | MASTER |

## ⚠️ Notas Importantes
- **Sincronización**: Si cambias la URL del servidor, actualiza la variable `URL` en los scripts de la carpeta `/tests`.
- **PostgreSQL**: Todos los tests interactúan con la base de datos configurada en `DATABASE_URL`. Ten cuidado al ejecutar `reset_master.py` en entornos de producción.
