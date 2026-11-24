#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from kw2_helper import (
        compute_token_for_char,
        decrypt_tokens,
        decrypt_with_keyword,
        find_worker_for_index,
    )
except ImportError:
    from interface.kw2_helper import (
        compute_token_for_char,
        decrypt_tokens,
        decrypt_with_keyword,
        find_worker_for_index,
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
RESULTS_DIR = os.path.join(BASE_DIR, "testes", "resultados")

# Cache de baseline sequencial por tamanho N para calculo imediato de Speedup (Sp) e Eficiencia (Ep)
BASELINE_CACHE = {
    10000000: 3.862093,
    1000000: 0.388000,
    100000: 0.039000,
}


def ensure_binaries():
    """Compila os binarios C++ se ainda nao existirem."""
    for name in ["sequencial", "threads", "processos"]:
        path = os.path.join(BASE_DIR, name)
        binary = os.path.join(path, "app")
        if not os.path.exists(binary):
            print(f"[*] Compilando binario {name}...")
            subprocess.run(["make", "-C", path], check=True)


def get_official_baseline():
    summary_json = os.path.join(RESULTS_DIR, "resumo_estatistico.json")
    if os.path.exists(summary_json):
        try:
            with open(summary_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "baseline_sequencial_s" in data:
                    BASELINE_CACHE[10000000] = float(data["baseline_sequencial_s"])
        except Exception:
            pass
    return BASELINE_CACHE[10000000]


def get_system_info():
    """Detecta informacoes de CPU, RAM e baseline sequencial."""
    cores = os.cpu_count() or 1
    cpu_model = "Desconhecido"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    total_mem_gb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    mem_kb = int(line.split()[1])
                    total_mem_gb = round(mem_kb / (1024 * 1024), 2)
                    break
    except Exception:
        pass

    return {
        "cores": cores,
        "cpu_model": cpu_model,
        "total_mem_gb": total_mem_gb,
        "baseline_seq_10m": round(get_official_baseline(), 4),
        "os": "Linux (Cgroups v2 / CFS)",
    }


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silenciar logs repetitivos de GET estatico
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            file_path = os.path.join(STATIC_DIR, "index.html")
            self.serve_file(file_path, "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(STATIC_DIR, rel_path)
            content_type = "text/plain"
            if rel_path.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif rel_path.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
            elif rel_path.endswith(".png"):
                content_type = "image/png"
            elif rel_path.endswith(".svg"):
                content_type = "image/svg+xml"
            self.serve_file(file_path, content_type)
        elif path.startswith("/results/"):
            rel_path = path[len("/results/"):]
            file_path = os.path.join(RESULTS_DIR, rel_path)
            content_type = "image/png" if rel_path.endswith(".png") else "text/plain"
            self.serve_file(file_path, content_type)
        elif path == "/api/system_info":
            self.send_json(get_system_info())
        elif path == "/api/official_results":
            self.handle_official_results()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def serve_file(self, file_path, content_type):
        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Arquivo nao encontrado")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length)

        try:
            req_data = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            req_data = {}

        if parsed.path == "/api/run":
            self.handle_run(req_data)
        elif parsed.path == "/api/decrypt":
            self.handle_decrypt(req_data)
        elif parsed.path == "/api/benchmark":
            self.handle_benchmark(req_data)
        elif parsed.path == "/api/diff_check":
            self.handle_diff_check(req_data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Endpoint inexistente")

    def handle_official_results(self):
        summary_json = os.path.join(RESULTS_DIR, "resumo_estatistico.json")
        if not os.path.exists(summary_json):
            plot_script = os.path.join(BASE_DIR, "testes", "plot_graficos.py")
            if os.path.exists(plot_script):
                subprocess.run(["python3", plot_script], check=False)

        if os.path.exists(summary_json):
            with open(summary_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["success"] = True
            self.send_json(data)
        else:
            self.send_json({"success": False, "error": "Resultados oficiais ainda nao gerados."}, 404)

    def handle_run(self, data):
        paradigm = data.get("paradigm", "threads")
        workers = int(data.get("workers", 4))
        cpus_limit = str(data.get("cpus_limit", "ilimitado"))
        size = int(data.get("size", 10000000))
        key = int(data.get("key", 84729))
        password = str(data.get("password", "AvaliacaoSO2"))
        keyword = str(data.get("keyword", ""))

        if paradigm not in ["sequencial", "threads", "processos"]:
            self.send_json({"error": "Paradigma invalido"}, 400)
            return

        effective_workers = 1 if paradigm == "sequencial" else workers
        ensure_binaries()

        extra_args = [keyword] if keyword else []
        masked_suffix = ' "***"' if keyword else ""

        if cpus_limit in ["1", "2", "4"]:
            runner = os.path.join(BASE_DIR, "container", "run_docker.sh")
            cmd = [runner, cpus_limit, paradigm, str(effective_workers), str(size), str(key), password] + extra_args
            cmd_display = f'./container/run_docker.sh {cpus_limit} {paradigm} {effective_workers} {size} {key} "{password}"{masked_suffix}'
        else:
            binary_path = os.path.join(BASE_DIR, paradigm, "app")
            cmd = [binary_path, str(effective_workers), str(size), str(key), password] + extra_args
            cmd_display = f'./{paradigm}/app {effective_workers} {size} {key} "{password}"{masked_suffix}'

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
            stdout = res.stdout
            stderr = res.stderr

            parsed_vars = {}
            capture = False
            for line in stdout.splitlines():
                if line.strip() == "[DADOS_PARSEAVEIS]":
                    capture = True
                    continue
                if capture and "=" in line:
                    k, v = line.strip().split("=", 1)
                    parsed_vars[k] = v

            tempo_geracao = float(parsed_vars.get("TEMPO_GERACAO", 0.0))
            tempo_total = float(parsed_vars.get("TEMPO_TOTAL", 0.0))
            checksum = parsed_vars.get("CHECKSUM", "0")
            senha_cifrada = parsed_vars.get("SENHA_CIFRADA", "")
            senha_decifrada = parsed_vars.get("SENHA_DECIFRADA", password)

            if paradigm == "sequencial" and cpus_limit == "ilimitado" and tempo_geracao > 0:
                BASELINE_CACHE[size] = tempo_geracao

            t_base = BASELINE_CACHE.get(size, tempo_geracao if tempo_geracao > 0 else 1.0)
            speedup = (t_base / tempo_geracao) if tempo_geracao > 0 else 1.0
            eficiencia = (speedup / effective_workers) if effective_workers > 0 else 1.0

            throughput = (size / tempo_geracao) if tempo_geracao > 0 else 0
            mem_mb = (size * 32) / (1024 * 1024)

            # Decomposicao de Dominio (Chunking Paralelo)
            chunks = []
            chunk_len = size // effective_workers
            for p in range(effective_workers):
                st = p * chunk_len
                en = size if p == effective_workers - 1 else st + chunk_len
                count = en - st
                chunks.append({
                    "worker_id": p,
                    "start_idx": st,
                    "end_idx": en,
                    "count": count,
                    "pct": round((count / size) * 100.0, 1),
                    "mem_mb": round((count * 32) / (1024 * 1024), 2),
                })

            # Decomposicao dos caracteres + identificacao do worker gerador
            ok_kw, payload_passo1 = decrypt_with_keyword(senha_cifrada, keyword, key, size)
            tokens = payload_passo1.split("-") if (ok_kw and payload_passo1) else []
            char_breakdown = []
            for i, c in enumerate(password):
                tok = tokens[i] if i < len(tokens) else compute_token_for_char(ord(c), key, size)[0]
                idx = (ord(c) * key) % size
                w_id, w_st, w_en = find_worker_for_index(idx, size, effective_workers)
                char_breakdown.append({
                    "char": c,
                    "ascii": ord(c),
                    "index": idx,
                    "worker_id": w_id,
                    "worker_range": f"[{w_st:,}..{w_en:,})".replace(",", "."),
                    "token": tok,
                })

            response = {
                "success": True,
                "paradigm": paradigm,
                "workers": effective_workers,
                "cpus_limit": cpus_limit,
                "size": size,
                "key": key,
                "kw2_protected": bool(keyword),
                "password": password,
                "tempo_geracao": tempo_geracao,
                "tempo_total": tempo_total,
                "baseline_seq": round(t_base, 6),
                "speedup": round(speedup, 3),
                "eficiencia_pct": round(eficiencia * 100.0, 1),
                "checksum": checksum,
                "senha_cifrada": senha_cifrada,
                "senha_decifrada": senha_decifrada,
                "throughput": round(throughput, 2),
                "mem_mb": round(mem_mb, 2),
                "chunks": chunks,
                "char_breakdown": char_breakdown,
                "cmd_display": cmd_display,
                "stdout": stdout,
                "stderr": stderr,
            }
            self.send_json(response)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_decrypt(self, data):
        cipher = str(data.get("cipher", ""))
        size = int(data.get("size", 10000000))
        key = int(data.get("key", 84729))
        workers = int(data.get("workers", 4))
        keyword = str(data.get("keyword", ""))

        ok, result_or_err, steps = decrypt_tokens(cipher, key, size, workers, keyword)
        if not ok:
            self.send_json({"success": False, "error": result_or_err}, 400)
            return

        self.send_json({
            "success": True,
            "decrypted_password": result_or_err,
            "total_tokens": len(steps),
            "steps": steps,
            "key": key,
            "size": size,
            "workers": workers,
            "kw2_protected": cipher.strip().startswith("KW2$"),
        })

    def handle_diff_check(self, data):
        ensure_binaries()
        size = int(data.get("size", 1000000))
        key = int(data.get("key", 84729))
        password = str(data.get("password", "AvaliacaoSO2"))
        keyword = str(data.get("keyword", "ValidacaoSO2_KW2"))
        extra = [keyword] if keyword else []

        cmds = {
            "sequencial": [os.path.join(BASE_DIR, "sequencial", "app"), "1", str(size), str(key), password] + extra,
            "processos": [os.path.join(BASE_DIR, "processos", "app"), "4", str(size), str(key), password] + extra,
            "threads": [os.path.join(BASE_DIR, "threads", "app"), "4", str(size), str(key), password] + extra,
        }
        outputs = {}
        results_blocks = {}
        for name, cmd in cmds.items():
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            outputs[name] = res.stdout
            lines = []
            in_block = False
            for line in res.stdout.splitlines():
                if line.strip() == "[RESULTADOS]":
                    in_block = True
                if in_block:
                    lines.append(line)
                if in_block and line.strip().startswith("Senha Descriptograf.:"):
                    break
            results_blocks[name] = "\n".join(lines)

        eq_proc = results_blocks["sequencial"] == results_blocks["processos"]
        eq_thr = results_blocks["sequencial"] == results_blocks["threads"]

        log_lines = [
            "==================================================================",
            "  VERIFICACAO ESTRITA DE EQUIVALENCIA DE SAIDA (diff s.out p.out) ",
            "==================================================================",
            f"Parametros: N={size} | Chave={key} | Senha={password}",
            "",
            "--- [1] Bloco [RESULTADOS] de ./sequencial/app 1 ---",
            results_blocks["sequencial"],
            "",
            "--- [2] Bloco [RESULTADOS] de ./processos/app 4 ---",
            results_blocks["processos"],
            "",
            "--- [3] Bloco [RESULTADOS] de ./threads/app 4 ---",
            results_blocks["threads"],
            "",
            "------------------------------------------------------------------",
            f"diff (Sequencial vs Processos 4w) : {'0 DIFERENCAS (100% IDENTICO BIT A BIT)' if eq_proc else 'DIVERGENTE'}",
            f"diff (Sequencial vs Threads 4w)   : {'0 DIFERENCAS (100% IDENTICO BIT A BIT)' if eq_thr else 'DIVERGENTE'}",
            "==================================================================",
        ]
        self.send_json({
            "success": True,
            "equivalent": eq_proc and eq_thr,
            "log": "\n".join(log_lines),
        })

    def handle_benchmark(self, data):
        size = int(data.get("size", 1000000))
        key = int(data.get("key", 84729))
        password = str(data.get("password", "AvaliacaoSO2"))
        ensure_binaries()

        scenarios = [
            ("host", "sequencial", 1, "ilimitado"),
            ("host", "processos", 1, "ilimitado"),
            ("host", "processos", 2, "ilimitado"),
            ("host", "processos", 4, "ilimitado"),
            ("host", "processos", 8, "ilimitado"),
            ("host", "threads", 1, "ilimitado"),
            ("host", "threads", 2, "ilimitado"),
            ("host", "threads", 4, "ilimitado"),
            ("host", "threads", 8, "ilimitado"),
            ("docker", "processos", 2, "1"),
            ("docker", "processos", 4, "1"),
            ("docker", "processos", 8, "1"),
            ("docker", "threads", 2, "1"),
            ("docker", "threads", 4, "1"),
            ("docker", "threads", 8, "1"),
            ("docker", "processos", 2, "2"),
            ("docker", "processos", 4, "2"),
            ("docker", "processos", 8, "2"),
            ("docker", "threads", 2, "2"),
            ("docker", "threads", 4, "2"),
            ("docker", "threads", 8, "2"),
            ("docker", "processos", 2, "4"),
            ("docker", "processos", 4, "4"),
            ("docker", "processos", 8, "4"),
            ("docker", "threads", 2, "4"),
            ("docker", "threads", 4, "4"),
            ("docker", "threads", 8, "4"),
        ]

        results = []
        t_seq = 0.0
        runner = os.path.join(BASE_DIR, "container", "run_docker.sh")

        for amb, paradigm, workers, cpus in scenarios:
            if amb == "docker":
                cmd = [runner, cpus, paradigm, str(workers), str(size), str(key), password]
            else:
                binary_path = os.path.join(BASE_DIR, paradigm, "app")
                cmd = [binary_path, str(workers), str(size), str(key), password]

            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                parsed_vars = {}
                capture = False
                for line in res.stdout.splitlines():
                    if line.strip() == "[DADOS_PARSEAVEIS]":
                        capture = True
                        continue
                    if capture and "=" in line:
                        k, v = line.strip().split("=", 1)
                        parsed_vars[k] = v

                t_ger = float(parsed_vars.get("TEMPO_GERACAO", 0.0))
                t_tot = float(parsed_vars.get("TEMPO_TOTAL", 0.0))
                chk = parsed_vars.get("CHECKSUM", "0")

                if amb == "host" and paradigm == "sequencial":
                    t_seq = t_ger
                    BASELINE_CACHE[size] = t_seq

                speedup = (t_seq / t_ger) if t_ger > 0 and t_seq > 0 else 1.0
                eficiencia = (speedup / workers) if workers > 0 else 1.0

                results.append({
                    "ambiente": amb,
                    "implementacao": paradigm,
                    "workers": workers,
                    "cpus_limit": cpus,
                    "execucoes": 1,
                    "media_geracao_s": round(t_ger, 6),
                    "desvio_geracao_s": 0.0,
                    "media_total_s": round(t_tot, 6),
                    "desvio_total_s": 0.0,
                    "speedup": round(speedup, 4),
                    "eficiencia": round(eficiencia, 4),
                    "eficiencia_pct": round(eficiencia * 100.0, 2),
                    "checksum": chk,
                })
            except Exception as e:
                results.append({
                    "ambiente": amb,
                    "implementacao": paradigm,
                    "workers": workers,
                    "cpus_limit": cpus,
                    "error": str(e),
                })

        self.send_json({
            "success": True,
            "baseline_sequencial_s": round(t_seq, 6),
            "size": size,
            "key": key,
            "password": password,
            "cenarios": results,
        })


def run_server(port=5000):
    ensure_binaries()
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"\n=======================================================")
    print(f"🚀 PAINEL VISUAL SO2 INICIADO COM SUCESSO!")
    print(f"📡 Acesse localmente em: http://localhost:{port}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Encerrando servidor HTTP...")
        httpd.server_close()


if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
