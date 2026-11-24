# task.md: Lista Formal de Tarefas Rastreáveis do Projeto

## Tarefa 1: Estruturação Canônica de Diretórios e Baseline Sequencial (`/sequencial`)
- [x] **1.1.** Criar a árvore de diretórios completa exigida pelo edital: `/sequencial`, `/processos`, `/threads`, `/container`, `/testes`, `/testes/entradas`, `/testes/resultados` e `/documentacao`.
- [x] **1.2.** Implementar `/sequencial/main.cpp` contendo:
  - Parser dinâmico de argumentos CLI (`./app <workers> [tamanho] [chave] [senha]`) sem valores fixos travados no código.
  - Estrutura contígua `struct EntradaDic { char valor[32]; }` alocada em memória.
  - Algoritmo de geração do dicionário com 50 iterações matemáticas modulares e reversão de string por posição, acumulando o `checksum_global` de integridade.
  - Rotina de cifragem determinística da senha baseada no dicionário gerado.
  - Cronometragem padronizada via `std::chrono` separando Tempo de Geração e Tempo Total.
- [x] **1.3.** Criar `/sequencial/Makefile` com regra de compilação utilizando `g++ -O3 -std=c++17 -Wall -Wextra` gerando o binário `app` e alvo `clean`.
- [x] **1.4.** Compilar e executar `/sequencial/app` validando que o tempo de execução sob `-O3` para `N = 10000000` é estritamente $\ge 2.0\text{s}$.
- [x] **1.5.** Redigir `/sequencial/README.md` contendo as 3 seções obrigatórias: Instalação de Dependências, Compilação do Programa e Instruções de Execução com exemplos reais.

## Tarefa 2: Implementação Concorrente com Processos (`/processos`)
- [x] **2.1.** Implementar `/processos/main.cpp` com alocação contígua do dicionário e da estrutura de sincronização via `mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0)`.
- [x] **2.2.** Configurar `pthread_mutex_t` com atributo `PTHREAD_PROCESS_SHARED` (ou acumulador atômico compartilhado) para proteger a atualização da métrica de integridade na região crítica.
- [x] **2.3.** Implementar instanciação de $P$ processos filhos via `fork()`, divisão de carga por *chunking* ($start$ e $end$), barreira no processo pai com `waitpid()` e desalocação com `munmap()`.
- [x] **2.4.** Criar `/processos/Makefile` (com flags `-O3 -pthread`) e `/processos/README.md` seguindo o padrão obrigatório do edital.
- [x] **2.5.** Verificar equivalência estrita de saída entre `/sequencial/app` e `/processos/app 4` via `diff` (diferença zero nas saídas de cifragem e checksum).

## Tarefa 3: Implementação Paralela com Multithreading (`/threads`)
- [x] **3.1.** Implementar `/threads/main.cpp` instanciando $P$ fluxos via `std::thread` operando sobre o vetor contíguo `EntradaDic` no mesmo espaço de endereçamento.
- [x] **3.2.** Implementar a região crítica utilizando `std::mutex` (`std::lock_guard<std::mutex>`) para atualização segura do checksum global de validação e sincronização final com `.join()`.
- [x] **3.3.** Criar `/threads/Makefile` (com flags `-O3 -pthread`) e `/threads/README.md` seguindo o padrão obrigatório do edital.
- [x] **3.4.** Verificar equivalência estrita de saída entre `/sequencial/app`, `/processos/app 4` e `/threads/app 4` via `diff`.

## Tarefa 4: Ambiente Containerizado e Limitação via Cgroups (`/container`)
- [x] **4.1.** Criar `/container/Dockerfile` baseado em `ubuntu:24.04` com instalação de `build-essential`, `g++`, `make`, `python3` e `python3-matplotlib`.
- [x] **4.2.** Criar script `/container/run_docker.sh` para build da imagem `projeto-so2` e execução parametrizada aplicando `--cpus="1"`, `--cpus="2"` e `--cpus="4"`.
- [x] **4.3.** Redigir `/container/README.md` documentando os comandos de build, execução isolada e explicação do controle via `cgroups` (CFS).

## Tarefa 5: Automação de Benchmarks e Geração dos 3 Gráficos (`/testes`)
- [x] **5.1.** Criar arquivos de parâmetros de teste em `/testes/entradas/`.
- [x] **5.2.** Desenvolver `/testes/benchmark_host.sh` (5 execuções para Sequencial e para Processos/Threads com 2, 4 e 8 workers) salvando em `/testes/resultados/tempos_host.csv`.
- [x] **5.3.** Desenvolver `/testes/benchmark_dock.sh` (5 execuções para Processos/Threads com 2, 4 e 8 workers sob `--cpus="1"`, `"2"` e `"4"`) salvando em `/testes/resultados/tempos_docker.csv`.
- [x] **5.4.** Implementar `/testes/plot_graficos.py` para processar os CSVs e gerar em `/testes/resultados/` o Gráfico 1 (Tempo de Execução), Gráfico 2 (Speedup vs. Linear/Amdahl) e Gráfico 3 (Host vs. Docker).

## Tarefa 6: Documentação Final e Checklist de Entrega (`/documentacao`)
- [x] **6.1.** Elaborar a estrutura de slides e conteúdo técnico para `/documentacao/apresentacao.pdf` cobrindo os 10 tópicos obrigatórios do roteiro de defesa.
- [x] **6.2.** Executar o checklist final de validação pré-entrega garantindo conformidade integral do pacote ZIP.