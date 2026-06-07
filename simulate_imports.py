import requests
import json
import time

BASE_URL = "http://localhost:8080"
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
    
    for sample in SAMPLES:
        print(f"
--- Testing File: {sample['file']} ---")
        
        # 1. Preview with auto-detect
        print("🔍 Step 1: Previewing with auto-detect...")
        res = requests.post(BASE_URL, json={"command": "stock.import.preview", "file_path": sample['file']})
        print(f"Result: {res.json()['status']}")
        
        # 2. Preview with custom mapping
        print("🎯 Step 2: Previewing with custom mapping...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.preview", 
            "file_path": sample['file'], 
            "custom_mapping": sample['mapping']
        })
        preview_data = res.json().get("data", [])
        print(f"Mapped {len(preview_data)} items.")
        
        # 3. Save Profile
        print(f"💾 Step 3: Saving profile '{sample['profile']}'...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.save_profile", 
            "mapping_id": sample['profile'], 
            "mapping": sample['mapping']
        })
        print(f"Saved: {res.json()['status']}")
        
        # 4. Commit
        print("✅ Step 4: Committing to DB...")
        res = requests.post(BASE_URL, json={
            "command": "stock.import.commit", 
            "data_list": preview_data
        })
        print(f"Commit result: {res.json()['message']}")
        
    print("
✨ All simulations completed!")

if __name__ == "__main__":
    # Wait for server to start
    time.sleep(2)
    try:
        run_simulation()
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
