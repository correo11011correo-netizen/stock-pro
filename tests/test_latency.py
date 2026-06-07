import requests
import time
import json
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://127.0.0.1:8888"
MASTER_USER = "123"
MASTER_PASS = "123"

def measure_latency(name: str, method: str, endpoint: str, payload: Any = None, headers: Dict = None):
    url = f"{BASE_URL}{endpoint}"
    headers = headers or {}
    
    start_time = time.perf_counter()
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=5)
        else:
            print(f"Unsupported method: {method}")
            return None
        
        end_time = time.perf_counter()
        latency = (end_time - start_time) * 1000
        return {
            "name": name,
            "status": response.status_code,
            "latency": latency,
            "success": response.ok
        }
    except Exception as e:
        print(f"Error testing {name}: {e}")
        return {
            "name": name,
            "status": "Error",
            "latency": -1,
            "success": False
        }

def run_latency_tests():
    print("🚀 Starting API Latency Benchmark...")
    print("-" * 60)
    
    # 1. Authentication - Get Master Token
    print("🔑 Authenticating as MASTER...")
    login_data = {"username": MASTER_USER, "password": MASTER_PASS}
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    
    if not login_res.ok:
        print("❌ Failed to login as MASTER. Using dummy token for protected routes (will likely fail 403/401).")
        token = "dummy_token"
    else:
        token = login_res.json().get("payload", {}).get("token", "no_token")
        print("✅ Authenticated successfully.")

    master_headers = {"Authorization": token}

    # 2. Define Test Suite
    tests = [
        # Public Endpoints
        ("Health Check", "GET", "/api/health", None, {}),
        ("System Config", "GET", "/api/config", None, {}),
        ("Public Login", "POST", "/api/auth/login", login_data, {}),
        
        # Master Endpoints
        ("Admin Dashboard", "GET", "/api/admin/dashboard", None, master_headers),
        ("Admin Tenants", "GET", "/api/admin/tenants", None, master_headers),
        ("Admin Users", "GET", "/api/admin/users", None, master_headers),
        ("Admin Audit Logs", "GET", "/api/admin/audit-logs", None, master_headers),
        
        # Dispatcher Commands
        ("Sys Info Cmd", "POST", "/", {"command": "sys.info"}, master_headers),
    ]

    results = []
    for name, method, endpoint, payload, headers in tests:
        res = measure_latency(name, method, endpoint, payload, headers)
        if res:
            results.append(res)
            status_icon = "✅" if res["success"] else "❌"
            print(f"{status_icon} {name:<20} | Status: {res['status']:<5} | Latency: {res['latency']:>8.2f}ms")

    # 3. Summary
    print("-" * 60)
    success_count = sum(1 for r in results if r["success"])
    avg_latency = sum(r["latency"] for r in results if r["latency"] > 0) / max(1, success_count)
    
    print(f"📊 Results: {success_count}/{len(results)} successful")
    print(f"⏱️  Average Latency (Successful): {avg_latency:.2f}ms")
    print("-" * 60)

if __name__ == "__main__":
    run_latency_tests()
