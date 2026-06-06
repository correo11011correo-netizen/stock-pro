#!/bin/bash
# Script para crear una rama de producción para Railway y subirla a GitHub

echo "🚀 Iniciando subida de configuración para Railway..."

# 1. Configuración de Credenciales
TOKEN="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"
USER="software-0ficial"
REPO_URL="https://github.com/software-0ficial/stock-pro.git"
BRANCH_NAME="railway-prod"

echo "📦 Configurando remoto y rama..."

# Eliminar remoto origin si ya existe para evitar conflictos
git remote remove origin 2>/dev/null

# Agregar el remoto con el token para autenticación automática
git remote add origin "https://$USER:$TOKEN@github.com/software-0ficial/stock-pro.git"

# 3. Crear y cambiar a la rama de Railway
git checkout -b $BRANCH_NAME

# 4. Subir los cambios
echo "📤 Subiendo código a la rama $BRANCH_NAME..."
git push -u origin $BRANCH_NAME

if [ $? -eq 0 ]; then
    echo "✅ ¡Éxito! El proyecto ha sido subido a la rama '$BRANCH_NAME'."
    echo "🔗 Ahora puedes ir a Railway y conectar el repo: $REPO_URL/tree/$BRANCH_NAME"
else
    echo "❌ Error al subir el código. Verifica que el token tenga permisos de escritura (repo scope)."
    exit 1
fi
