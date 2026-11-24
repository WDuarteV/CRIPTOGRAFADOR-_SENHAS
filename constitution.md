# Constitution: Criptografador de Senhas Baseado em Dicionário Dinâmico (SO2)

## 1. Visão do Projeto
Desenvolver, avaliar e documentar um sistema de criptografia simétrica baseado na geração matemática intensiva de um dicionário dinâmico em memória em C++. O projeto tem como finalidade demonstrar, comparar e analisar rigorosamente os paradigmas de execução Sequencial, Concorrente via Processos (POSIX IPC) e Paralela via Multithreading (C++11/POSIX) sob diferentes restrições de hardware e isolamento via containers Linux (Docker/cgroups).

## 2. Princípios Fundamentais de Engenharia
- **Equivalência Estrita de Dados e Alocação:** As três implementações devem operar sobre a mesma estrutura contígua de memória (`struct EntradaDic` com buffer estático `char[32]`), evitando alocações dinâmicas fragmentadas (`std::string`) durante o loop crítico que causariam contenção de lock no alocador de heap (`malloc`).
- **Determinismo e Equivalência de Saída:** Para um mesmo conjunto de parâmetros `(tamanho, chave, senha)`, a saída gerada pelas versões Sequencial, Processos e Threads deve ser estritamente idêntica bit a bit (`diff s.out p.out == 0`).
- **Isometria de Medição:** O cálculo de desempenho deve utilizar `std::chrono::high_resolution_clock` posicionado exatamente nos mesmos pontos lógicos nas três versões, isolando o Tempo de Geração do Dicionário e o Tempo Total (incluindo alocação/mapeamento e cifragem).
- **Rigor Científico na Experimentação:** Todas as métricas de desempenho (Tempo, Speedup e Eficiência) devem ser extraídas a partir da média aritmética e desvio padrão de 5 execuções consecutivas por cenário experimental.

## 3. Regras de Negócios e Restrições Inegociáveis (Edital SO2)
1. **Proibição de Hardcoding:** É expressamente proibido fixar parâmetros de execução no código-fonte. Todos os binários devem aceitar argumentos via CLI (`argc`/`argv`) no formato padronizado: `./app <workers> [tamanho] [chave] [senha]`, possuindo valores *default* de fallback apenas quando omitidos os argumentos opcionais (ex: `tamanho = 10000000`, `chave = 84729`, `senha = "AvaliacaoSO2"`).
2. **Baseline Relevante ($T_{\text{seq}} \ge 2.0\text{s}$):** A versão sequencial, mesmo compilada com otimização máxima (`g++ -O3`), deve apresentar tempo de execução igual ou superior a 2,0 segundos no host físico (garantido pelo laço de 10.000.000 de posições com 50 iterações matemáticas modulares por índice).
3. **Compartilhamento Real de Memória em Processos:** A versão de processos deve utilizar obrigatoriamente `fork()`, sincronização via `waitpid()` e memória compartilhada alocada com `mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0)`, contornando o isolamento por *Copy-on-Write* (CoW).
4. **Sincronização e Região Crítica Explícita:** Além da decomposição de domínio em blocos disjuntos (*chunking*), as versões paralelas devem implementar uma métrica global de validação/integridade (ex: checksum acumulativo das entradas geradas) atualizada em região crítica protegida por `std::mutex` (em `/threads`) e sincronização atômica ou mutex em memória compartilhada (em `/processos`).
5. **Isolamento de Recursos via Cgroups:** A bateria de testes em container deve utilizar Docker com a flag `--cpus` configurada para `"1"`, `"2"` e `"4"`, permitindo avaliar a contenção no escalonador *Completely Fair Scheduler* (CFS) e o overhead de troca de contexto.
6. **Estrutura Canônica de Entrega:** O repositório deve obedecer estritamente à árvore `/sequencial`, `/processos`, `/threads`, `/container`, `/testes` (com `/entradas` e `/resultados`) e `/documentacao`, contendo arquivos `Makefile` e `README.md` individuais e completos em cada módulo.

## 4. Público-Alvo e Stakeholders
- **Banca Avaliadora / Docente:** Professor da disciplina de Sistemas Operacionais 2 da FAETERJ Petrópolis (Avaliação P1).
- **Desenvolvedor / Autor:** Wallace Duarte Venâncio (execução técnica, análise de métricas e defesa oral individual).
- **Agentes de Desenvolvimento/Automação:** Ambientes de execução Linux e ferramentas de engenharia assistida encarregadas da codificação, automação de testes e plotagem de resultados.