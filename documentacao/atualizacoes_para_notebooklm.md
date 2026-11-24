# ATUALIZAÇÃO OFICIAL DO PROJETO SO2 — SUBSTITUI OS DADOS ANTERIORES

**Projeto:** Criptografador de Senhas Baseado em Dicionário Dinâmico (C++17, Linux)
**Disciplina:** Sistemas Operacionais II — FAETERJ Petrópolis | **Aluno:** Wallace Duarte Venâncio
**Data da atualização:** 12/11/2026

> **INSTRUÇÃO PARA O NOTEBOOKLM:** Este documento CORRIGE e SUBSTITUI todos os números, hipóteses e conclusões de desempenho das fontes anteriores (PDFs e slides antigos). Em caso de conflito, **este documento prevalece**. Ao regenerar a apresentação, use apenas os valores desta atualização. Mantenha os mesmos 10 tópicos/slides da estrutura anterior.

---

## 1. O que mudou e por quê

1. Na primeira bateria, **1 processo levou 6,78 s** e **1 thread 3,94 s**, mesmo com código de cálculo idêntico.
2. A hipótese antiga (Transparent Huge Pages de 2 MB nas threads × páginas de 4 KB do `mmap(MAP_SHARED)` nos processos) foi **testada e REFUTADA por medição**:
   - Falhas de página (minor page faults): processos ≈ **78.000**, threads ≈ **600** (a diferença existe).
   - Porém o **tempo de sistema (kernel) foi de só 0,17 s**; o tempo extra estava no **tempo de usuário** (6,7 s contra 3,65 s), ou seja, no código do programa, não no kernel.
   - Trocando `MAP_SHARED` por `MAP_PRIVATE`, o tempo continuou em ~6,3 s. Logo, o `mmap(MAP_SHARED)` **não** era a causa.
3. **Causa real:** o laço de cálculo estava dentro de `main()` em `processos/main.cpp`, e o `g++ -O3` gerou código de máquina mais lento (inlining). Movendo o laço para uma função própria `noinline` (igual à das threads), 1 processo caiu de 6,78 s para ~3,75 s e 8 processos para ~1,21 s.
4. Após a correção, **as 135 execuções foram refeitas** (5 repetições por cenário, N = 10.000.000). O checksum permaneceu `5000000903112875` em todas, e a equivalência com `diff` continua válida (0 diferenças).
5. Os dados do Docker desta bateria foram coletados com **`docker run --cpus` real (Docker Desktop, que roda em uma VM Linux)**, e não com o plano B de cgroups nativo.

**Afirmações antigas que devem ser REMOVIDAS dos slides:**
- "Threads venceram Processos por causa de Transparent Huge Pages (2 MB) contra ~80.000 page faults de 4 KB."
- "Speedup de 3,23x (Threads) e 2,75x (Processos)."
- "1 processo = 6,78 s", "8 threads com `--cpus=1` = 3,94 s (0,99x)", "8 processos com `--cpus=1` = 6,82 s (0,57x)".
- Sequencial = 3,9228 s ± 0,0838 s.

---

## 2. Números NOVOS (substituem os anteriores)

**Hardware:** Intel Core i5-1235U (12ª geração): 2 P-cores com Hyper-Threading (4 threads, até 4,4 GHz) + 8 E-cores (até 3,3 GHz) = 12 threads lógicas; 16 GB de RAM. Compilação: `g++ -O3 -std=c++17 -Wall -Wextra -pthread`. Dicionário: N = 10.000.000 (320 MB), chave 84729, senha `AvaliacaoSO2`.

### 2.1 Host físico (médias de 5 execuções)

| Implementação | Workers | Tempo médio ± desvio (s) | Speedup | Eficiência |
|---|---|---|---|---|
| Sequencial | 1 | 3,8621 ± 0,2309 | 1,00x | 100% |
| Threads | 1 | 3,7146 ± 0,2204 | 1,04x | 104% |
| Threads | 2 | 2,3956 ± 0,0500 | 1,61x | 80,6% |
| Threads | 4 | 1,7667 ± 0,0637 | 2,19x | 54,6% |
| **Threads** | **8** | **1,1220 ± 0,0107** | **3,44x** | **43,0%** |
| Processos | 1 | 4,3374 ± 0,2240 | 0,89x | 89,0% |
| Processos | 2 | 2,5069 ± 0,2722 | 1,54x | 77,0% |
| Processos | 4 | 1,8110 ± 0,0944 | 2,13x | 53,3% |
| **Processos** | **8** | **1,1649 ± 0,0141** | **3,32x** | **41,4%** |

**Conclusão do host:** Threads (3,44x) e Processos (3,32x) ficaram **praticamente empatados**. Threads têm leve vantagem por criação mais barata e por não precisarem de `mmap`/IPC.

### 2.2 Docker com limite de CPU (`--cpus`), médias de 5 execuções

| `--cpus` | Implementação | 2 workers | 4 workers | 8 workers |
|---|---|---|---|---|
| 1 | Threads | 5,339 s (0,72x) | 7,327 s (0,53x) | 9,656 s (0,40x) |
| 1 | Processos | 5,433 s (0,71x) | 7,658 s (0,50x) | 10,194 s (0,38x) |
| 2 | Threads | 2,261 s (1,71x) | 3,729 s (1,04x) | 4,495 s (0,86x) |
| 2 | Processos | 2,322 s (1,66x) | 3,629 s (1,06x) | 4,705 s (0,82x) |
| 4 | Threads | 2,270 s (1,70x) | 1,740 s (2,22x) | 2,137 s (1,81x) |
| 4 | Processos | 2,316 s (1,67x) | 1,832 s (2,11x) | 2,288 s (1,69x) |

(Speedup calculado em relação ao sequencial do host, 3,8621 s.)

**Conclusões do Docker:**
- Com `--cpus=1` não há paralelismo físico, só revezamento (concorrência por time-sharing). **Quanto mais workers, pior** (8 threads = 9,66 s, 0,40x). Isso confirma o efeito de **sobreassinatura** (mais fluxos do que CPUs disponíveis): trocas de contexto, perda de cache e fatiamento da cota do CFS.
- Quando workers ≤ `--cpus`, há ganho (ex.: 2 workers com `--cpus=2` = 1,71x; 4 workers com `--cpus=4` = 2,22x). Quando workers > `--cpus`, o desempenho piora.
- Com `--cpus=1`, até 2 workers (5,3 s) ficou acima do sequencial (3,86 s). Duas **hipóteses, não medidas**: sobrecarga de limitar CPU dentro da VM do Docker Desktop e núcleos virtuais caindo em E-cores. Medição de apoio: 1 thread fixada em um P-core = 4,09 s; em um E-core = 5,72 s.
- Há variação alta em alguns casos (ex.: 4 threads com `--cpus=2`: desvio 0,36 s), compatível com máquina de uso geral e núcleos heterogêneos.

### 2.3 Lei de Amdahl (estimativa)
Com S = 3,44 e P = 8, a fração paralelizável efetiva é `f = (1 − 1/S) / (1 − 1/P) ≈ 0,81` (~81%). Deve ser apresentada como **estimativa**, não medição direta.

### 2.4 Por que o speedup não chega a 8 (explicação atualizada)
1. **Lei de Amdahl:** parte não paralelizável (alocação, criação dos workers, barreira, cifragem final).
2. **Núcleos não idênticos:** 2 P-cores com Hyper-Threading + 8 E-cores mais lentos (medido: 4,09 s em P-core × 5,72 s em E-core para 1 thread).
3. **Memória/cache compartilhados** (320 MB escritos ao mesmo tempo): hipótese coerente, **não medida diretamente** (confirmaria com `perf stat`).

### 2.5 Tempo de geração × tempo total
Geração = preenchimento paralelo do dicionário. Total = geração + alocação + cifragem + descriptografia. A diferença nos CSVs é de décimos de milésimo a poucos milésimos de segundo, pois cifrar uma senha curta é desprezível.

---

## 3. Alterações slide a slide (estrutura de 10 slides mantida)

| Slide | O que atualizar |
|---|---|
| 1 Capa | Sem mudança. |
| 2 Problema / sequencial | Trocar **T_seq = 3,9228 s ± 0,0838 s** por **3,8621 s ± 0,2309 s** (≥ 2 s continua atendido). |
| 3 Estratégia (Chunking) | Sem mudança (blocos contíguos, sem corrida, sem false sharing). |
| 4 Processos | Trocar o destaque de desempenho por **8 processos = 1,1649 s (3,32x)**. Manter `fork`, `mmap(MAP_SHARED \| MAP_ANONYMOUS)` por causa do Copy-on-Write, `_exit(0)`, `waitpid`. Incluir: **~78.000 minor page faults medidos, mas só 0,17 s de tempo de sistema**. |
| 5 Threads | **Remover** o argumento de THP de 2 MB como vantagem. Dizer: heap privado ≈ 600 page faults; melhor desempenho: **8 threads = 1,1220 s (3,44x)**. |
| 6 Região crítica | Sem mudança (mutex uma vez por worker; map-reduce local). |
| 7 Metodologia | Acrescentar: o código de cálculo dos processos foi isolado em função `noinline` após investigação; 135 execuções refeitas; Docker coletado com `docker run --cpus` real (Docker Desktop). |
| 8 Resultados | Usar as tabelas da seção 2 (host e Docker). Lembrar: 135 execuções = 45 host + 90 Docker. |
| 9 Gráficos 1, 2 e 3 | Gráfico 1: 1,12 s (threads) e 1,16 s (processos) com 8 workers. Gráfico 2: S = 3,44x e 3,32x; afastamento da reta ideal por Amdahl + núcleos heterogêneos + memória (hipótese). Gráfico 3: com `--cpus=1`, mais workers = pior (até 0,40x). |
| 10 Conclusão | Threads e processos praticamente empatados (3,44x × 3,32x). Threads: mais simples e leves. Processos: isolamento de memória ao custo de IPC. **Destacar a investigação:** hipótese THP refutada por medição, causa real corrigida (código gerado pelo compilador). |

---

## 4. Novo conteúdo sugerido: slide extra (opcional) "Investigação e Correção"

**Título:** Do 6,78 s ao 3,75 s: medir antes de concluir

- Sintoma: 1 processo 6,78 s × 1 thread 3,94 s (mesmo código de cálculo).
- Hipótese inicial: THP (2 MB) × páginas de 4 KB do `mmap(MAP_SHARED)`.
- Medição: 78.000 × 600 page faults, mas só **0,17 s** de tempo de sistema; troca para `MAP_PRIVATE` não mudou (≈ 6,3 s).
- Causa: laço dentro de `main()` → código mais lento sob `-O3`.
- Correção: função `noinline`. Resultado: 1 processo ≈ 3,75 s; 8 processos 1,16 s (3,32x).
- Lição: separar custo de kernel (tempo de sistema) de custo de código (tempo de usuário).

**Roteiro de fala (≈ 1 min):** "Na primeira bateria, o processo com 1 worker foi muito mais lento que a thread, apesar do mesmo cálculo. Minha hipótese era a memória compartilhada de 4 KB contra páginas de 2 MB. Medi as falhas de página e o tempo de sistema: as falhas existiam, mas custavam apenas 0,17 s. Troquei o tipo de mapeamento e nada mudou. O problema estava no código gerado pelo compilador para o laço dentro do main. Isolei o laço numa função, refiz as 135 execuções e agora processos e threads estão praticamente empatados."

---

## 5. Resposta-relâmpago atualizada (30 s)

"Gerei um dicionário de 320 MB com 500 milhões de contas modulares. O sequencial leva 3,9 s. Dividi o trabalho em blocos contíguos, sem sobreposição, então não há corrida na escrita nem false sharing. Em processos usei `mmap(MAP_SHARED)` para escapar do Copy-on-Write; em threads a memória já é compartilhada. O checksum é a região crítica, protegida por mutex e acessada uma vez por worker. Com 8 workers, threads chegaram a 3,44x e processos a 3,32x, limitados por Amdahl, memória e núcleos não idênticos. No Docker com 1 CPU não há ganho: quanto mais workers, pior, por revezamento. Investiguei uma diferença inicial entre processos e threads, descartei a hipótese da memória por medição e corrigi a causa real: o código gerado pelo compilador."

---

## 6. Fatos que NÃO mudaram (podem ser mantidos)
- Estrutura: `/sequencial`, `/processos`, `/threads`, `/container`, `/testes`, `/documentacao` (+ `/interface` opcional).
- CLI: `./app <workers> [tamanho] [chave] [senha]` (sem valores fixos).
- Dicionário: `struct EntradaDic { char valor[32]; }`, 10.000.000 × 32 B = 320 MB; recorrência `valor = (valor * 31 + 17) % 1000000007` com 50 iterações; sem `malloc` dentro do laço.
- Checksum de integridade: `5000000903112875` (idêntico em sequencial, processos e threads); validação por `diff` com 0 diferenças.
- Região crítica: `std::mutex` + `std::lock_guard` (threads) e `pthread_mutex_t` com `PTHREAD_PROCESS_SHARED` (processos), acessados 1 vez por worker.
- Docker: `ubuntu:24.04`, `docker run --rm --cpus="1|2|4"`; scripts `container/run_docker.sh`, `testes/benchmark_host.sh`, `testes/benchmark_dock.sh`, `testes/plot_graficos.py`.
- Interface web local (Zero-Interference, cronômetro dentro do binário C++, API HTTP em `localhost:5000`) é camada opcional e não participa das medições oficiais.

---

## 7. Prompt para colar no NotebookLM junto com este arquivo

```text
Use o arquivo "atualizacoes_para_notebooklm.md" como fonte prioritária: ele corrige os dados de desempenho das fontes anteriores. Refaça a apresentação de 10 slides do projeto SO2 mantendo a estrutura anterior, mas aplicando: (1) apenas os números novos das tabelas da seção 2; (2) remova a explicação de Transparent Huge Pages/80.000 page faults como causa da diferença entre processos e threads; (3) siga as alterações slide a slide da seção 3; (4) inclua o slide extra "Do 6,78 s ao 3,75 s: medir antes de concluir" da seção 4; (5) use bullets curtos e roteiro de fala de ~1 minuto por slide.
```

