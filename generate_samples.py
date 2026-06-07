import pandas as pd
import json
import os

# Ensure directory exists
os.makedirs("data/samples", exist_ok=True)

# 1. CSV - Standard English (Shopify style)
df1 = pd.DataFrame({
    "Handle": ["prod-1", "prod-2"],
    "Title": ["iPhone 13", "Samsung S22"],
    "Variant Price": ["999.99", "850.00"],
    "Variant Inventory Qty": [10, 15],
    "Product Type": ["Phones", "Phones"]
})
df1.to_csv("data/samples/shopify_export.csv", index=False)

# 2. XLSX - Spanish Corporate (Enterprise style)
df2 = pd.DataFrame({
    "Código Interno": ["C001", "C002"],
    "Descripción Artículo": ["Silla Oficina", "Mesa Director"],
    "Precio Venta Unitario": [120.50, 450.00],
    "Existencias Actuales": [5, 2],
    "Categoría Grupo": ["Muebles", "Muebles"]
})
df2.to_excel("data/samples/corp_stock.xlsx", index=False)

# 3. TXT - Pipe Delimited (Legacy system style)
with open("data/samples/legacy_system.txt", "w", encoding="utf-8") as f:
    f.write("sku|item|cost|qty|dept\n")
    f.write("L001|Cable HDMI|5.99|100|Accesorios\n")
    f.write("L002|Adaptador USB|12.50|50|Accesorios\n")

# 4. JSON - API Export (Modern SaaS style)
json_data = [
    {
        "id": "api-1",
        "name": "Teclado Mecánico",
        "price": 89.90,
        "stock": 20,
        "category": "Periféricos"
    },
    {
        "id": "api-2",
        "name": "Mouse Gamer",
        "price": 45.00,
        "stock": 30,
        "category": "Periféricos"
    }
]
with open("data/samples/api_export.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=4)

# 5. CSV - Messy format (Strange headers and currency symbols)
df5 = pd.DataFrame({
    "ART_ID": ["M001", "M002"],
    "LABEL": ["Monitor 24", "Monitor 27"],
    "VALUE": ["$200,00", "$300,00"], # Testing the cleaning logic
    "AMOUNT": [8, 4],
    "TAG": ["Hardware", "Hardware"]
})
df5.to_csv("data/samples/messy_data.csv", index=False)

print("✅ 5 sample files generated in data/samples/")
