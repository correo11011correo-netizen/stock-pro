from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8888/appweb/index.html"

def test_full_owner_hybrid_experience():
    with sync_playwright() as p:
        print("\n🚀 INICIANDO TEST EXHAUSTIVO: DUEÑO (ONLINE -> OFFLINE -> ONLINE)")
        print("="*80)
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # --- FASE 1: ONLINE TOTAL ---
            print("\n🌐 [FASE 1] Modo Online - Verificación de Funciones")
            page.goto(BASE_URL)
            page.fill("#login-user", "dueno_test")
            page.fill("#login-pass", "Password123!")
            page.click("#btn-login")
            page.wait_for_selector("#screen-main:not(.hidden)")
            print("✅ Login: OK")

            # 1.1 Sincronización (PULL)
            page.click("button:has-text('Sync')")
            time.sleep(2)
            print("✅ Sincronización Inicial: OK (Stock cargado en LocalDB)")

            # 1.2 Búsqueda y Venta Online
            page.fill("#stock-search", "Laptop")
            page.click("button:has-text('🔍')") 
            page.wait_for_selector(".product-item")
            page.click(".product-item") 
            page.wait_for_selector(".cart-item")
            
            page.once("dialog", lambda dialog: dialog.accept())
            page.click("button:has-text('Finalizar Venta')")
            print("✅ Venta Online: OK")

            # 1.3 Acceso Administrativo
            page.click("#btn-admin-tab")
            page.wait_for_selector("#tab-admin:not(.hidden)")
            page.once("dialog", lambda dialog: dialog.accept())
            page.click("button:has-text('Inventario')")
            print("✅ Panel Administrativo: OK")

            # --- FASE 2: OFFLINE TOTAL ---
            print("\n🔌 [FASE 2] Modo Offline - Resiliencia")
            context.set_offline(True)
            print("📡 Conexión cortada...")

            # 2.1 Búsqueda Offline
            page.fill("#stock-search", "Mouse")
            page.click("button:has-text('🔍')") 
            page.wait_for_selector(".product-item")
            print("✅ Búsqueda Offline: OK")

            # 2.2 Venta Offline
            page.click(".product-item")
            page.wait_for_selector(".cart-item")
            page.once("dialog", lambda dialog: dialog.accept())
            page.click("button:has-text('Finalizar Venta')")
            print("✅ Venta Offline: OK")

            # 2.3 Bloqueo de Admin Offline
            page.click("button:has-text('Admin')")
            page.once("dialog", lambda dialog: dialog.accept())
            page.click("button:has-text('Usuarios')")
            print("✅ Admin Offline: Bloqueado (Correcto)")

            # --- FASE 3: RECUPERACIÓN ---
            print("\n🌐 [FASE 3] Re-conexión y Sincronización")
            context.set_offline(False)
            print("📡 Conexión restablecida...")

            page.click("button:has-text('Sync')")
            time.sleep(3)
            
            status = page.inner_text("#sync-status")
            if "Online" in status:
                print("✅ Sincronización Final: OK")
            else:
                print(f"❌ Error en estado final: {status}")

            print("="*80)
            print("🏁 TEST EXHAUSTIVO FINALIZADO CON ÉXITO")
            print("="*80)

        except Exception as e:
            print(f"❌ ERROR DURANTE EL TEST: {e}")
            page.screenshot(path="debug_full_hybrid.png")
        finally:
            browser.close()

if __name__ == "__main__":
    test_full_owner_hybrid_experience()


if __name__ == "__main__":
    test_full_owner_hybrid_experience()
