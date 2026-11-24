# Módulo Paralelo com Multithreading - Criptografador de Senhas Baseado em Dicionário Dinâmico

Este módulo implementa a versão paralela baseada em multithreading com `std::thread` do projeto acadêmico de Sistemas Operacionais 2 (FAETERJ Petrópolis).

Diferente do módulo concorrente de processos que exige chamadas de sistema para memória compartilhada (`mmap`), esta versão opera sobre o espaço de endereçamento único compartilhado nativamente pelas threads do processo. O particionamento da carga de cálculo é feito através de fatias contíguas disjuntas (*chunking*), garantindo que cada thread trabalhadora processe uma região exclusiva do vetor `EntradaDic`. A sincronização da métrica global de integridade (`checksum_global`) é protegida por uma região crítica controlada por `std::mutex` com gerenciamento RAII via `std::lock_guard`, e a barreira final de sincronização é estabelecida com a chamada `.join()` sobre todas as threads ativas.

---

## 1. Instalação de Dependências

O módulo utiliza o padrão moderno C++17 e a biblioteca de threads padrão do C++, requerendo os pacotes essenciais do compilador GNU.

### No Debian/Ubuntu (e derivados):
```bash
sudo apt update
sudo apt install -y build-essential g++ make
```

### No Arch Linux / Manjaro:
```bash
sudo pacman -S --needed base-devel gcc make
```

### No Fedora / RHEL:
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install -y gcc-c++ make
```

---

## 2. Compilação do Programa

O `Makefile` deste módulo compila com o nível máximo de otimização (`-O3`), advertências rigorosas (`-Wall -Wextra`), padrão C++17 e suporte à biblioteca de threads POSIX (`-pthread`):

Para compilar e gerar o binário `app`:
```bash
make
```

Para remover o binário gerado:
```bash
make clean
```

---

## 3. Instruções de Execução

Conforme as restrições estritas da disciplina (proibição de *hardcoding*), o binário recebe argumentos via linha de comando (`argc`/`argv`):

```bash
./app <workers> [tamanho] [chave] [senha]
```

### Significado dos Parâmetros:
- `<workers>`: Quantidade de threads de trabalho a serem instanciadas via `std::thread` (Obrigatório; ex: `1`, `2`, `4`, `8`).
- `[tamanho]` *(Opcional)*: Quantidade de posições do dicionário $N$ (Padrão: `10000000`).
- `[chave]` *(Opcional)*: Semente inteira para o cálculo modular (Padrão: `84729`).
- `[senha]` *(Opcional)*: String a ser criptografada (Padrão: `"AvaliacaoSO2"`).

---

### Exemplos Reais de Execução

#### 1. Execução Paralela com 4 Threads (Cenário Oficial de Benchmark):
```bash
./app 4 10000000 84729 AvaliacaoSO2
```
*Saída obtida no host:*
```text
==================================================
   Criptografador de Senhas - Dicionario Dinamico 
==================================================
[CONFIGURACAO]
Paradigma:            Threads (std::thread)
Workers Solicitados:  4 (threads de trabalho)
Tamanho Dicionario:   10000000
Chave Secreta:        84729
Senha Original:       AvaliacaoSO2
--------------------------------------------------
[RESULTADOS]
Checksum Integridade: 5000000903112875
Senha Criptografada:  734705969_tsbus-344817495_tsbus-626125172_tsbus-500933052_tsbus-571520743_tsbus-626125172_tsbus-515793045_tsbus-626125172_tsbus-538256351_tsbus-714093983_tsbus-646836158_tsbus-082839254_tsbus
Senha Descriptograf.: AvaliacaoSO2
--------------------------------------------------
[TELEMETRIA]
Tempo de Geracao:     1.812575 s
Tempo Total:          1.812601 s
==================================================
[DADOS_PARSEAVEIS]
PARADIGMA=threads
WORKERS=4
TAMANHO=10000000
CHAVE=84729
CHECKSUM=5000000903112875
SENHA_CIFRADA=734705969_tsbus-344817495_tsbus-626125172_tsbus-500933052_tsbus-571520743_tsbus-626125172_tsbus-515793045_tsbus-626125172_tsbus-538256351_tsbus-714093983_tsbus-646836158_tsbus-082839254_tsbus
SENHA_DECIFRADA=AvaliacaoSO2
TEMPO_GERACAO=1.812575
TEMPO_TOTAL=1.812601
```

#### 2. Validação Cruzada via `diff` (Sequencial vs. Processos vs. Threads):
```bash
diff -u <(../sequencial/app 1 10000000 84729 AvaliacaoSO2 | sed -n "/\[RESULTADOS\]/,/\[TELEMETRIA\]/p") \
        <(./app 4 10000000 84729 AvaliacaoSO2 | sed -n "/\[RESULTADOS\]/,/\[TELEMETRIA\]/p")
```
*(Retorno 0 comprovando equivalência estrita de saída)*.

#### 3. Exibição da Tela de Ajuda:
```bash
./app --help
```

---

## 4. Análise Comparativa e Decisões de Engenharia
1. **Espaço de Endereçamento Compartilhado:** Elimina o overhead de chamadas de sistema de IPC (`mmap`, criação de tabelas de páginas próprias para cada processo), resultando em menor latência de inicialização e maior eficiência energética da CPU.
2. **Mitigação de Contenção de Lock de Heap:** O vetor `EntradaDic` contíguo evita que as threads disputem os locks internos do alocador `malloc` da biblioteca C (`glibc`), permitindo paralelismo real e escalabilidade próxima ao limite teórico da Lei de Amdahl.
3. **Região Crítica Otimizada:** Em vez de travar o mutex a cada índice do laço (o que destruiria o paralelismo por contenção excessiva de lock), cada thread acumula seu checksum local em registrador/pilha privativa e entra na região crítica **uma única vez** ao final do seu bloco para somar ao totalizador global.
