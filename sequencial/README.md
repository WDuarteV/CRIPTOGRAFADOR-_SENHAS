# Módulo Sequencial (Baseline) - Criptografador de Senhas Baseado em Dicionário Dinâmico

Este módulo implementa a versão sequencial (monothread) de referência para o projeto de Sistemas Operacionais 2 (FAETERJ Petrópolis). O programa gera um dicionário de substituição de larga escala em memória primária e realiza a cifragem determinística de uma senha a partir do mapeamento de caracteres.

Esta implementação serve como a linha de base (*baseline*) para o cálculo de *Speedup* ($S_p = T_{\text{seq}} / T_p$) e *Eficiência* ($E_p = S_p / p$) frente às implementações paralelas com processos (`/processos`) e threads (`/threads`).

---

## 1. Instalação de Dependências

O projeto foi desenvolvido em C++ moderno (C++17) e requer uma distribuição Linux padrão com os pacotes básicos de compilação GNU instalados.

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

O módulo possui um `Makefile` configurado com nível máximo de otimização (`-O3`), advertências rigorosas (`-Wall -Wextra`) e padrão C++17.

Para compilar e gerar o executável `app`:
```bash
make
```

Para limpar o binário gerado:
```bash
make clean
```

---

## 3. Instruções de Execução

Conforme as restrições estritas da disciplina (proibição de *hardcoding*), o executável aceita parâmetros dinâmicos via linha de comando (`argc`/`argv`):

```bash
./app <workers> [tamanho] [chave] [senha]
```

### Significado dos Parâmetros:
- `<workers>`: Quantidade de fluxos de execução solicitados. No modo sequencial, o programa executa com **1 worker** efetivo, preservando a assinatura unificada de CLI exigida pelo edital.
- `[tamanho]` *(Opcional)*: Quantidade de entradas do dicionário $N$ (Padrão: `10000000`).
- `[chave]` *(Opcional)*: Semente numérica inteira para o laço modular de 50 iterações (Padrão: `84729`).
- `[senha]` *(Opcional)*: String a ser criptografada (Padrão: `"AvaliacaoSO2"`).

---

### Exemplos Reais de Execução

#### 1. Execução Padrão de Calibração (Cenário Oficial de Benchmark):
```bash
./app 1 10000000 84729 AvaliacaoSO2
```
*Saída esperada:*
```text
==================================================
   Criptografador de Senhas - Dicionario Dinamico 
==================================================
[CONFIGURACAO]
Paradigma:            Sequencial
Workers Solicitados:  1 (efetivo: 1)
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
Tempo de Geracao:     3.873064 s
Tempo Total:          3.873093 s
==================================================
[DADOS_PARSEAVEIS]
PARADIGMA=sequencial
WORKERS=1
TAMANHO=10000000
CHAVE=84729
CHECKSUM=5000000903112875
SENHA_CIFRADA=734705969_tsbus-344817495_tsbus-626125172_tsbus-500933052_tsbus-571520743_tsbus-626125172_tsbus-515793045_tsbus-626125172_tsbus-538256351_tsbus-714093983_tsbus-646836158_tsbus-082839254_tsbus
SENHA_DECIFRADA=AvaliacaoSO2
TEMPO_GERACAO=3.873064
TEMPO_TOTAL=3.873093
```

#### 2. Execução Rápida para Teste Funcional:
```bash
./app 1 500000 12345 TesteRapido
```

#### 3. Exibição da Tela de Ajuda:
```bash
./app --help
```

---

## 4. Notas de Engenharia e Performance
1. **Memória Contígua:** Utiliza a estrutura `struct EntradaDic { char valor[32]; }`, ocupando ~320 MB para $N = 10.000.000$.
2. **Zero Overhead de Heap:** O laço de formatação e reversão opera diretamente com buffer local estático e escrita no vetor contíguo, eliminando chamadas repetitivas ao alocador `malloc` (`std::string`), o que evita gargalos de lock de heap.
3. **Calibração de Tempo ($T_{\text{seq}} \ge 2.0\text{s}$):** A carga matemática de 50 iterações modulares sobre 10 milhões de elementos garante um tempo de baseline robusto (~3.8s), em estrita conformidade com os requisitos do edital da FAETERJ Petrópolis.
