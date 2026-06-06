from playwright.sync_api import sync_playwright
import time
from datetime import datetime

BASE_URL = "http://localhost:8888/admin_dashboard.html"

def measure_action(action_name, func):
    """Wrapper para medir la latencia de una acción."""
    start = time.perf_counter()
    try:
        result = func()
        end = time.perf_counter()
        duration = (end - start) * 1000
        print(f"⏱️  [{action_name}] Duración: {duration:.2f}ms")
        return result, duration
    except Exception as e:
        end = time.perf_counter()
        duration = (end - start) * 1000
        print(f"❌ [{action_name}] FALLÓ después de {duration:.2f}ms. Error: {e}")
        raise e

def test_ui_diagnostic_mode():
    with sync_playwright() as p:
        print("🚀 INICIANDO MODO DE DIAGNÓSTICO DE UI (Admin OS Mobile)")
        print("="*70)
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # --- PASO 1: CARGA INICIAL ---
            def load_page():
                page.goto(BASE_URL)
            measure_action("Carga de Página Inicial", load_page)

            # --- PASO 2: SETUP MASTER ---
            def setup_master():
                page.click("text=Crear cuenta MASTER")
                page.wait_for_selector("#section-setup.active")
                page.fill("#setup-username", "diag_master")
                page.fill("#setup-password", "Diag_Pass123!")
                page.click("button:has-text('Finalizar Configuración')")
                page.wait_for_selector("#toast:not(.hidden)")
                page.click("#toast")
            measure_action("Creación de Cuenta MASTER", setup_master)

            # --- PASO 3: LOGIN ---
            def do_login():
                page.fill("#login-username", "diag_master")
                page.fill("#login-password", "Diag_Pass123!")
                page.click("button:has-text('Iniciar Sesión')")
                page.wait_for_selector("#app:not(.hidden)")
            measure_action("Autenticación y Carga de App", do_login)

            # --- PASO 4: NAVEGACIÓN Y KPIs ---
            def check_dashboard():
                page.click("text=Dashboard")
                page.wait_for_selector("#kpi-tenants")
                val = page.inner_text("#kpi-tenants")
                if val == "—": raise Exception("KPIs no cargados")
            measure_action("Carga de Dashboard y KPIs", check_dashboard)

            # --- PASO 5: GESTIÓN DE SUSCRIPCIÓN ---
            def update_subscription():
                page.click("text=Negocios")
                page.wait_for_selector("#tenants-list")
                
                # Verificar que hay al menos una tarjeta de negocio
                cards = page.locator("#tenants-list .glass-card")
                if cards.count() == 0: raise Exception("No hay tarjetas de negocio")
                
                page.click("button:has-text('Suscripción')")
                page.wait_for_selector("#modal-subscription:not(.hidden)")
                page.select_option("#sub-plan", "PRO")
                page.fill("#sub-credits", "1000")
                page.click("button:has-text('Guardar')")
                page.wait_for_selector("#toast:not(.hidden)")
                page.click("#toast")
            measure_action("Actualización de Suscripción (End-to-End)", update_subscription)

            # --- PASO 6: GESTIÓN de USUARIOS ---
            def suspend_user():
                page.click("text=Usuarios")
                page.wait_for_selector("#users-list")
                
                # Buscar el botón de suspender en la primera tarjeta de usuario
                btn = page.locator("button:has-text('Suspender')").first
                if btn.count() == 0: raise Exception("No hay botón de suspender")
                btn.click()
                
                page.wait_for_selector("#modal-user-status:not(.hidden)", timeout=5000)
                confirm_btn = page.locator("#user-modal-confirm-btn")
                if confirm_btn.count() == 0: raise Exception("Botón Confirmar ausente")
                confirm_btn.click()
                page.wait_for_selector("#toast:not(.hidden)")
                page.click("#toast")
            measure_action("Flujo de Suspensión de Usuario", suspend_user)

            print("="*70)
            print("🏁 DIAGNÓSTICO DE INTERFAZ FINALIZADO CON ÉXITO")
            print("="*70)

        except Exception as e:
            print(f"❌ ERROR CRÍTICO: {e}")
            page.screenshot(path="debug_failure.png")
        finally:
            browser.close()

if __name__ == "__main__":
    test_ui_diagnostic_mode()
