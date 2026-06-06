from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:8888/appweb/index.html"

def run_workflow(browser, username, password, expected_role, checks):
    print(f"\n🧪 PROBANDO FLUJO DE TRABAJO: {username} ({expected_role})")
    print("-" * 50)
    page = browser.new_page()
    try:
        page.goto(BASE_URL)
        page.fill("#login-user", username)
        page.fill("#login-pass", password)
        page.click("#btn-login")
        page.wait_for_selector("#screen-main:not(.hidden)", timeout=10000)
        
        role_badge = page.inner_text("#user-role-badge")
        print(f"✅ Login exitoso. Rol detectado: {role_badge}")
        
        for check_name, selector, should_be_visible in checks:
            is_visible = "hidden" not in (page.locator(selector).get_attribute("class") or "")
            status = "✅" if is_visible == should_be_visible else "❌"
            print(f"{status} {check_name}: {'Visible' if is_visible else 'Oculto'} (Esperado: {'Visible' if should_be_visible else 'Oculto'})")
            
        page.close()
    except Exception as e:
        print(f"❌ Error en flujo de {username}: {e}")
        page.screenshot(path=f"debug_{username}.png")
        page.close()

def test_all_roles():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Definición de flujos
        workflows = [
            {
                "user": "empleado_test",
                "pass": "Password123!",
                "role": "EMPLOYEE",
                "checks": [
                    ("Tab Stock", "button:has-text('Stock')", True),
                    ("Tab Ventas", "button:has-text('Ventas')", True),
                    ("Tab Admin", "#btn-admin-tab", False),
                ]
            },
            {
                "user": "dueno_test",
                "pass": "Password123!",
                "role": "OWNER",
                "checks": [
                    ("Tab Stock", "button:has-text('Stock')", True),
                    ("Tab Ventas", "button:has-text('Ventas')", True),
                    ("Tab Admin", "#btn-admin-tab", True),
                ]
            }
        ]
        
        for wf in workflows:
            run_workflow(browser, wf["user"], wf["pass"], wf["role"], wf["checks"])
            
        browser.close()

if __name__ == "__main__":
    test_all_roles()
