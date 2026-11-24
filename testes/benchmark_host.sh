#!/usr/bin/env bash
# ==============================================================================
# Automacao de Baterias de Benchmark no Host Fisico (5 Execucoes por Cenario)
# Disciplina: Sistemas Operacionais 2 - FAETERJ Petropolis
# Gera: /testes/resultados/tempos_host.csv
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_CSV="$ROOT_DIR/testes/resultados/tempos_host.csv"
REPS="${REPS:-5}"
TAMANHO="${1:-10000000}"
CHAVE="${2:-84729}"
SENHA="${3:-AvaliacaoSO2}"

mkdir -p "$ROOT_DIR/testes/resultados"

echo "=================================================================="
echo "  BENCHMARK HOST FISICO - CRIPTOGRAFADOR DINAMICO SO2"
echo "  Parametros: N=$TAMANHO | Chave=$CHAVE | Senha=$SENHA | Reps=$REPS"
echo "=================================================================="

# Garantir compilacao otimizada (-O3) dos 3 modulos
make -C "$ROOT_DIR/sequencial" >/dev/null
make -C "$ROOT_DIR/processos" >/dev/null
make -C "$ROOT_DIR/threads" >/dev/null

# Cabecalho estrito conforme Spec.md (Secao 3.3)
echo "ambiente,implementacao,workers,cpus_limit,execucao,tempo_geracao_s,tempo_total_s,checksum,senha_cifrada" > "$OUT_CSV"

executar_cenario() {
    local impl="$1"
    local workers="$2"
    local bin="$ROOT_DIR/$impl/app"

    echo "[*] Executando Host -> $impl ($workers workers) [$REPS repeticoes]..."
    for ((r = 1; r <= REPS; r++)); do
        local out
        out=$("$bin" "$workers" "$TAMANHO" "$CHAVE" "$SENHA")
        local t_ger t_tot chk cifrada
        t_ger=$(echo "$out" | grep "^TEMPO_GERACAO=" | cut -d'=' -f2)
        t_tot=$(echo "$out" | grep "^TEMPO_TOTAL=" | cut -d'=' -f2)
        chk=$(echo "$out" | grep "^CHECKSUM=" | cut -d'=' -f2)
        cifrada=$(echo "$out" | grep "^SENHA_CIFRADA=" | cut -d'=' -f2)

        echo "host,$impl,$workers,ilimitado,$r,$t_ger,$t_tot,$chk,$cifrada" >> "$OUT_CSV"
        printf "    Run %d/%d: Tempo Geracao = %s s | Tempo Total = %s s | Checksum = %s\n" "$r" "$REPS" "$t_ger" "$t_tot" "$chk"
    done
}

# 1. Baseline Sequencial (1 processo)
executar_cenario "sequencial" 1

# 2. Versao Paralela com Processos (1, 2, 4 e 8 processos)
for w in 1 2 4 8; do
    executar_cenario "processos" "$w"
done

# 3. Versao Paralela com Threads (1, 2, 4 e 8 threads)
for w in 1 2 4 8; do
    executar_cenario "threads" "$w"
done

echo "------------------------------------------------------------------"
echo "[OK] Resultados consolidados salvos em: $OUT_CSV"
echo "=================================================================="

