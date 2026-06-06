from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8888/appweb/index.html"

def test_appweb_login():
    with sync_playwright() as p:
        print("🚀 TESTEANDO INICIO DE SESIÓN - APP WEB PWA")
        print("="*60)
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Carga de la App Web
            print("📂 Cargando página...")
            page.goto(BASE_URL)
            page.wait_for_selector("#screen-login")
            print("✅ Página de login cargada")

            # 2. Intento de Login (Usando credenciales recién creadas)
            print("🔑 Intentando iniciar sesión...")
            page.fill("#login-user", "test_final_user")
            page.fill("#login-pass", "Password123!")
            page.click("#btn-login")

            # 3. Verificación de Transición
            # Esperamos a que screen-login tenga la clase 'hidden' y screen-main no la tenga
            print("⏳ Verificando transición de pantalla...")
            page.wait_for_selector("#screen-main:not(.hidden)", timeout=10000)
            
            login_screen = page.locator("#screen-login")
            if "hidden" in (login_screen.get_attribute("class") or ""):
                print("✅ Pantalla de login oculta")
            else:
                raise Exception("La pantalla de login sigue visible")

            print("✅ Pantalla principal visible")

            # 4. Verificación de Rol y UI
            print("👤 Verificando datos de usuario...")
            role_badge = page.inner_text("#user-role-badge")
            print(f"Rol detectado: {role_badge}")
            
            # Para test_final_user, el rol es OWNER.
            if "OWNER" in role_badge.upper() or "MASTER" in role_badge.upper():
                admin_btn = page.locator("#btn-admin-tab")
                if "hidden" not in (admin_btn.get_attribute("class") or ""):
                    print("✅ Botón de Admin visible para rol OWNER/MASTER")
                else:
                    raise Exception("Botón de Admin debería ser visible para OWNER")

            print("="*60)
            print("🏁 TEST DE LOGIN APP WEB FINALIZADO CON ÉXITO")
            print("="*60)

        except Exception as e:
            print(f"❌ ERROR EN TEST: {e}")
            page.screenshot(path="debug_appweb_failure.png")
            print("📸 Captura de pantalla guardada en debug_appweb_failure.png")
        finally:
            browser.close()

if __name__ == "__main__":
    test_appweb_login()
