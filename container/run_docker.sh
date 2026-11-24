#!/usr/bin/env bash
# ==============================================================================
# Script Auxiliar de Build e Execucao Containerizada com Limitacao de CPU (--cpus)
# Disciplina: Sistemas Operacionais 2 - FAETERJ Petropolis
# Uso: ./container/run_docker.sh <cpus> <paradigma> <workers> [tamanho] [chave] [senha]
# Exemplo: ./container/run_docker.sh 1 threads 8 10000000 84729 AvaliacaoSO2
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="projeto-so2"

exibir_ajuda() {
    echo "Uso: $0 <cpus> <paradigma> <workers> [tamanho] [chave] [senha]"
    echo ""
    echo "Parametros:"
    echo "  <cpus>       : Limite de nucleos de CPU via cgroups (ex: 1, 2, 4)"
    echo "  <paradigma>  : Modulo a executar (sequencial | processos | threads)"
    echo "  <workers>    : Quantidade de fluxos de trabalho (ex: 1, 2, 4, 8)"
    echo "  [tamanho]    : Tamanho do dicionario dinamico (padrao: 10000000)"
    echo "  [chave]      : Chave secreta numerica (padrao: 84729)"
    echo "  [senha]      : Senha a ser criptografada (padrao: AvaliacaoSO2)"
    echo ""
    echo "Exemplos oficiais do edital:"
    echo "  $0 1 processos 4"
    echo "  $0 2 threads 4"
    echo "  $0 4 threads 8"
}

if [[ "$1" == "-h" || "$1" == "--help" || $# -lt 3 ]]; then
    exibir_ajuda
    exit 0
fi

CPUS="$1"
PARADIGMA="$2"
WORKERS="$3"
TAMANHO="${4:-10000000}"
CHAVE="${5:-84729}"
SENHA="${6:-AvaliacaoSO2}"
PALAVRA_CHAVE="${7:-}"

if [[ "$PARADIGMA" != "sequencial" && "$PARADIGMA" != "processos" && "$PARADIGMA" != "threads" ]]; then
    echo "Erro: <paradigma> invalido ($PARADIGMA). Use: sequencial, processos ou threads." >&2
    exit 1
fi

EXTRA_ARGS=()
if [[ -n "$PALAVRA_CHAVE" ]]; then
    EXTRA_ARGS+=("$PALAVRA_CHAVE")
fi

# Verifica se o daemon do Docker esta acessivel
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
        echo "[*] Construindo imagem Docker '$IMAGE_NAME' (ubuntu:24.04)..." >&2
        docker build -t "$IMAGE_NAME" -f "$ROOT_DIR/container/Dockerfile" "$ROOT_DIR" >&2
    fi
    docker run --rm --cpus="$CPUS" "$IMAGE_NAME" "./$PARADIGMA/app" "$WORKERS" "$TAMANHO" "$CHAVE" "$SENHA" "${EXTRA_ARGS[@]}"
else
    # Fallback nativo Linux cgroups v2 (systemd-run CPUQuota + taskset)
    # Utiliza exatamente o mesmo subsistema cpu.max / CFS Quota do Kernel Linux usado pelo Docker --cpus
    BIN="$ROOT_DIR/$PARADIGMA/app"
    if [[ ! -x "$BIN" ]]; then
        make -C "$ROOT_DIR/$PARADIGMA" >/dev/null 2>&1
    fi

    QUOTA=$((CPUS * 100))
    MAX_CORE=$((CPUS - 1))
    if command -v systemd-run >/dev/null 2>&1 && command -v taskset >/dev/null 2>&1; then
        systemd-run --user --scope --quiet -p "CPUQuota=${QUOTA}%" \
            taskset -c "0-${MAX_CORE}" "$BIN" "$WORKERS" "$TAMANHO" "$CHAVE" "$SENHA" "${EXTRA_ARGS[@]}"
    elif command -v taskset >/dev/null 2>&1; then
        taskset -c "0-${MAX_CORE}" "$BIN" "$WORKERS" "$TAMANHO" "$CHAVE" "$SENHA" "${EXTRA_ARGS[@]}"
    else
        "$BIN" "$WORKERS" "$TAMANHO" "$CHAVE" "$SENHA" "${EXTRA_ARGS[@]}"
    fi
fi

