# ==============================================================================
# Dockerfile - Projeto Criptografador de Senhas com Dicionario Dinamico (SO2)
# Instituicao: FAETERJ Petropolis | Aluno: Wallace Duarte Venancio
# ==============================================================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Instalacao do compilador C++, ferramentas de build e Python/Matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    make \
    python3 \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

# 2. Configuracao do diretorio de trabalho
WORKDIR /projeto

# 3. Copia dos modulos de codigo-fonte e scripts de teste
COPY common/ ./common/
COPY sequencial/ ./sequencial/
COPY processos/ ./processos/
COPY threads/ ./threads/
COPY testes/ ./testes/

# 4. Compilacao limpa e otimizada (-O3) dos tres paradigmas
RUN make -C sequencial clean all && \
    make -C processos clean all && \
    make -C threads clean all

# Comando padrao de verificacao (pode ser sobrescrito no docker run)
CMD ["./threads/app", "4", "10000000", "84729", "AvaliacaoSO2"]

