#!/bin/bash

# Helper script para interactuar con la API del Sistema de Stock y Escaneo via curl
# Permite depurar el backend y el dispatcher sin necesidad de cargar el navegador.

API_URL="http://localhost:8888"

# Colores para la salida
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Herramienta de Pruebas de API - Stock Scan ===${NC}"
echo -e "Servidor: $API_URL\n"

# Función para ejecutar peticiones POST
execute_cmd() {
    local cmd=$1
    local params=$2
    local role=${3:-"empleado"}
    local pro=${4:-"false"}

    echo -e "${BLUE}Ejecutando: ${NC}$cmd (Role: $role, Pro: $pro)"
    echo -e "Params: $params"
    
    # Usamos una variable para el JSON para evitar problemas de escapado
    local json_payload=$(cat <<EOF
{
    "command": "$cmd",
    "params": $params,
    "role": "$role",
    "is_pro": $pro
}
EOF
)

    curl -s -X POST "$API_URL/" \
        -H "Content-Type: application/json" \
        -d "$json_payload" | jq .
    echo -e "\n--------------------------------------------------\n"
}

# 1. Prueba de Configuración (GET)
echo -e "${GREEN}[1/5] Probando GET /api/config...${NC}"
curl -s "$API_URL/api/config" | jq .
echo -e "\n--------------------------------------------------\n"

# 2. Listar Stock
echo -e "${GREEN}[2/5] Probando stock.list...${NC}"
execute_cmd "stock.list" "{}" "empleado" "false"

# 3. Agregar Producto (Simulado)
echo -e "${GREEN}[3/5] Probando stock.add...${NC}"
execute_cmd "stock.add" '{"codigo": "PROD-001", "nombre": "Prueba Curl", "cantidad": 10, "precio": 100.0, "categoria": "General"}' "admin" "true"

# 4. Crear Venta
echo -e "${GREEN}[4/5] Probando venta.cobrar...${NC}"
execute_cmd "venta.cobrar" '{"cliente": "Cliente Curl", "items": [{"codigo": "PROD-001", "cantidad": 1}], "metodo_pago": "Efectivo", "paga_con": 110.0}' "empleado" "false"

# 5. Información del Sistema
echo -e "${GREEN}[5/5] Probando sys.info...${NC}"
execute_cmd "sys.info" "{}" "admin" "true"

echo -e "${BLUE}=== Pruebas Completadas ===${NC}"
echo -e "Revisa la consola donde corre 'python3 main.py' para ver los logs detallados."
