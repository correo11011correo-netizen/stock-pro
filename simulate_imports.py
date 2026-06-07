import requests
import json
import time

BASE_URL = "http://localhost:8888"
SAMPLES = [
    {
        "file": "data/samples/shopify_export.csv",
        "profile": "Shopify",
        "mapping": {"codigo": "Handle", "nombre": "Title", "precio": "Variant Price", "cantidad": "Variant Inventory Qty", "categoria": "Product Type"}
    },
    {
        "file": "data/samples/corp_stock.xlsx",
        "profile": "Corporate",
        "mapping": {"codigo": "Código Interno", "nombre": "Descripción Artículo", "precio": "Precio Venta Unitario", "cantidad": "Existencias Actuales", "categoria": "Categoría Grupo"}
    },
    {
        "file": "data/samples/legacy_system.txt",
        "profile": "Legacy",
        "mapping": {"codigo": "sku", "nombre": "item", "precio": "cost", "cantidad": "qty", "categoria": "dept"}
    },
    {
        "file": "data/samples/api_export.json",
        "profile": "API_Export",
        "mapping": {"codigo": "id", "nombre": "name", "precio": "price", "cantidad": "stock", "categoria": "category"}
    },
    {
        "file": "data/samples/messy_data.csv",
        "profile": "Messy",
        "mapping": {"codigo": "ART_ID", "nombre": "LABEL", "precio": "VALUE", "cantidad": "AMOUNT", "categoria": "TAG"}
    }
]

def run_simulation():
    print("🚀 Starting Import Simulation Workflow...")
    
    # 0. Login to get a token
    print("🔐 Step 0: Logging in...")
    login_res = requests.post(BASE_URL, json={
        "command": "auth.login",
        "user": "asd",
        "pass": "asd"
    })
    token = login_res.json().get("payload", {}).get("token")
    if not token:
        print("❌ Login failed. Cannot proceed.")
        return
    print(f"Token acquired: {token[:10]}...")

    for sample in SAMPLES:
        print(f"\n--- Testing File: {sample['file']} ---")
        
        # 1. Preview with auto-detect
        print("🔍 Step 1: Previewing with auto-detect...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.preview", 
            "file_path": sample['file'],
            "token": token
        })
        payload = res.json().get("payload", {})
        print(f"Result: {payload.get('status', 'error')}")
        
        # 2. Preview with custom mapping
        print("🎯 Step 2: Previewing with custom mapping...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.preview", 
            "file_path": sample['file'], 
            "custom_mapping": sample['mapping'],
            "token": token
        })
        preview_data = res.json().get("payload", {}).get("data", [])
        print(f"Mapped {len(preview_data)} items.")
        
        # 3. Save Profile
        print(f"💾 Step 3: Saving profile '{sample['profile']}'...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.save_profile", 
            "mapping_id": sample['profile'], 
            "mapping": sample['mapping'],
            "token": token
        })
        payload = res.json().get("payload", {})
        print(f"Saved: {payload.get('status', 'error')}")
        
        # 4. Commit
        print("✅ Step 4: Committing to DB...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.commit", 
            "data_list": preview_data,
            "token": token
        })
        payload = res.json().get("payload", {})
        print(f"Commit result: {payload.get('message', 'Error')}")
        
    print("\n✨ All simulations completed!")

if __name__ == "__main__":
    # Wait for server to start
    time.sleep(2)
    try:
        run_simulation()
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
