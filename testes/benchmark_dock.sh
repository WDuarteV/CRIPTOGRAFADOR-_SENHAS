#!/usr/bin/env bash
# ==============================================================================
# Automacao de Baterias de Benchmark com Limitacao de CPU (--cpus="1", "2", "4")
# Disciplina: Sistemas Operacionais 2 - FAETERJ Petropolis
# Gera: /testes/resultados/tempos_docker.csv
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_CSV="$ROOT_DIR/testes/resultados/tempos_docker.csv"
RUNNER="$ROOT_DIR/container/run_docker.sh"
REPS="${REPS:-5}"
TAMANHO="${1:-10000000}"
CHAVE="${2:-84729}"
SENHA="${3:-AvaliacaoSO2}"

mkdir -p "$ROOT_DIR/testes/resultados"
chmod +x "$RUNNER"

echo "=================================================================="
echo "  BENCHMARK CONTAINER / CGROUPS (--cpus 1, 2, 4) - SO2"
echo "  Parametros: N=$TAMANHO | Chave=$CHAVE | Senha=$SENHA | Reps=$REPS"
echo "=================================================================="

# Cabecalho estrito conforme Spec.md (Secao 3.3)
echo "ambiente,implementacao,workers,cpus_limit,execucao,tempo_geracao_s,tempo_total_s,checksum,senha_cifrada" > "$OUT_CSV"

executar_cenario_docker() {
    local cpus="$1"
    local impl="$2"
    local workers="$3"

    echo "[*] Executando Container (--cpus=$cpus) -> $impl ($workers workers) [$REPS repeticoes]..."
    for ((r = 1; r <= REPS; r++)); do
        local out
        out=$("$RUNNER" "$cpus" "$impl" "$workers" "$TAMANHO" "$CHAVE" "$SENHA")
        local t_ger t_tot chk cifrada
        t_ger=$(echo "$out" | grep "^TEMPO_GERACAO=" | cut -d'=' -f2)
        t_tot=$(echo "$out" | grep "^TEMPO_TOTAL=" | cut -d'=' -f2)
        chk=$(echo "$out" | grep "^CHECKSUM=" | cut -d'=' -f2)
        cifrada=$(echo "$out" | grep "^SENHA_CIFRADA=" | cut -d'=' -f2)

        echo "docker,$impl,$workers,$cpus,$r,$t_ger,$t_tot,$chk,$cifrada" >> "$OUT_CSV"
        printf "    [--cpus=%s] Run %d/%d: Tempo Geracao = %s s | Tempo Total = %s s\n" "$cpus" "$r" "$REPS" "$t_ger" "$t_tot"
    done
}

# Bateria experimental para --cpus="1", "2" e "4" com 2, 4 e 8 workers
for cpus in 1 2 4; do
    for impl in processos threads; do
        for w in 2 4 8; do
            executar_cenario_docker "$cpus" "$impl" "$w"
        done
    done
done

echo "------------------------------------------------------------------"
echo "[OK] Resultados containerizados salvos em: $OUT_CSV"
echo "=================================================================="

