import pandas as pd
import json
import logging
from typing import List, Dict, Any
from abc import ABC, abstractmethod
import os

class BaseImportAdapter(ABC):
    """Clase base abstracta para adaptadores de importación."""
    
    @abstractmethod
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        """Lee un archivo y retorna una lista de diccionarios."""
        pass

class CSVAdapter(BaseImportAdapter):
    """Adaptador para archivos CSV y TXT delimitados."""
    
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            # Intentamos detectar el delimitador común
            df = pd.read_csv(file_path, sep=None, engine='python')
            return df.to_dict('records')
        except Exception as e:
            logging.error(f"Error reading CSV {file_path}: {e}")
            raise e

class ExcelAdapter(BaseImportAdapter):
    """Adaptador para archivos Excel (.xlsx, .xls)."""
    
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            df = pd.read_excel(file_path)
            return df.to_dict('records')
        except Exception as e:
            logging.error(f"Error reading Excel {file_path}: {e}")
            raise e

class JSONAdapter(BaseImportAdapter):
    """Adaptador para archivos JSON."""
    
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Asegurar que sea una lista
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logging.error(f"Error reading JSON {file_path}: {e}")
            raise e

def get_adapter(file_path: str) -> BaseImportAdapter:
    """Factoría para obtener el adaptador según la extensión del archivo."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv' or ext == '.txt':
        return CSVAdapter()
    elif ext in ['.xlsx', '.xls']:
        return ExcelAdapter()
    elif ext == '.json':
        return JSONAdapter()
    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}")
