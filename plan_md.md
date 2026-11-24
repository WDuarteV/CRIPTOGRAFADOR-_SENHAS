# Plan.md: Plano Arquitetural e Roteiro de Implementação

## 1. Arquitetura de Alto Nível
O sistema é estruturado de forma modular, onde cada paradigma de execução reside em seu próprio diretório isolado, mas compartilha a mesma lógica algorítmica de geração de dicionário e cifragem:

1. **Núcleo Algorítmico (Comum às 3 versões):**
   - **Fase A (Alocação):** Reserva de bloco contíguo para $N$ estruturas `EntradaDic` ($N = 10.000.000$ por padrão).
   - **Fase B (Geração e Decomposição de Domínio):** Divisão do espaço $[0, N)$ em $P$ subintervalos disjuntos $[start, end)$. Cada índice realiza 50 iterações de aritmética modular pseudoaleatória baseadas no índice e na `chave`, seguidas de formatação e reversão de string no buffer estático. Ao final do seu bloco, cada trabalhador entra em uma Região Crítica para somar seu checksum local ao acumulador global de integridade.
   - **Fase C (Barreira de Sincronização):** Aguardo do término de todos os fluxos de execução (`waitpid` para processos; `join` para threads).
   - **Fase D (Cifragem e Verificação):** Mapeamento dos caracteres da `senha` utilizando entradas determinísticas do dicionário gerado e emissão padronizada das métricas de tempo (`Tempo_Geracao`, `Tempo_Total`), `Checksum` e `Senha_Cifrada` via `stdout`.

2. **Camada de Infraestrutura e Automação:**
   - **Containerização (`/container`):** Imagem Docker baseada em `ubuntu:24.04` com toolchain C++ e Python, orquestrada por script que injeta limites no subsistema `cpu.cfs_quota_us` via `--cpus`.
   - **Pipeline de Benchmark (`/testes`):** Scripts Bash que executam cada configuração 5 vezes, extraem os tempos, registram em arquivos CSV em `/testes/resultados/` e acionam o motor gráfico em Python (`plot_graficos.py`) para renderizar os 3 gráficos exigidos.

## 2. Stack Tecnológica Recomendada
- **Linguagem Principal:** C++ (Padrão C++17), compilado via `g++` com flags `-O3 -Wall -Wextra` (e `-pthread` para threads/processos).
- **APIs de Sistema Operacional (POSIX/Linux):** `<unistd.h>`, `<sys/mman.h>`, `<sys/wait.h>`, `<pthread.h>` (para sincronização interprocessos via `pthread_mutexattr_setpshared` ou operações atômicas).
- **Concorrência C++ Standard:** `<thread>`, `<mutex>`, `<chrono>`, `<atomic>`.
- **Automação de Build e Testes:** GNU Make (`Makefile`) e Bash Scripting (`#!/usr/bin/env bash`).
- **Virtualização Leve:** Docker Engine com suporte a Linux Control Groups (cgroups v1/v2).
- **Análise de Dados e Plotagem:** Python 3 com `matplotlib`, `pandas` (ou `csv`/`statistics` nativos) e `numpy`.

## 3. Fases de Desenvolvimento (Milestones & Roadmap)

### Fase 1: Fundação, Estrutura Canônica e Baseline Sequencial
- Criação da árvore de diretórios oficial do projeto.
- Implementação de `/sequencial/main.cpp` com parser CLI dinâmico, estrutura `EntradaDic` contígua, algoritmo de 50 iterações calibrado para $T_{\text{seq}} \ge 2.0\text{s}$ sob `-O3`, cálculo de checksum e medição via `std::chrono`.
- Criação do `/sequencial/Makefile` e `/sequencial/README.md`.

### Fase 2: Concorrência com Processos e Memória Compartilhada (`/processos`)
- Implementação de `/processos/main.cpp` utilizando `mmap` (`MAP_SHARED | MAP_ANONYMOUS`) para o vetor de dicionário e para a estrutura de controle/região crítica (mutex compartilhado ou variável atômica).
- Implementação da criação de processos com `fork()`, divisão de carga (*chunking*), barreira com `waitpid()` e liberação com `munmap()`.
- Validação de equivalência estrita (`diff`) contra a versão sequencial e elaboração do `Makefile` e `README.md`.

### Fase 3: Paralelismo com Multithreading (`/threads`)
- Implementação de `/threads/main.cpp` com `std::thread`, compartilhamento direto do espaço de endereçamento, controle de região crítica via `std::mutex` para atualização da métrica de integridade e sincronização via `.join()`.
- Validação de equivalência estrita (`diff`) e elaboração do `Makefile` e `README.md`.

### Fase 4: Containerização e Controle de Recursos (`/container`)
- Construção do `Dockerfile` (`ubuntu:24.04`, `build-essential`, `g++`, `make`, `python3-matplotlib`).
- Desenvolvimento do script `run_docker.sh` para compilação da imagem e execução parametrizada com `--cpus="1"`, `"2"` e `"4"`.
- Documentação em `/container/README.md`.

### Fase 5: Automação de Benchmarks e Geração de Gráficos (`/testes`)
- Criação dos arquivos de parâmetros em `/testes/entradas/`.
- Implementação de `benchmark_host.sh` e `benchmark_dock.sh` executando 5 baterias por cenário (1, 2, 4 e 8 workers) e consolidando médias e desvios padrões em CSVs dentro de `/testes/resultados/`.
- Desenvolvimento de `plot_graficos.py` para gerar o **Gráfico 1** (Tempo de Execução), **Gráfico 2** (Speedup Real vs. Linear / Lei de Amdahl) e **Gráfico 3** (Host vs. Docker sob limitação de CPUs).

### Fase 6: Documentação de Apresentação e Homologação Final (`/documentacao`)
- Consolidação dos resultados experimentais e estruturação do material de defesa cobrindo os 10 tópicos obrigatórios (`/documentacao/apresentacao.pdf`).
- Execução do checklist final de validação pré-entrega.