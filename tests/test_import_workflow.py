import unittest
import os
import json
import pandas as pd
from src.core.database import DatabaseManager
from src.core.stock_service import StockService
from src.core.import_service import ImportService
from src.commands.dispatcher import CommandDispatcher

class TestFlexibleImport(unittest.TestCase):
    def setUp(self):
        # Setup DB and services
        # We use a dedicated schema for testing to avoid affecting production data
        self.db = DatabaseManager("test_import_workflow")
        self.db._init_db()
        self.stock_service = StockService(self.db)
        self.import_service = ImportService(self.stock_service)
        self.dispatcher = CommandDispatcher(self.db, self.stock_service, None, None)
        
        # Create the sample CSV
        self.csv_path = "tests/sample_foreign_stock.csv"
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("Referencia,Nombre Producto,Precio Venta,Existencias,Categoría\n")
            f.write("REF001,Producto A,10.50,100,Electronica\n")
            f.write("REF002,Producto B,20.00,50,Hogar\n")

    def test_full_import_workflow(self):
        # 1. Preview (should auto-detect or needs_mapping)
        preview = self.import_service.preview_import(self.csv_path)
        self.assertEqual(preview["status"], "success")
        self.assertIn("Referencia", preview["mapping_used"]["codigo"])
        self.assertIn("Nombre Producto", preview["mapping_used"]["nombre"])
        
        # 2. Test custom mapping
        custom_mapping = {
            "codigo": "Referencia",
            "nombre": "Nombre Producto",
            "precio": "Precio Venta",
            "cantidad": "Existencias",
            "categoria": "Categoría"
        }
        preview_custom = self.import_service.preview_import(self.csv_path, custom_mapping=custom_mapping)
        self.assertEqual(preview_custom["status"], "success")
        self.assertEqual(preview_custom["data"][0]["mapped"]["precio"], 10.50)
        self.assertEqual(preview_custom["data"][1]["mapped"]["precio"], 20.0) # Cleaning test (20,00 -> 20.0)

        # 3. Save Profile
        save_res = self.dispatcher.execute("stock.import.save_profile", {
            "mapping_id": "TestSaaS",
            "mapping": custom_mapping
        }, current_user_role="admin")
        self.assertEqual(save_res["status"], "success")
        
        # 4. Use Profile
        preview_profile = self.import_service.preview_import(self.csv_path, mapping_id="TestSaaS")
        self.assertEqual(preview_profile["status"], "success")
        self.assertEqual(preview_profile["mapping_used"], custom_mapping)

        # 5. Commit
        commit_res = self.import_service.commit_import(preview_profile["data"])
        self.assertEqual(commit_res["status"], "success")
        
        # Verify in DB
        prod = self.stock_service.get_product("REF001")
        self.assertEqual(prod["status"], "success")
        self.assertEqual(prod["data"]["nombre"], "Producto A")

if __name__ == "__main__":
    unittest.main()
