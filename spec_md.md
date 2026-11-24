# Spec.md: Especificações Técnicas do Sistema

## 1. Requisitos Funcionais (RF)
- **RF01 - Interface de Linha de Comando (CLI) Dinâmica:** Todos os binários (`/sequencial/app`, `/processos/app`, `/threads/app`) devem receber argumentos via `argc` e `argv` obedecendo à assinatura: `./app <workers> [tamanho] [chave] [senha]`.
  - `workers` (Obrigatório nos modos paralelos; ignorado ou fixado em `1` no sequencial): Número de fluxos de execução ($P \in \{1, 2, 4, 8\}$).
  - `tamanho` (Opcional, Default: `10000000`): Total de posições $N$ do dicionário dinâmico.
  - `chave` (Opcional, Default: `84729`): Semente numérica inteira para o cálculo modular.
  - `senha` (Opcional, Default: `"AvaliacaoSO2"`): String alvo a ser cifrada.
- **RF02 - Geração Matemática do Dicionário:** Para cada índice $i \in [0, N)$, o sistema deve executar 50 iterações de transformações aritméticas modulares e bit-a-bit utilizando $i$ e `chave`, gravando o resultado formatado e invertido na posição `dicionario[i]`.
- **RF03 - Decomposição de Domínio (Chunking):** Nas versões `/processos` e `/threads`, o intervalo $[0, N)$ deve ser particionado em $P$ blocos contíguos disjuntos onde para cada trabalhador $p \in [0, P-1]$:
  - $start = p \times \lfloor N / P \rfloor$
  - $end = (p == P - 1) \ ? \ N : start + \lfloor N / P \rfloor$
- **RF04 - Região Crítica e Métrica de Integridade:** Cada trabalhador deve acumular um checksum local (soma de verificação das entradas geradas em seu subintervalo) e, ao concluir seu bloco, somá-lo a uma variável global compartilhada protegida por exclusão mútua (`pthread_mutex_t` em memória compartilhada para processos; `std::mutex` para threads).
- **RF05 - Cifragem Determinística da Senha:** Após a barreira de sincronização (`waitpid` ou `join`), o fluxo principal deve cifrar cada caractere da `senha` consultando posições determinísticas do dicionário pronto e combinando-as com o caractere original, gerando uma string hexadecimal/alfanumérica reproduzível.
- **RF06 - Saída Padronizada:** Os três executáveis devem imprimir no `stdout` exatamente o mesmo formato de saída de verificação (excluindo as linhas de telemetria de tempo ao comparar com `diff`, ou separando telemetria em `stderr`/formato parseável) para garantir validação direta e extração automatizada pelos scripts de benchmark.

## 2. Requisitos Não Funcionais (RNF)
- **RNF01 - Desempenho de Baseline:** A versão sequencial compilada com `g++ -O3` deve apresentar tempo de execução $T_{\text{seq}} \ge 2.0\text{s}$ (meta calibrada entre $2.5\text{s}$ e $4.0\text{s}$) para $N = 10.000.000$.
- **RNF02 - Alocação Contígua Livre de Lock Contention:** É proibido o uso de `std::vector<std::string>` ou alocações dinâmicas individuais por índice durante o laço paralelo, prevenindo contenção de lock na `glibc` (`malloc`).
- **RNF03 - Memória Compartilhada POSIX Real (Zero CoW no Dicionário):** Na versão `/processos`, o buffer do dicionário e a estrutura de sincronização devem ser alocados via `mmap()` com as flags `PROT_READ | PROT_WRITE` e `MAP_SHARED | MAP_ANONYMOUS` antes da chamada `fork()`, com liberação obrigatória via `munmap()` antes do `return 0`.
- **RNF04 - Padronização Cronométrica:** A medição via `std::chrono::high_resolution_clock` deve iniciar imediatamente antes da etapa de preparação/geração e registrar:
  1. `Tempo de Geração (s)`: Intervalo restrito à criação dos workers, cálculo do dicionário, atualização da região crítica e barreira (`waitpid`/`join`).
  2. `Tempo Total (s)`: Intervalo completo desde a alocação/mapeamento (`mmap`/`new`), passando pela geração, até a conclusão da cifragem da senha.
- **RNF05 - Isolamento de CPU via Cgroups:** O container Docker deve suportar limitação estrita de núcleos lógicos com `--cpus="1"`, `--cpus="2"` e `--cpus="4"` sobre a imagem `ubuntu:24.04`.

## 3. Modelos de Dados Essenciais

### 3.1. Estrutura da Entrada do Dicionário (Em Memória)
```cpp
#include <cstdint>

struct EntradaDic {
    char valor[32]; // Buffer estático contíguo (32 bytes por posição; ~320 MB para N=10.000.000)
};
```

### 3.2. Estrutura de Controle Compartilhado (Exclusiva para `/processos`)
```cpp
#include <pthread.h>
#include <cstdint>

struct ControleCompartilhado {
    pthread_mutex_t mutex;      // Inicializado com PTHREAD_PROCESS_SHARED
    uint64_t checksum_global;   // Métrica de integridade protegida por região crítica
};
```

### 3.3. Esquema dos Arquivos CSV de Resultados (`/testes/resultados/*.csv`)
```csv
ambiente,implementacao,workers,cpus_limit,execucao,tempo_geracao_s,tempo_total_s,checksum,senha_cifrada
host,sequencial,1,ilimitado,1,3.124501,3.210492,98472398472,A9F4...
host,processos,4,ilimitado,1,0.892341,0.981230,98472398472,A9F4...
docker,threads,8,1,1,3.651290,3.740112,98472398472,A9F4...
```

## 4. Integrações e Interfaces do Sistema
- **Interface C++ <-> Kernel Linux (Syscalls):** Integração direta com chamadas de sistema POSIX `mmap()`, `munmap()`, `fork()`, `waitpid()` e `clone()` (via `pthread`/`std::thread`).
- **Interface C++ <-> Scripts Bash (`benchmark_host.sh` e `benchmark_dock.sh`):** Os scripts invocam os binários passando parâmetros CLI, capturam a saída padrão, validam a integridade da cifragem e gravam os tempos nos arquivos CSV em `/testes/resultados/`.
- **Interface CSV <-> Motor de Plotagem (`plot_graficos.py`):** O script Python consome os arquivos CSV gerados, calcula média aritmética ($\mu$), desvio padrão ($\sigma$), Speedup ($S_p = T_{\text{seq}} / T_p$) e Eficiência ($E_p = S_p / p$), exportando os três gráficos em alta resolução (`grafico1_tempo.png`, `grafico2_speedup.png`, `grafico3_docker.png`).