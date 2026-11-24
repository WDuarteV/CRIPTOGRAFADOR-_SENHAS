# Criptografador Dinâmico de Senhas (`KW2$`) — Paralelismo, IPC & Docker

Aplicação de criptografia e descriptografia simétrica baseada em **dicionário dinâmico em memória (320 MB para `N = 10.000.000`)** combinada com uma **2ª camada de proteção por Palavra-Chave Secreta (`KW2$`)** usando derivação SHA-256 (10.000 iterações), padding PKCS#7 (blocos de 32 bytes), cifragem por fluxo CTR e tag MAC de integridade.

Desenvolvida originalmente para a disciplina **Sistemas Operacionais 2 (FAETERJ Petrópolis)** comparando execução **Sequencial**, **Threads (`std::thread` + `std::mutex`)**, **Processos (`fork()` + `mmap MAP_SHARED` + `pthread_mutex_t`)** e **Container Docker (`--cpus`)**, agora endurecida contra engenharia reversa para uso pessoal.

---

## Como funciona a criptografia em 2 passos

1. **Passo 1 — Dicionário Dinâmico Contíguo (`EntradaDic[32B]`):**
   Gera `N` entradas determinísticas (`50` iterações modulares por posição), soma o `checksum_global` em região crítica com mutex e mapeia cada caractere da senha via índice `(ASCII × K) mod N`.
2. **Passo 2 — Camada Extra com Palavra-Chave (`KW2$` em [`common/keyword_crypto.hpp`](common/keyword_crypto.hpp)):**
   Quando uma palavra-chave secreta é informada (obrigatória na interface web e no CLI interativo), o payload de tokens passa por:
   - Derivação de chave de 256 bits (`10.000` rodadas SHA-256 sobre `palavra_chave`, `K` e `N`);
   - Padding PKCS#7 para múltiplos de 32 bytes (oculta o comprimento exato da senha);
   - Cifragem por fluxo SHA-256 CTR + tag MAC de 16 bytes (`KW2$<ciphertext_hex>$<mac_hex>`).

Sem a palavra-chave correta, a tag MAC bloqueia a descriptografia mesmo para quem possui acesso ao código-fonte.

---

## Estrutura do Projeto

- `common/` — Cabeçalho C++17 compartilhado (`keyword_crypto.hpp`) com SHA-256 e proteção `KW2$`
- `sequencial/` — Implementação baseline monothread (`C++17`)
- `threads/` — Implementação paralela com `std::thread` e `std::mutex`
- `processos/` — Implementação paralela com `fork()`, `mmap(MAP_SHARED)` e `pthread_mutex` (`PTHREAD_PROCESS_SHARED`)
- `interface/` — Servidor HTTP (`server.py`), helper `kw2_helper.py`, CLI interativo (`cli_interativo.py`) e painel web (`static/`)
- `container/` — `Dockerfile` (`ubuntu:24.04`) e `run_docker.sh` (com fallback `systemd-run` / `taskset`)
- `testes/` — Scripts de benchmark (`benchmark_host.sh`, `benchmark_dock.sh`), gerador de gráficos (`plot_graficos.py`) e resultados CSV/PNG/SVG
- `documentacao/` — Manuais, explicações da arquitetura, roteiro de apresentação e guias em HTML/PDF

---

## Como executar (Linux ou Windows via WSL2)

> **Nota sobre Windows:** o módulo `processos/` utiliza APIs POSIX/Linux (`fork`, `mmap`, `waitpid`, `PTHREAD_PROCESS_SHARED`). No Windows, execute via **WSL2 (Ubuntu)** ou **Docker Desktop**.

### 1. Interface Web (recomendado)
Requer `g++`, `make` e `python3`:

```bash
./executar_interface.sh
```

Acesse **`http://localhost:5000`** no navegador. Os binários C++ são compilados automaticamente caso não existam.

### 2. CLI Interativo
```bash
python3 interface/cli_interativo.py
```

### 3. Execução direta em C++
```bash
make -C threads
./threads/app <workers> [tamanho] [chave] [senha] [palavra_chave]
# Exemplo com proteção KW2:
./threads/app 4 10000000 84729 MinhaSenha123 MinhaPalavraSecreta
```

### 4. Execução via Docker / Cgroups
```bash
./container/run_docker.sh 2 threads 4 10000000 84729 MinhaSenha123 MinhaPalavraSecreta
```

