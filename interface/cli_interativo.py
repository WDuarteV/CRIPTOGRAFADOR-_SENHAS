#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from kw2_helper import decrypt_tokens
except ImportError:
    from interface.kw2_helper import decrypt_tokens

# Cores ANSI
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
PURPLE = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header():
    print(f"{CYAN}{BOLD}")
    print("=================================================================")
    print("   CRIPTOGRAFADOR DINÂMICO DE SENHAS - SISTEMAS OPERACIONAIS II  ")
    print("       Laboratório CLI de Paralelismo, Cifragem & Telemetria     ")
    print("=================================================================")
    print(f"{RESET}")


def main():
    print_header()

    # 1. Pergunta da Senha
    senha_input = input(f"{BOLD}1. Digite a senha a ser criptografada [Padrão: AvaliacaoSO2]: {RESET}").strip()
    if not senha_input:
        senha_input = "AvaliacaoSO2"

    # 2. Pergunta do Paradigma
    print(f"\n{BOLD}2. Escolha o paradigma de execução:{RESET}")
    print("   [1] Sequencial (Baseline monothread)")
    print("   [2] Threads (std::thread + std::mutex - multithreading)")
    print("   [3] Processos (fork + mmap MAP_SHARED + pthread_mutex - POSIX IPC)")
    escolha_paradigma = input(f"{BOLD}Opção [1, 2 ou 3 - Padrão 2]: {RESET}").strip()
    if escolha_paradigma == "1":
        paradigma = "sequencial"
    elif escolha_paradigma == "3":
        paradigma = "processos"
    else:
        paradigma = "threads"

    # 3. Quantidade de Workers
    workers = 4
    if paradigma != "sequencial":
        workers_input = input(f"\n{BOLD}3. Quantidade de workers (1, 2, 4, 8) [Padrão: 4]: {RESET}").strip()
        try:
            workers = int(workers_input) if workers_input else 4
        except ValueError:
            workers = 4
    else:
        workers = 1

    # 4. Tamanho do Dicionário (Padrão real = 2 -> 10.000.000)
    print(f"\n{BOLD}4. Tamanho do Dicionário Dinâmico:{RESET}")
    print("   [1] 1.000.000 posições (~30,5 MB - Rápido)")
    print("   [2] 10.000.000 posições (~305,2 MB / 320 MB decimais - Oficial SO2)")
    tamanho_op = input(f"{BOLD}Opção [1 ou 2 - Padrão 2]: {RESET}").strip()
    tamanho = 1000000 if tamanho_op == "1" else 10000000
    mem_mb = (tamanho * 32) / (1024 * 1024)

    chave = 84729

    # 5. Palavra-Chave Secreta (2a camada de proteção contra engenharia reversa)
    print(f"\n{BOLD}5. Palavra-Chave Secreta (Camada Extra KW2 SHA-256):{RESET}")
    palavra_chave = ""
    while not palavra_chave:
        palavra_chave = input(f"{BOLD}   Digite a palavra-chave secreta (obrigatória para proteger/decifrar): {RESET}").strip()
        if not palavra_chave:
            print(f"   {YELLOW}Aviso: informe uma palavra-chave não vazia.{RESET}")

    # Verificação e compilação do binário C++
    binary_path = os.path.join(BASE_DIR, paradigma, "app")
    if not os.path.exists(binary_path):
        print(f"\n{YELLOW}[*] Compilando binário C++ ({paradigma})...{RESET}")
        subprocess.run(["make", "-C", os.path.join(BASE_DIR, paradigma)], check=True)

    print(f"\n{CYAN}[*] Executando motor C++ nativo ({paradigma} com {workers} workers, N={tamanho:,})...{RESET}")
    cmd = [binary_path, str(workers), str(tamanho), str(chave), senha_input, palavra_chave]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Erro ao executar binário: {res.stderr}")
        return

    # Extrair telemetria parseável
    parsed = {}
    capturing = False
    for line in res.stdout.splitlines():
        if line.strip() == "[DADOS_PARSEAVEIS]":
            capturing = True
            continue
        if capturing and "=" in line:
            k, v = line.strip().split("=", 1)
            parsed[k] = v

    t_ger = float(parsed.get("TEMPO_GERACAO", 0.0))
    t_tot = float(parsed.get("TEMPO_TOTAL", 0.0))
    checksum = parsed.get("CHECKSUM", "0")
    senha_cifrada = parsed.get("SENHA_CIFRADA", "")
    senha_decifrada_cpp = parsed.get("SENHA_DECIFRADA", "")

    t_base = 3.862093 if tamanho == 10000000 else 0.388000
    speedup = (t_base / t_ger) if t_ger > 0 else 1.0
    eficiencia = (speedup / workers) * 100.0 if workers > 0 else 100.0

    # Exibição dos Resultados e Telemetria
    print(f"\n{GREEN}{BOLD}==================== RESULTADOS DA TELEMETRIA ===================={RESET}")
    print(f"  • Paradigma Utilizado:   {CYAN}{paradigma.upper()}{RESET}")
    print(f"  • Workers Ativos (P):    {CYAN}{workers} (Fatia: {tamanho // workers:,} posições/worker){RESET}")
    print(f"  • Tamanho Dicionário:    {CYAN}{tamanho:,} posições ({mem_mb:.2f} MB){RESET}")
    print(f"  • Chave Modular:         {CYAN}{chave}{RESET}")
    print(f"  • Checksum Integridade:  {PURPLE}{checksum}{RESET}")
    print(f"  • Tempo de Geração:      {YELLOW}{t_ger:.6f} s{RESET}")
    print(f"  • Tempo Total:           {YELLOW}{t_tot:.6f} s{RESET}")
    print(f"  • Speedup Estimado (Sp): {GREEN}{speedup:.2f}x (Eficiência: {eficiencia:.1f}%){RESET}")
    print(f"  • Throughput:            {CYAN}{(tamanho / t_ger / 1e6):.2f} Milhões/s{RESET}")
    print(f"{GREEN}------------------------------------------------------------------{RESET}")
    print(f"  {BOLD}Senha Original:{RESET}          {senha_input}")
    print(f"  {BOLD}Senha Criptografada:{RESET}     {GREEN}{senha_cifrada}{RESET}")
    print(f"  {BOLD}Reversão no Dicionário:{RESET}  {CYAN}{senha_decifrada_cpp} (Validado em Memória C++){RESET}")
    print(f"{GREEN}=================================================================={RESET}")

    # 5. Descriptografia Detalhada
    print()
    resp_desc = input(f"{BOLD}Deseja inspecionar a descriptografia reversa passo a passo? [S/n]: {RESET}").strip().lower()
    if resp_desc != "n":
        kw_decifrar = input(f"{BOLD}Informe a palavra-chave secreta para destravar e descriptografar: {RESET}").strip()
        print(f"\n{CYAN}[*] Validando palavra-chave (KW2) e processando descriptografia reversa...{RESET}")
        inicio_desc = time.perf_counter()
        ok, resultado_desc, _ = decrypt_tokens(senha_cifrada, chave, tamanho, workers, kw_decifrar)
        fim_desc = time.perf_counter()

        print(f"\n{GREEN}{BOLD}=================== RESULTADO DA DESCRIPTOGRAFIA ==================={RESET}")
        print(f"  • Senha Cifrada de Entrada: {senha_cifrada[:45]}...")
        print(f"  • Tempo de Verificação:     {(fim_desc - inicio_desc)*1000:.3f} ms")
        if ok:
            print(f"  • Senha Recuperada:         {BOLD}{GREEN}'{resultado_desc}'{RESET}")
            if resultado_desc == senha_input:
                print(f"  • Status de Integridade:    {GREEN}{BOLD}✔ 100% EXATA (KW2 + Dicionário Validados){RESET}")
            else:
                print(f"  • Status de Integridade:    {YELLOW}Aviso de divergência{RESET}")
        else:
            print(f"  • Erro de Descriptografia:  {RED}{BOLD}✘ {resultado_desc}{RESET}")
        print(f"{GREEN}=================================================================={RESET}\n")


if __name__ == "__main__":
    main()
