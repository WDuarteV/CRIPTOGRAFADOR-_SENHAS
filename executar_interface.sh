#!/usr/bin/env bash
# ==========================================================
# SCRIPT DE INICIALIZAÇÃO DA INTERFACE VISUAL - SO2
# ==========================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo "   INICIANDO PAINEL VISUAL DE CRIPTOGRAFIA & TELEMETRIA   "
echo "=========================================================="

# 1. Compilar binários C++ se necessário
echo "[*] Verificando compilação dos motores C++..."
make -C sequencial >/dev/null 2>&1
make -C threads >/dev/null 2>&1
make -C processos >/dev/null 2>&1

PORT=5000

# 2. Iniciar servidor em background se não estiver rodando
if ! ss -tuln | grep -q ":$PORT "; then
    echo "[*] Iniciando servidor web de telemetria na porta $PORT..."
    python3 interface/server.py $PORT &
    SERVER_PID=$!
    sleep 1
else
    echo "[*] Servidor web já se encontra ativo na porta $PORT."
fi

URL="http://localhost:$PORT"
echo ""
echo "=========================================================="
echo "  🚀 INTERFACE VISUAL DISPONÍVEL EM:"
echo "     $URL"
echo "=========================================================="
echo ""

# 3. Tentar abrir o navegador padrão (Chrome ou xdg-open)
if command -v google-chrome-stable >/dev/null 2>&1; then
    google-chrome-stable --app="$URL" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
fi

echo "[*] Pressione Ctrl+C para encerrar o painel visual quando desejar."

# Manter aguardando se foi iniciado por este processo
if [ -n "$SERVER_PID" ]; then
    wait $SERVER_PID
fi
