# Módulo de Testes, Benchmarks Automatizados e Plotagem (`/testes`)

Este diretório concentra os scripts de automação científica de testes no Host físico e no ambiente isolado por `cgroups`/Docker, os conjuntos de dados de entrada (`/entradas`) e os artefatos estatísticos e visuais gerados (`/resultados`), cumprindo integralmente as diretrizes avaliativas de Sistemas Operacionais 2 (FAETERJ Petrópolis).

---

## 1. Instalação de Dependências

Os scripts de automação utilizam `bash` (GNU Coreutils), `g++`, `make` e `python3` para agregação estatística (cálculo de média $\mu$, desvio padrão $\sigma$, Speedup $S_p$ e Eficiência $E_p$) e geração dos 3 gráficos em alta resolução (`.png` e `.svg`).

### No Debian / Ubuntu (e derivados):
```bash
sudo apt update
sudo apt install -y build-essential g++ make python3 python3-matplotlib
```

### No Arch Linux / Manjaro:
```bash
sudo pacman -S --needed base-devel gcc make python python-matplotlib
```

### No Fedora / RHEL:
```bash
sudo dnf install -y gcc-c++ make python3 python3-matplotlib
```

---

## 2. Compilação do Programa

Os scripts `benchmark_host.sh` e `benchmark_dock.sh` verificam e acionam automaticamente a compilação otimizada (`-O3`) dos três módulos (`/sequencial`, `/processos`, `/threads`) antes de iniciar a coleta cronométrica. Caso deseje compilar manualmente a partir da raiz do projeto:

```bash
make -C sequencial clean all
make -C processos clean all
make -C threads clean all
```

---

## 3. Instruções de Execução

### 3.1. Executar a Bateria Completa no Host Físico (5 execuções por configuração):
```bash
chmod +x testes/benchmark_host.sh
./testes/benchmark_host.sh 10000000 84729 AvaliacaoSO2
```
- **Saída gerada:** `/testes/resultados/tempos_host.csv`

### 3.2. Executar a Bateria Containerizada / Cgroups (`--cpus="1"`, `"2"`, `"4"`):
```bash
chmod +x testes/benchmark_dock.sh
./testes/benchmark_dock.sh 10000000 84729 AvaliacaoSO2
```
- **Saída gerada:** `/testes/resultados/tempos_docker.csv`

### 3.3. Gerar o Resumo Estatístico e os 3 Gráficos Obrigatórios:
```bash
python3 testes/plot_graficos.py
```
- **Arquivos gerados em `/testes/resultados/`:**
  1. `resumo_estatistico.csv` e `resumo_estatistico.json` — Tabelas com média ($\mu$), desvio padrão ($\sigma$), Speedup ($S_p = T_{\text{seq}}/T_p$) e Eficiência ($E_p = S_p/P$).
  2. `grafico1_tempo.png` — **Gráfico 1: Tempo de Execução (s)** (Sequencial vs. Processos vs. Threads para 1, 2, 4 e 8 workers).
  3. `grafico2_speedup.png` — **Gráfico 2: Speedup Real ($S_p$) vs. Linear Ideal ($y = x$)** (Análise da Lei de Amdahl).
  4. `grafico3_docker.png` — **Gráfico 3: Host Físico vs. Container Docker (`--cpus="1"`, `"2"`, `"4"`)** (Impacto de contenção no escalonador CFS).

