#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de Consolidacao Estatistica e Plotagem dos 3 Graficos Obrigatorios (SO2)
Disciplina: Sistemas Operacionais 2 - FAETERJ Petropolis
Aluno: Wallace Duarte Venancio

Consome:
  - /testes/resultados/tempos_host.csv
  - /testes/resultados/tempos_docker.csv
Exporta:
  - /testes/resultados/resumo_estatistico.csv
  - /testes/resultados/resumo_estatistico.json
  - /testes/resultados/grafico1_tempo.png
  - /testes/resultados/grafico2_speedup.png
  - /testes/resultados/grafico3_docker.png
"""

import os
import csv
import json
import math
import shutil
import statistics
import subprocess
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "testes", "resultados")
HOST_CSV = os.path.join(RES_DIR, "tempos_host.csv")
DOCK_CSV = os.path.join(RES_DIR, "tempos_docker.csv")
SUMMARY_CSV = os.path.join(RES_DIR, "resumo_estatistico.csv")
SUMMARY_JSON = os.path.join(RES_DIR, "resumo_estatistico.json")


def load_csv_rows(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def aggregate_metrics():
    host_rows = load_csv_rows(HOST_CSV)
    dock_rows = load_csv_rows(DOCK_CSV)
    all_rows = host_rows + dock_rows

    grouped = {}
    for r in all_rows:
        key = (
            r["ambiente"].strip(),
            r["implementacao"].strip(),
            int(r["workers"]),
            str(r["cpus_limit"]).strip(),
        )
        grouped.setdefault(key, []).append(
            (float(r["tempo_geracao_s"]), float(r["tempo_total_s"]), r["checksum"].strip())
        )

    # Obter baseline sequencial no host
    seq_key = ("host", "sequencial", 1, "ilimitado")
    t_seq_ger = 3.85
    t_seq_tot = 3.85
    if seq_key in grouped and grouped[seq_key]:
        t_seq_ger = statistics.mean(x[0] for x in grouped[seq_key])
        t_seq_tot = statistics.mean(x[1] for x in grouped[seq_key])

    summary_list = []
    for (amb, impl, workers, cpus), vals in sorted(
        grouped.items(), key=lambda x: (x[0][0], x[0][3], x[0][1], x[0][2])
    ):
        ger_list = [v[0] for v in vals]
        tot_list = [v[1] for v in vals]
        chk = vals[0][2]

        mean_ger = statistics.mean(ger_list)
        sd_ger = statistics.stdev(ger_list) if len(ger_list) > 1 else 0.0
        mean_tot = statistics.mean(tot_list)
        sd_tot = statistics.stdev(tot_list) if len(tot_list) > 1 else 0.0

        speedup = (t_seq_ger / mean_ger) if mean_ger > 0 else 1.0
        eficiencia = (speedup / workers) if workers > 0 else 1.0

        summary_list.append({
            "ambiente": amb,
            "implementacao": impl,
            "workers": workers,
            "cpus_limit": cpus,
            "execucoes": len(vals),
            "media_geracao_s": round(mean_ger, 6),
            "desvio_geracao_s": round(sd_ger, 6),
            "media_total_s": round(mean_tot, 6),
            "desvio_total_s": round(sd_tot, 6),
            "speedup": round(speedup, 4),
            "eficiencia": round(eficiencia, 4),
            "eficiencia_pct": round(eficiencia * 100.0, 2),
            "checksum": chk,
        })

    os.makedirs(RES_DIR, exist_ok=True)
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "ambiente", "implementacao", "workers", "cpus_limit", "execucoes",
            "media_geracao_s", "desvio_geracao_s", "media_total_s", "desvio_total_s",
            "speedup", "eficiencia", "eficiencia_pct", "checksum"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_list)

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "baseline_sequencial_s": round(t_seq_ger, 6),
            "baseline_total_s": round(t_seq_tot, 6),
            "cenarios": summary_list,
        }, f, indent=2, ensure_ascii=False)

    return t_seq_ger, summary_list


def lookup(summary_list, ambiente, impl, workers, cpus="ilimitado"):
    for item in summary_list:
        if (
            item["ambiente"] == ambiente
            and item["implementacao"] == impl
            and item["workers"] == workers
            and str(item["cpus_limit"]) == str(cpus)
        ):
            return item
    return None


def render_svg_to_png(svg_content, png_path, width=1200, height=720):
    """Renderiza SVG para PNG de alta resolucao usando Chrome Headless ou Matplotlib."""
    svg_path = png_path.replace(".png", ".svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    chrome_bin = shutil.which("google-chrome-stable") or shutil.which("chromium") or shutil.which("google-chrome")
    if chrome_bin:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: {width}px; height: {height}px; overflow: hidden; background: #0b0f19; }}
</style></head><body>{svg_content}</body></html>""")
        try:
            subprocess.run(
                [
                    chrome_bin,
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    f"--window-size={width},{height}",
                    f"--screenshot={png_path}",
                    f"file://{tmp_path}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=20,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def generate_grafico1_svg(t_seq, summary):
    """Grafico 1: Tempo de Execucao (s) - X: Workers (1, 2, 4, 8), Series: Seq, Processos, Threads."""
    workers_list = [1, 2, 4, 8]
    seq_vals = [t_seq for _ in workers_list]
    proc_vals = []
    proc_sds = []
    thr_vals = []
    thr_sds = []

    for w in workers_list:
        p = lookup(summary, "host", "processos", w)
        t = lookup(summary, "host", "threads", w)
        proc_vals.append(p["media_geracao_s"] if p else t_seq)
        proc_sds.append(p["desvio_geracao_s"] if p else 0.0)
        thr_vals.append(t["media_geracao_s"] if t else t_seq)
        thr_sds.append(t["desvio_geracao_s"] if t else 0.0)

    max_y = max(seq_vals + proc_vals + thr_vals) * 1.18
    if max_y <= 0:
        max_y = 5.0

    W, H = 1200, 720
    pad_l, pad_r, pad_t, pad_b = 110, 60, 110, 110
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    def y_pos(v):
        return pad_t + plot_h - (v / max_y) * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:#0b0f19;font-family:\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">',
        f'<rect width="{W}" height="{H}" fill="#0b0f19"/>',
        f'<text x="{W/2}" y="46" text-anchor="middle" fill="#f8fafc" font-size="24" font-weight="700">Gráfico 1: Tempo Médio de Execução no Host (N = 10.000.000)</text>',
        f'<text x="{W/2}" y="76" text-anchor="middle" fill="#94a3b8" font-size="15">Comparativo entre Baseline Sequencial, Processos (fork + mmap) e Threads (std::thread) • Média ± DP (5 execuções)</text>',
    ]

    # Grid Y
    steps_y = 6
    for i in range(steps_y + 1):
        val = (max_y / steps_y) * i
        yp = y_pos(val)
        svg.append(f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{W - pad_r}" y2="{yp:.1f}" stroke="#1e293b" stroke-width="1.5"/>')
        svg.append(f'<text x="{pad_l - 14}" y="{yp + 5:.1f}" text-anchor="end" fill="#94a3b8" font-size="14">{val:.2f} s</text>')

    # Eixos
    svg.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{W - pad_r}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<text x="36" y="{pad_t + plot_h/2}" transform="rotate(-90 36,{pad_t + plot_h/2})" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Tempo de Geração do Dicionário (segundos)</text>')
    svg.append(f'<text x="{pad_l + plot_w/2}" y="{H - 25}" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Quantidade de Trabalhadores (Workers P)</text>')

    # Linha tracejada do Baseline Sequencial
    y_seq = y_pos(t_seq)
    svg.append(f'<line x1="{pad_l}" y1="{y_seq:.1f}" x2="{W - pad_r}" y2="{y_seq:.1f}" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="8,6"/>')
    svg.append(f'<rect x="{W - pad_r - 290}" y="{y_seq - 38:.1f}" width="284" height="24" rx="4" fill="#0b0f19" opacity="0.88"/>')
    svg.append(f'<text x="{W - pad_r - 10}" y="{y_seq - 21:.1f}" text-anchor="end" fill="#fbbf24" font-size="13" font-weight="700">Baseline Sequencial (T_seq = {t_seq:.3f}s)</text>')

    group_w = plot_w / len(workers_list)
    bar_w = 56

    for idx, w in enumerate(workers_list):
        cx = pad_l + group_w * (idx + 0.5)
        svg.append(f'<text x="{cx:.1f}" y="{pad_t + plot_h + 34}" text-anchor="middle" fill="#f1f5f9" font-size="16" font-weight="700">{w} {"Worker" if w == 1 else "Workers"}</text>')

        # Barra Sequencial (apenas em 1w ou referencia visual)
        bars = [
            ("Sequencial", seq_vals[idx], 0.0, "#f59e0b", cx - bar_w * 1.6),
            ("Processos", proc_vals[idx], proc_sds[idx], "#a855f7", cx - bar_w * 0.5),
            ("Threads", thr_vals[idx], thr_sds[idx], "#0ea5e9", cx + bar_w * 0.6),
        ]
        for label, val, sd, color, bx in bars:
            by = y_pos(val)
            bh = (pad_t + plot_h) - by
            svg.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh:.1f}" rx="5" fill="{color}" opacity="0.9"/>')
            # Error bar
            if sd > 0:
                y_top = y_pos(val + sd)
                y_bot = y_pos(max(0, val - sd))
                mx = bx + bar_w / 2
                svg.append(f'<line x1="{mx:.1f}" y1="{y_top:.1f}" x2="{mx:.1f}" y2="{y_bot:.1f}" stroke="#f8fafc" stroke-width="2"/>')
                svg.append(f'<line x1="{mx - 8:.1f}" y1="{y_top:.1f}" x2="{mx + 8:.1f}" y2="{y_top:.1f}" stroke="#f8fafc" stroke-width="2"/>')
                svg.append(f'<line x1="{mx - 8:.1f}" y1="{y_bot:.1f}" x2="{mx + 8:.1f}" y2="{y_bot:.1f}" stroke="#f8fafc" stroke-width="2"/>')
            svg.append(f'<text x="{bx + bar_w/2:.1f}" y="{by - 10:.1f}" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="700">{val:.2f}s</text>')

    # Legenda no canto superior direito (onde as barras de 4w e 8w sao baixas)
    leg_x = W - pad_r - 370
    leg_y = pad_t + 14
    legends = [
        ("Sequencial (Baseline)", "#f59e0b"),
        ("Processos (fork + mmap MAP_SHARED)", "#a855f7"),
        ("Threads (std::thread + std::mutex)", "#0ea5e9"),
    ]
    svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="360" height="96" rx="8" fill="#111827" stroke="#334155"/>')
    for i, (lname, lcol) in enumerate(legends):
        ly = leg_y + 24 + i * 28
        svg.append(f'<rect x="{leg_x + 16}" y="{ly - 12}" width="16" height="16" rx="3" fill="{lcol}"/>')
        svg.append(f'<text x="{leg_x + 42}" y="{ly + 1}" fill="#e2e8f0" font-size="14" font-weight="600">{lname}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def generate_grafico2_svg(t_seq, summary):
    """Grafico 2: Speedup (Sp = T_seq / Tp) vs Speedup Linear Ideal (y = x) - Lei de Amdahl."""
    workers_list = [1, 2, 4, 8]
    ideal_vals = [float(w) for w in workers_list]
    proc_sp = []
    thr_sp = []

    for w in workers_list:
        p = lookup(summary, "host", "processos", w)
        t = lookup(summary, "host", "threads", w)
        proc_sp.append(p["speedup"] if p else 1.0)
        thr_sp.append(t["speedup"] if t else 1.0)

    max_y = 8.5
    W, H = 1200, 720
    pad_l, pad_r, pad_t, pad_b = 110, 60, 110, 110
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    def x_pos(idx):
        return pad_l + (plot_w / (len(workers_list) - 1)) * idx

    def y_pos(v):
        return pad_t + plot_h - (v / max_y) * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:#0b0f19;font-family:\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">',
        f'<rect width="{W}" height="{H}" fill="#0b0f19"/>',
        f'<text x="{W/2}" y="46" text-anchor="middle" fill="#f8fafc" font-size="24" font-weight="700">Gráfico 2: Curva de Speedup (Sp = T_seq / T_p) vs. Linear Ideal (Lei de Amdahl)</text>',
        f'<text x="{W/2}" y="76" text-anchor="middle" fill="#94a3b8" font-size="15">Análise de Escalabilidade Real e Limite de Saturação de Barramento de Memória (320 MB)</text>',
    ]

    for i in range(9):
        val = float(i)
        yp = y_pos(val)
        svg.append(f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{W - pad_r}" y2="{yp:.1f}" stroke="#1e293b" stroke-width="1.5"/>')
        svg.append(f'<text x="{pad_l - 14}" y="{yp + 5:.1f}" text-anchor="end" fill="#94a3b8" font-size="14">{val:.1f}x</text>')

    svg.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{W - pad_r}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<text x="36" y="{pad_t + plot_h/2}" transform="rotate(-90 36,{pad_t + plot_h/2})" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Speedup Acelerado (Sp = T_seq / T_p)</text>')
    svg.append(f'<text x="{pad_l + plot_w/2}" y="{H - 25}" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Quantidade de Trabalhadores (Workers P)</text>')

    for idx, w in enumerate(workers_list):
        xp = x_pos(idx)
        svg.append(f'<line x1="{xp:.1f}" y1="{pad_t}" x2="{xp:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" stroke-dasharray="4,4"/>')
        svg.append(f'<text x="{xp:.1f}" y="{pad_t + plot_h + 34}" text-anchor="middle" fill="#f1f5f9" font-size="16" font-weight="700">{w} {"Worker" if w == 1 else "Workers"}</text>')

    def draw_line(vals, color, dashed=False, label_offset=-14):
        pts = " ".join(f"{x_pos(i):.1f},{y_pos(v):.1f}" for i, v in enumerate(vals))
        dash_attr = 'stroke-dasharray="8,6"' if dashed else ""
        svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="3.5" {dash_attr} points="{pts}"/>')
        for i, v in enumerate(vals):
            xp, yp = x_pos(i), y_pos(v)
            svg.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="6.5" fill="{color}" stroke="#0b0f19" stroke-width="2"/>')
            svg.append(f'<text x="{xp:.1f}" y="{yp + label_offset:.1f}" text-anchor="middle" fill="{color}" font-size="14" font-weight="700">{v:.2f}x</text>')

    draw_line(ideal_vals, "#64748b", dashed=True, label_offset=-16)
    draw_line(thr_sp, "#10b981", dashed=False, label_offset=-12)
    draw_line(proc_sp, "#a855f7", dashed=False, label_offset=24)

    # Legenda
    leg_x = pad_l + 24
    leg_y = pad_t + 20
    legends = [
        ("Speedup Linear Ideal (y = P)", "#64748b"),
        ("Speedup Real — Threads (std::thread)", "#10b981"),
        ("Speedup Real — Processos (fork + mmap)", "#a855f7"),
    ]
    svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="370" height="98" rx="8" fill="#111827" stroke="#334155"/>')
    for i, (lname, lcol) in enumerate(legends):
        ly = leg_y + 24 + i * 28
        svg.append(f'<rect x="{leg_x + 16}" y="{ly - 12}" width="16" height="16" rx="3" fill="{lcol}"/>')
        svg.append(f'<text x="{leg_x + 42}" y="{ly + 1}" fill="#e2e8f0" font-size="14" font-weight="600">{lname}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def generate_grafico3_svg(t_seq, summary):
    """Grafico 3: Host vs Docker/Cgroups (--cpus=1, 2, 4) para 2, 4 e 8 Workers."""
    workers_list = [2, 4, 8]
    # Comparamos Threads e Processos sob --cpus="1", "2", "4" vs Host Ilimitado
    series_defs = [
        ("Docker --cpus=1 (Threads)", "docker", "threads", "1", "#ef4444"),
        ("Docker --cpus=1 (Processos)", "docker", "processos", "1", "#f97316"),
        ("Docker --cpus=2 (Threads)", "docker", "threads", "2", "#eab308"),
        ("Docker --cpus=2 (Processos)", "docker", "processos", "2", "#ec4899"),
        ("Docker --cpus=4 (Threads)", "docker", "threads", "4", "#3b82f6"),
        ("Docker --cpus=4 (Processos)", "docker", "processos", "4", "#06b6d4"),
        ("Host Ilimitado (Processos)", "host", "processos", "ilimitado", "#a855f7"),
        ("Host Ilimitado (Threads)", "host", "threads", "ilimitado", "#10b981"),
    ]

    all_vals = [t_seq]
    series_data = []
    for label, amb, impl, cpus, color in series_defs:
        vals = []
        for w in workers_list:
            item = lookup(summary, amb, impl, w, cpus)
            v = item["media_geracao_s"] if item else 0.0
            vals.append(v)
            all_vals.append(v)
        series_data.append((label, vals, color))

    max_y = max(all_vals) * 1.22
    if max_y <= 0:
        max_y = 6.0

    W, H = 1200, 720
    pad_l, pad_r, pad_t, pad_b = 110, 60, 155, 95
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    def y_pos(v):
        return pad_t + plot_h - (v / max_y) * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:#0b0f19;font-family:\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">',
        f'<rect width="{W}" height="{H}" fill="#0b0f19"/>',
        f'<text x="{W/2}" y="42" text-anchor="middle" fill="#f8fafc" font-size="24" font-weight="700">Gráfico 3: Host Físico vs. Container Docker / Cgroups (--cpus="1", "2", "4")</text>',
        f'<text x="{W/2}" y="70" text-anchor="middle" fill="#94a3b8" font-size="15">Impacto do Escalonador CFS e Sobrecarga de Troca de Contexto sob Restrição de Hardware</text>',
    ]

    # Legenda horizontal no topo (2 linhas x 4 colunas, livre de sobreposicao com barras)
    leg_x = pad_l
    leg_y = 86
    svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="{plot_w}" height="54" rx="8" fill="#111827" stroke="#334155"/>')
    col_w = plot_w / 4
    for i, (lname, _, lcol) in enumerate(series_data):
        row = i // 4
        col = i % 4
        lx = leg_x + col * col_w + 14
        ly = leg_y + 20 + row * 22
        svg.append(f'<rect x="{lx:.1f}" y="{ly - 10}" width="12" height="12" rx="3" fill="{lcol}"/>')
        svg.append(f'<text x="{lx + 18:.1f}" y="{ly}" fill="#e2e8f0" font-size="11.5" font-weight="600">{lname}</text>')

    steps_y = 6
    for i in range(steps_y + 1):
        val = (max_y / steps_y) * i
        yp = y_pos(val)
        svg.append(f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{W - pad_r}" y2="{yp:.1f}" stroke="#1e293b" stroke-width="1.5"/>')
        svg.append(f'<text x="{pad_l - 14}" y="{yp + 5:.1f}" text-anchor="end" fill="#94a3b8" font-size="14">{val:.2f} s</text>')

    svg.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{W - pad_r}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="2"/>')
    svg.append(f'<text x="36" y="{pad_t + plot_h/2}" transform="rotate(-90 36,{pad_t + plot_h/2})" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Tempo de Execução (segundos)</text>')
    svg.append(f'<text x="{pad_l + plot_w/2}" y="{H - 25}" text-anchor="middle" fill="#cbd5e1" font-size="16" font-weight="600">Quantidade de Trabalhadores Concorrentes (Workers P)</text>')

    group_w = plot_w / len(workers_list)
    bar_w = 32
    bar_gap = 5
    n_series = len(series_data)
    cluster_w = n_series * bar_w + (n_series - 1) * bar_gap

    for idx, w in enumerate(workers_list):
        cx = pad_l + group_w * (idx + 0.5)
        svg.append(f'<text x="{cx:.1f}" y="{pad_t + plot_h + 34}" text-anchor="middle" fill="#f1f5f9" font-size="16" font-weight="700">{w} Workers</text>')
        start_x = cx - cluster_w / 2
        for s_idx, (label, vals, color) in enumerate(series_data):
            val = vals[idx]
            bx = start_x + s_idx * (bar_w + bar_gap)
            by = y_pos(val)
            bh = (pad_t + plot_h) - by
            svg.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh:.1f}" rx="4" fill="{color}" opacity="0.92"/>')
            svg.append(f'<text x="{bx + bar_w/2:.1f}" y="{by - 6:.1f}" text-anchor="middle" fill="#f8fafc" font-size="10" font-weight="700">{val:.2f}s</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    print("[*] Processando CSVs e calculando estatisticas (media, desvio padrao, speedup, eficiencia)...")
    t_seq, summary = aggregate_metrics()
    print(f"    Baseline Sequencial (T_seq): {t_seq:.6f} s")
    print(f"    Total de cenarios sumarizados: {len(summary)}")

    g1_path = os.path.join(RES_DIR, "grafico1_tempo.png")
    g2_path = os.path.join(RES_DIR, "grafico2_speedup.png")
    g3_path = os.path.join(RES_DIR, "grafico3_docker.png")

    print("[*] Renderizando Grafico 1 (Tempo de Execucao)...")
    render_svg_to_png(generate_grafico1_svg(t_seq, summary), g1_path)

    print("[*] Renderizando Grafico 2 (Speedup vs Ideal Linear)...")
    render_svg_to_png(generate_grafico2_svg(t_seq, summary), g2_path)

    print("[*] Renderizando Grafico 3 (Host vs Docker/Cgroups)...")
    render_svg_to_png(generate_grafico3_svg(t_seq, summary), g3_path)

    print("[OK] Graficos gerados com sucesso em:", RES_DIR)


if __name__ == "__main__":
    main()

