# Módulo de Containerização e Controle de Recursos (`/container`)

Este módulo provê a infraestrutura de empacotamento em container Docker (`ubuntu:24.04`) e limitação de recursos de hardware via **Linux Control Groups (`cgroups`)** para o projeto de Sistemas Operacionais 2 (FAETERJ Petrópolis).

O objetivo experimental deste ambiente é submeter as implementações concorrentes (`/processos` e `/threads`) a cotas estritas de processamento (`--cpus="1"`, `--cpus="2"` e `--cpus="4"`), permitindo mensurar na prática o efeito da contenção no escalonador **Completely Fair Scheduler (CFS)** do Kernel Linux, a sobrecarga de trocas de contexto (*context switches*) e a invalidação de caches L1/L2 quando o número de fluxos concorrentes ($P$) excede a cota de núcleos físicos/virtuais disponíveis.

---

## 1. Instalação de Dependências

Para construir e executar o ambiente containerizado, é necessário possuir o **Docker Engine** instalado e ativo na distribuição Linux hospedeira (bem como `g++` e `make` caso utilize o modo direto com `systemd-run`/`cgroups v2`).

### No Debian / Ubuntu (e derivados):
```bash
sudo apt update
sudo apt install -y docker.io build-essential g++ make
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### No Arch Linux / Manjaro:
```bash
sudo pacman -S --needed docker base-devel gcc make
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### No Fedora / RHEL:
```bash
sudo dnf install -y docker gcc-c++ make
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

---

## 2. Compilação do Programa (Build da Imagem Docker)

O `Dockerfile` localizado neste diretório utiliza a imagem base oficial `ubuntu:24.04`, instala o conjunto de ferramentas `build-essential`, `g++`, `make` e `python3-matplotlib`, copia os módulos `/sequencial`, `/processos`, `/threads` e `/testes`, e compila automaticamente os três binários com a flag de otimização `-O3`.

A partir da raiz do projeto (`/projeto`), execute o comando de build:
```bash
docker build -t projeto-so2 -f container/Dockerfile .
```

Para verificar se a imagem foi criada com sucesso:
```bash
docker images | grep projeto-so2
```

---

## 3. Instruções de Execução

A execução com limitação de núcleos pode ser feita diretamente via comando `docker run --rm --cpus="<N>"` ou através do script orquestrador automatizado `./container/run_docker.sh`.

### Sintaxe via Script Auxiliar (`run_docker.sh`):
```bash
./container/run_docker.sh <cpus> <paradigma> <workers> [tamanho] [chave] [senha]
```

### Sintaxe Direta via Docker CLI (Exemplos Oficiais do Edital):

#### 1. Execução de 4 Processos restritos a 1 CPU (`--cpus="1"`):
```bash
docker run --rm --cpus="1" projeto-so2 ./processos/app 4 10000000 84729 AvaliacaoSO2
```

#### 2. Execução de 4 Threads restritas a 2 CPUs (`--cpus="2"`):
```bash
docker run --rm --cpus="2" projeto-so2 ./threads/app 4 10000000 84729 AvaliacaoSO2
```

#### 3. Execução de 8 Threads restritas a 4 CPUs (`--cpus="4"`):
```bash
docker run --rm --cpus="4" projeto-so2 ./threads/app 8 10000000 84729 AvaliacaoSO2
```

#### 4. Execução de Cenário de Alta Contenção (8 Workers disputando 1 única CPU):
```bash
./container/run_docker.sh 1 threads 8 10000000 84729 AvaliacaoSO2
```

---

## 4. Fundamentação Teórica de Sistemas Operacionais (Cgroups & CFS)

1. **Mecanismo de Cgroups no Kernel Linux:** Quando passamos a flag `--cpus="1"`, o Docker configura o subsistema de controle de CPU do kernel (`cpu.cfs_quota_us = 100000` e `cpu.cfs_period_us = 100000` no cgroups v1, ou `cpu.max = "100000 100000"` no cgroups v2). Isso limita o tempo total de CPU de todos os processos/threads do container a **100 ms a cada janela de 100 ms** (equivalente a exatamente 1 núcleo lógico).
2. **Degradação sob Contenção (`8 workers` em `--cpus="1"`):** Quando instanciamos 8 threads ou 8 processos sob o limite de 1 CPU, não há paralelismo físico real, apenas **concorrência por multiplexação temporal (time-sharing)**. O escalonador *Completely Fair Scheduler* (CFS) fatia a cota única de 100 ms entre os 8 fluxos, forçando preempções constantes, salvamento/restauração de registradores, invalidação de linhas de cache L1/L2 (*cache thrashing*) e *TLB flushes* (no caso de processos), tornando o tempo de execução com 8 workers em 1 CPU superior ao tempo de 1 único worker sequencial.

