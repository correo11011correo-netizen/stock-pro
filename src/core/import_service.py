import logging
import json
import os
from typing import List, Dict, Any, Optional
from .import_adapters import get_adapter
from .stock_service import StockService

class ImportService:
    """
    Servicio de Importación Universal de Stock.
    Permite cargar datos desde múltiples formatos y mapearlos dinámicamente.
    Sigue el estándar de auditoría AUDIT-DEBUG.
    """
    
    def __init__(self, stock_service: StockService):
        self.stock_service = stock_service
        self.logger = logging.getLogger("ImportService")
        # Ruta absoluta para evitar errores de contexto de ejecución
        # Ruta relativa a la carpeta data del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.profiles_path = os.path.join(base_dir, "data", "import_profiles.json")

    def _load_profiles(self) -> Dict[str, Dict[str, str]]:
        """Carga los perfiles de mapeo desde el JSON."""
        try:
            if not os.path.exists(self.profiles_path):
                return {}
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading import profiles: {e}")
            return {}

    def _map_row(self, row: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Traduce una fila de datos crudos a los campos internos del sistema.
        Realiza limpieza básica de tipos y valida campos obligatorios.
        """
        mapped = {}
        for internal_field, source_col in mapping.items():
            val = row.get(source_col)
            
            # Limpieza básica según el campo
            if internal_field in ['precio', 'cantidad']:
                try:
                    if val is not None:
                        # Eliminar símbolos de moneda, comas de miles y espacios
                        clean_val = str(val).replace('$', '').replace('€', '').replace('£', '').replace(',', '').strip()
                        # Manejar el caso donde el punto es el separador de miles y la coma el decimal (común en algunos países)
                        if ',' in clean_val and '.' not in clean_val:
                            clean_val = clean_val.replace(',', '.')
                        val = float(clean_val)
                except (ValueError, TypeError):
                    val = 0.0
            
            if internal_field == 'es_peso':
                # Convertir a boolean si es string ('yes', '1', 'true')
                if isinstance(val, str):
                    val = val.lower() in ['yes', '1', 'true', 'si', 'true', 'v']
                elif isinstance(val, (int, float)):
                    val = bool(val)
            
            mapped[internal_field] = val
        
        # Validación de campos obligatorios
        if not mapped.get('codigo') or not mapped.get('nombre'):
            raise ValueError("Faltan campos obligatorios: 'codigo' o 'nombre' no pudieron ser mapeados o están vacíos.")
        
        return mapped

    def _auto_detect_mapping(self, raw_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Analiza las cabeceras de los datos crudos y detecta automáticamente 
        el mapeo basándose en un set extendido de palabras clave.
        """
        if not raw_data:
            return {}

        headers = list(raw_data[0].keys())
        detected_mapping = {}
        
        # Diccionario de patrones: Campo Interno -> Lista de palabras clave
        patterns = {
            'codigo': ['codigo', 'code', 'sku', 'id', 'barcode', 'ean', 'ref', 'referencia', 'articulo_id', 'item_code'],
            'nombre': ['nombre', 'name', 'producto', 'item', 'descripcion', 'desc', 'artículo', 'title', 'label', 'product_name'],
            'precio': ['precio', 'price', 'cost', 'valor', 'monto', 'unit_price', 'precio_venta', 'costo_unitario', 'sale_price'],
            'cantidad': ['cantidad', 'qty', 'quantity', 'stock', 'amount', 'existencia', 'inventario', 'disponibilidad', 'stock_level'],
            'categoria': ['categoria', 'category', 'tipo', 'type', 'grupo', 'group', 'familia', 'dept', 'department'],
            'es_peso': ['peso', 'weight', 'kilo', 'kg', 'is_weight', 'gramos', 'unit_type', 'medida']
        }

        for internal_field, keywords in patterns.items():
            for header in headers:
                header_lower = header.lower()
                if any(kw in header_lower for kw in keywords):
                    detected_mapping[internal_field] = header
                    break
        
        self.logger.info(f"Auto-detección completada: {detected_mapping}")
        return detected_mapping

    def save_mapping_profile(self, mapping_id: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Guarda un perfil de mapeo para su uso futuro.
        """
        try:
            profiles = self._load_profiles()
            profiles[mapping_id] = mapping
            
            # Asegurar que el directorio de datos existe
            os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
            
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"Perfil de mapeo '{mapping_id}' guardado exitosamente.")
            return {"status": "success", "message": f"Perfil '{mapping_id}' guardado correctamente."}
        except Exception as e:
            self.logger.error(f"Error saving import profile: {e}")
            return {"status": "error", "message": f"Error al guardar el perfil: {str(e)}"}

    def preview_import(self, file_path: str, mapping_id: Optional[str] = None, custom_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Previsualiza la importación. Lee el archivo, aplica el mapeo (o lo detecta) 
        y devuelve los datos sin insertarlos en la base de datos.
        Si no hay mapeo, devuelve el estado 'needs_mapping'.
        """
        try:
            # 1. Obtener adaptador y leer datos
            adapter = get_adapter(file_path)
            raw_data = adapter.read(file_path)
            
            if not raw_data:
                return {"status": "error", "message": "El archivo está vacío."}
            
            # 2. Resolver el mapeo
            mapping = custom_mapping
            if not mapping and mapping_id:
                profiles = self._load_profiles()
                mapping = profiles.get(mapping_id)
            
            if not mapping:
                mapping = self._auto_detect_mapping(raw_data)
            
            # SI NO HAY MAPEO (ni automático ni manual), devolvemos los datos crudos para que el usuario mapee
            if not mapping:
                return {
                    "status": "needs_mapping", 
                    "message": "Se requiere definir el mapeo de columnas.",
                    "headers": list(raw_data[0].keys()),
                    "sample_data": raw_data[:5] # Enviamos las primeras 5 filas como ejemplo
                }

            # 3. Mapear todas las filas
            preview_data = []
            for i, row in enumerate(raw_data, start=1):
                try:
                    mapped = self._map_row(row, mapping)
                    preview_data.append({
                        "row": i,
                        "original": row,
                        "mapped": mapped
                    })
                except Exception as e:
                    preview_data.append({
                        "row": i,
                        "original": row,
                        "error": str(e)
                    })

            return {
                "status": "success",
                "data": preview_data,
                "count": len(preview_data),
                "mapping_used": mapping
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def commit_import(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Inserta una lista de productos ya validados y editados desde la UI.
        """
        success_count = 0
        error_count = 0

        for item in data_list:
            try:
                # Extraemos los datos mapeados del item
                d = item.get('mapped', {})
                result = self.stock_service.add_product(
                    codigo=d.get('codigo'),
                    nombre=d.get('nombre'),
                    precio=d.get('precio'),
                    cantidad=d.get('cantidad'),
                    categoria=d.get('categoria'),
                    es_peso=d.get('es_peso', False)
                )
                if result["status"] == "success":
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        return {
            "status": "success",
            "message": f"Importación finalizada. {success_count} cargados, {error_count} errores.",
            "stats": {"success": success_count, "errors": error_count}
        }

    def _audit_db(self, accion: str, detalle: str):
        """Persiste el log de auditoría en la tabla 'audit' de la base de datos."""

        try:
            # Usamos la db del stock_service
            query = "INSERT INTO audit (usuario, accion, detalle) VALUES (%s, %s, %s)"
            # Como no tenemos el usuario actual aquí, usamos 'SYSTEM_IMPORT'
            self.stock_service.db.execute(query, ("SYSTEM_IMPORT", accion, detalle))
        except Exception as e:
            self.logger.error(f"Error escribiendo en tabla audit: {e}")

