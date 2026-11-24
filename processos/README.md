# Módulo Concorrente com Processos - Criptografador de Senhas Baseado em Dicionário Dinâmico

Este módulo implementa a versão concorrente baseada em múltiplos processos do projeto acadêmico de Sistemas Operacionais 2 (FAETERJ Petrópolis).

O programa particiona a geração massiva do dicionário dinâmico em blocos contíguos disjuntos (*chunking*) processados em paralelo por processos filhos criados via chamada de sistema `fork()`. O compartilhamento de dados ocorre sobre uma região de memória mapeada com `mmap(..., MAP_SHARED | MAP_ANONYMOUS, ...)`, eliminando o isolamento de memória imposto pelo mecanismo de *Copy-on-Write* (CoW) do Linux. A sincronização de integridade é realizada em região crítica com `pthread_mutex_t` configurado como `PTHREAD_PROCESS_SHARED` e a barreira final de sincronização é estabelecida pelo processo pai via `waitpid()`.

---

## 1. Instalação de Dependências

O módulo utiliza primitivas POSIX e C++17, necessitando do conjunto de desenvolvimento padrão GNU (`g++`, `make`, `glibc` com suporte a `pthreads`).

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

O `Makefile` deste módulo inclui as diretivas de otimização `-O3`, padrões modernos `-std=c++17` e a biblioteca de threads POSIX `-pthread` para suportar o mutex interprocessos:

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

O programa aceita parâmetros dinâmicos via linha de comando (`argc`/`argv`):

```bash
./app <workers> [tamanho] [chave] [senha]
```

### Significado dos Parâmetros:
- `<workers>`: Quantidade de processos filhos a serem criados via `fork()` (Obrigatório; ex: `1`, `2`, `4`, `8`).
- `[tamanho]` *(Opcional)*: Quantidade de posições do dicionário $N$ (Padrão: `10000000`).
- `[chave]` *(Opcional)*: Semente inteira para o cálculo modular (Padrão: `84729`).
- `[senha]` *(Opcional)*: String a ser criptografada (Padrão: `"AvaliacaoSO2"`).

---

### Exemplos Reais de Execução

#### 1. Execução Concorrente com 4 Processos (Cenário Oficial de Benchmark):
```bash
./app 4 10000000 84729 AvaliacaoSO2
```
*Saída obtida:*
```text
==================================================
   Criptografador de Senhas - Dicionario Dinamico 
==================================================
[CONFIGURACAO]
Paradigma:            Processos (fork + mmap)
Workers Solicitados:  4 (processos filhos)
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
Tempo de Geracao:     2.497229 s
Tempo Total:          2.497364 s
==================================================
[DADOS_PARSEAVEIS]
PARADIGMA=processos
WORKERS=4
TAMANHO=10000000
CHAVE=84729
CHECKSUM=5000000903112875
SENHA_CIFRADA=734705969_tsbus-344817495_tsbus-626125172_tsbus-500933052_tsbus-571520743_tsbus-626125172_tsbus-515793045_tsbus-626125172_tsbus-538256351_tsbus-714093983_tsbus-646836158_tsbus-082839254_tsbus
SENHA_DECIFRADA=AvaliacaoSO2
TEMPO_GERACAO=2.497229
TEMPO_TOTAL=2.497364
```

#### 2. Teste de Equivalência Estrita via `diff` contra a Versão Sequencial:
```bash
diff -u <(../sequencial/app 1 10000000 84729 AvaliacaoSO2 | sed -n "/\[RESULTADOS\]/,/\[TELEMETRIA\]/p") \
        <(./app 4 10000000 84729 AvaliacaoSO2 | sed -n "/\[RESULTADOS\]/,/\[TELEMETRIA\]/p")
```
*(Retorno 0 sem diferenças, comprovando identidade bit a bit dos resultados).*

#### 3. Exibição da Tela de Ajuda:
```bash
./app --help
```

---

## 4. Detalhes de Arquitetura e Engenharia de Sistemas Operacionais
1. **Memória Compartilhada Real (`mmap`):** A flag `MAP_SHARED` instrui o kernel a gravar modificações diretamente nas páginas físicas compartilhadas, enquanto `MAP_ANONYMOUS` dispensa arquivos temporários em disco. Isso impede que o mecanismo de *Copy-on-Write* (CoW) isole os dados nos processos filhos.
2. **Exclusão Mútua Interprocessos:** A região crítica que atualiza o `checksum_global` utiliza um `pthread_mutex_t` com atributo `PTHREAD_PROCESS_SHARED`, permitindo que processos com espaços de endereçamento distintos acessem com segurança o mesmo primitivo de sincronização.
3. **Divisão de Carga Limpa:** Não há condições de corrida durante a escrita do dicionário porque os intervalos $[start, end)$ são estritamente disjuntos.
4. **Higienização de Recursos:** Ao término da cifragem, o processo pai destrói o mutex (`pthread_mutex_destroy`) e libera as regiões mapeadas via `munmap()`.
