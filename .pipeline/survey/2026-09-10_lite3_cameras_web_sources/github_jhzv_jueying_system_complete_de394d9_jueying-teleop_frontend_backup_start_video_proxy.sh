#!/bin/bash

# ==============================================================================
# JUEYING VIDEO STREAM PROXY
# Convierte RTSP del robot a HTTP/MJPEG para navegadores
# ==============================================================================

echo "=============================================="
echo "  Jueying Lite3 - Video Stream Proxy"
echo "=============================================="
echo ""

# Configuración
ROBOT_IP="192.168.1.120"
RTSP_PORT="8554"
RTSP_STREAM="test"
HTTP_PORT="8081"

RTSP_URL="rtsp://${ROBOT_IP}:${RTSP_PORT}/${RTSP_STREAM}"

echo "📹 Configuración:"
echo "  - RTSP origen: ${RTSP_URL}"
echo "  - HTTP puerto: ${HTTP_PORT}"
echo "  - Acceso: http://localhost:${HTTP_PORT}/stream"
echo ""

# Verificar conectividad con el robot
echo "🔍 Verificando conectividad con robot..."
if ping -c 1 -W 2 ${ROBOT_IP} > /dev/null 2>&1; then
    echo "✅ Robot alcanzable en ${ROBOT_IP}"
else
    echo "❌ No se puede alcanzar el robot en ${ROBOT_IP}"
    echo "   Verifica la conexión de red"
    exit 1
fi

# Verificar que ffmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "❌ FFmpeg no está instalado"
    echo ""
    echo "Para instalar:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    exit 1
fi

echo ""
echo "🚀 Iniciando proxy de video en modo servidor HTTP..."
echo "   El navegador puede acceder a: http://localhost:${HTTP_PORT}/stream"
echo "   Presiona Ctrl+C para detener"
echo ""
echo "=============================================="
echo ""

# Usar modo listening de FFmpeg (actúa como servidor HTTP)
ffmpeg -rtsp_transport tcp \
    -i "${RTSP_URL}" \
    -f mjpeg \
    -q:v 5 \
    -r 15 \
    -listen 1 \
    "http://127.0.0.1:${HTTP_PORT}/stream" \
    2>&1 | grep -v "frame=" || true

echo ""
echo "⏹️  Proxy detenido"
