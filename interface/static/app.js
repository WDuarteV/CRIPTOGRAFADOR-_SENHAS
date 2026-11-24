// ==========================================================
// CONTROLE DE INTERFACE, CHUNKING PARALELO & TELEMETRIA - SO2
// ==========================================================

let currentCiphertext = "";
let chartTimesInstance = null;
let chartSpeedupInstance = null;
let chartDockerInstance = null;

const WORKER_COLORS = [
  "#0284c7", "#7c3aed", "#059669", "#d97706",
  "#e11d48", "#2563eb", "#9333ea", "#0d9488"
];

document.addEventListener("DOMContentLoaded", () => {
  fetchSystemInfo();
  onParadigmChange("threads");
  renderChunkingPreview();
  loadOfficialBenchmarkResults();

  document.getElementById("param-workers").addEventListener("change", renderChunkingPreview);
  document.getElementById("param-size").addEventListener("change", renderChunkingPreview);
});

// Alternância de Abas
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  const targetContent = document.getElementById(`tab-${tabId}`);

  if (targetBtn) targetBtn.classList.add("active");
  if (targetContent) targetContent.classList.add("active");

  if (tabId === "benchmark") {
    setTimeout(() => {
      if (chartTimesInstance) chartTimesInstance.resize();
      if (chartSpeedupInstance) chartSpeedupInstance.resize();
      if (chartDockerInstance) chartDockerInstance.resize();
    }, 60);
  }
}

// Informações de Sistema
async function fetchSystemInfo() {
  try {
    const res = await fetch("/api/system_info");
    const data = await res.json();
    document.getElementById("cpu-cores-val").textContent = `${data.cores} núcleos lógicos`;
    document.getElementById("ram-val").textContent = `${data.total_mem_gb} GB`;
    if (data.baseline_seq_10m) {
      document.getElementById("baseline-seq-val").textContent = `${data.baseline_seq_10m} s`;
    }
  } catch (err) {
    console.warn("Falha ao obter dados do sistema:", err);
  }
}

// Mudança de Paradigma
function onParadigmChange(paradigm) {
  document.querySelectorAll(".radio-card").forEach(c => c.classList.remove("active"));
  const checkedRadio = document.querySelector(`input[name="paradigm"][value="${paradigm}"]`);
  if (checkedRadio && checkedRadio.parentElement) {
    checkedRadio.parentElement.classList.add("active");
  }

  const workersSelect = document.getElementById("param-workers");
  const syncBadge = document.getElementById("metric-sync-primitive");
  const ipcSub = document.getElementById("metric-ipc-sub");

  if (paradigm === "sequencial") {
    workersSelect.value = "1";
    workersSelect.disabled = true;
    syncBadge.textContent = "Sem Concorrência (1 Fluxo)";
    ipcSub.textContent = "Heap Contíguo (new EntradaDic[N])";
  } else if (paradigm === "threads") {
    workersSelect.disabled = false;
    if (workersSelect.value === "1") workersSelect.value = "4";
    syncBadge.textContent = "std::mutex + join()";
    ipcSub.textContent = "Espaço Virtual Compartilhado";
  } else if (paradigm === "processos") {
    workersSelect.disabled = false;
    if (workersSelect.value === "1") workersSelect.value = "4";
    syncBadge.textContent = "pthread_mutex (PROCESS_SHARED) + waitpid()";
    ipcSub.textContent = "mmap(MAP_SHARED | MAP_ANONYMOUS)";
  }

  renderChunkingPreview();
}

function setQuickPassword(pwd) {
  document.getElementById("param-password").value = pwd;
}

function toggleKeywordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const hidden = input.type === "password";
  input.type = hidden ? "text" : "password";
  if (btn) btn.textContent = hidden ? "🙈" : "👁️";
}

// Visualizador de Decomposição de Domínio (Chunking Paralelo)
function renderChunkingPreview(customChunks = null) {
  const paradigm = document.querySelector('input[name="paradigm"]:checked').value;
  const workers = paradigm === "sequencial" ? 1 : parseInt(document.getElementById("param-workers").value || "4");
  const size = parseInt(document.getElementById("param-size").value || "10000000");

  document.getElementById("chunk-total-n").textContent = size.toLocaleString("pt-BR");
  document.getElementById("chunk-end-label").textContent = size.toLocaleString("pt-BR");

  const archDesc = document.getElementById("chunk-arch-desc");
  if (paradigm === "sequencial") {
    archDesc.textContent = "Baseline Sequencial: 1 único fluxo processa [0 .. N)";
  } else if (paradigm === "threads") {
    archDesc.textContent = `${workers} Threads (std::thread) compartilhando Heap Contíguo + std::mutex`;
  } else {
    archDesc.textContent = `${workers} Processos Filhos (fork) escrevendo em mmap(MAP_SHARED) sem Copy-on-Write`;
  }

  let chunks = customChunks;
  if (!chunks) {
    chunks = [];
    const chunkLen = Math.floor(size / workers);
    for (let p = 0; p < workers; p++) {
      const st = p * chunkLen;
      const en = (p === workers - 1) ? size : st + chunkLen;
      const count = en - st;
      chunks.push({
        worker_id: p,
        start_idx: st,
        end_idx: en,
        count: count,
        pct: ((count / size) * 100).toFixed(1),
        mem_mb: ((count * 32) / (1024 * 1024)).toFixed(2)
      });
    }
  }

  const barContainer = document.getElementById("chunk-bar-container");
  const cardsGrid = document.getElementById("worker-cards-grid");
  barContainer.innerHTML = "";
  cardsGrid.innerHTML = "";

  const workerTypeLabel = paradigm === "processos" ? "Processo Filho" : (paradigm === "threads" ? "Thread" : "Fluxo Único");

  chunks.forEach((ch, idx) => {
    const color = WORKER_COLORS[idx % WORKER_COLORS.length];

    const seg = document.createElement("div");
    seg.className = "chunk-segment";
    seg.style.width = `${ch.pct}%`;
    seg.style.backgroundColor = color;
    seg.textContent = `W#${ch.worker_id} (${ch.pct}%)`;
    barContainer.appendChild(seg);

    const card = document.createElement("div");
    card.className = "worker-card";
    card.style.borderLeftColor = color;
    card.innerHTML = `
      <div class="worker-card-header">
        <span>${workerTypeLabel} #${ch.worker_id}</span>
        <span style="color:${color}">${ch.mem_mb} MB</span>
      </div>
      <div class="worker-card-detail">
        <div>Intervalo: <code>[${ch.start_idx.toLocaleString("pt-BR")} .. ${ch.end_idx.toLocaleString("pt-BR")})</code></div>
        <div>Posições: <strong>${ch.count.toLocaleString("pt-BR")}</strong> &times; 50 iter modulares</div>
        <div>Sincronização: <code>checksum_local &rarr; mutex</code></div>
      </div>
    `;
    cardsGrid.appendChild(card);
  });
}

// Execução da Criptografia & Telemetria no Motor C++
async function executeCrypto() {
  const btn = document.getElementById("btn-run");
  const btnIcon = document.getElementById("btn-run-icon");
  const btnText = document.getElementById("btn-run-text");
  const statusBadge = document.getElementById("telemetry-status-badge");

  const paradigm = document.querySelector('input[name="paradigm"]:checked').value;
  const workers = paradigm === "sequencial" ? 1 : parseInt(document.getElementById("param-workers").value);
  const cpus_limit = document.getElementById("param-cpus").value;
  const size = parseInt(document.getElementById("param-size").value);
  const key = parseInt(document.getElementById("param-key").value || "84729");
  const password = document.getElementById("param-password").value.trim();
  const keywordInput = document.getElementById("param-keyword");
  const keyword = keywordInput ? keywordInput.value.trim() : "";

  if (!password) {
    alert("Por favor, digite uma senha para criptografar.");
    return;
  }
  if (!keyword) {
    alert("Por favor, informe a Palavra-Chave Secreta! Ela é necessária para proteger a senha gerada e para descriptografar depois.");
    if (keywordInput) keywordInput.focus();
    return;
  }

  btn.disabled = true;
  btnIcon.textContent = "⏳";
  btnText.textContent = "Executando Binário C++ Nativo...";
  statusBadge.className = "pill-badge running";
  statusBadge.textContent = "Executando C++...";

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paradigm, workers, cpus_limit, size, key, password, keyword })
    });
    const data = await res.json();

    if (!data.success) {
      alert("Erro ao executar: " + (data.error || "Falha desconhecida"));
      statusBadge.className = "pill-badge error";
      statusBadge.textContent = "Erro";
      return;
    }

    // Atualizar Métricas de Telemetria e Speedup
    document.getElementById("metric-tger").textContent = `${data.tempo_geracao.toFixed(6)} s`;
    document.getElementById("metric-ttot").textContent = `${data.tempo_total.toFixed(6)} s`;
    document.getElementById("metric-speedup").textContent = `${data.speedup.toFixed(2)}x`;
    document.getElementById("metric-speedup-sub").textContent = `Baseline N=${(size/1e6).toFixed(1)}M: ${data.baseline_seq.toFixed(3)}s`;
    document.getElementById("metric-efficiency").textContent = `${data.eficiencia_pct.toFixed(1)}%`;
    document.getElementById("metric-throughput").textContent = `${(data.throughput / 1000000).toFixed(2)} M/s`;
    document.getElementById("metric-mem").textContent = `${data.mem_mb.toFixed(2)} MB`;
    document.getElementById("metric-checksum").textContent = data.checksum;

    // Atualizar Senha Cifrada e Decifrada no C++
    currentCiphertext = data.senha_cifrada;
    document.getElementById("result-ciphertext").value = data.senha_cifrada;
    document.getElementById("cpp-decrypted-check").textContent = `${data.senha_decifrada} (100% Íntegra)`;
    document.getElementById("cpp-cmd-preview").textContent = data.cmd_display;

    // Sincronizar Aba 2 (Descriptografia)
    document.getElementById("decrypt-input").value = data.senha_cifrada;
    document.getElementById("decrypt-key").value = key;
    document.getElementById("decrypt-size").value = size;
    document.getElementById("decrypt-workers").value = String(data.workers);
    const decryptKw = document.getElementById("decrypt-keyword");
    if (decryptKw) decryptKw.value = keyword;

    // Atualizar Visualizador de Chunking
    if (data.chunks) {
      renderChunkingPreview(data.chunks);
    }

    // Preencher Tabela de Decomposição por Caractere + Worker Responsável
    const tbody = document.getElementById("table-breakdown-body");
    tbody.innerHTML = "";
    data.char_breakdown.forEach((item, index) => {
      const wColor = WORKER_COLORS[item.worker_id % WORKER_COLORS.length];
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>#${index + 1}</strong></td>
        <td><span class="password-char">'${item.char}'</span></td>
        <td><code>${item.ascii}</code></td>
        <td><code>(${item.ascii} &times; ${key}) % ${size}</code></td>
        <td><strong class="text-accent">${item.index.toLocaleString("pt-BR")}</strong></td>
        <td><span class="worker-badge" style="border-color:${wColor}; color:${wColor};">Worker #${item.worker_id} ${item.worker_range}</span></td>
        <td><code class="text-emerald">${item.token}</code></td>
      `;
      tbody.appendChild(tr);
    });

    // Atualizar Terminal stdout
    appendTerminalOutput(`$ ${data.cmd_display}\n\n` + data.stdout);

    statusBadge.className = "pill-badge ready";
    statusBadge.textContent = cpus_limit === "ilimitado" ? "Concluído (Host)" : `Concluído (--cpus=${cpus_limit})`;

  } catch (err) {
    alert("Erro na requisição: " + err.message);
    statusBadge.className = "pill-badge error";
    statusBadge.textContent = "Erro";
  } finally {
    btn.disabled = false;
    btnIcon.textContent = "🚀";
    btnText.textContent = "Executar Motor C++ Paralelo & Medir Speedup";
  }
}

// Copiar Senha Cifrada
function copyCipher() {
  const txt = document.getElementById("result-ciphertext").value;
  if (!txt) {
    alert("Nenhuma senha criptografada para copiar.");
    return;
  }
  navigator.clipboard.writeText(txt);
  alert("Tokens da senha criptografada copiados para a área de transferência!");
}

// Enviar para Aba de Descriptografia
function sendToDecrypt() {
  const cipher = document.getElementById("result-ciphertext").value;
  if (!cipher) {
    alert("Execute a criptografia primeiro para gerar os tokens.");
    return;
  }
  document.getElementById("decrypt-input").value = cipher;
  document.getElementById("decrypt-key").value = document.getElementById("param-key").value;
  document.getElementById("decrypt-size").value = document.getElementById("param-size").value;
  const kwEl = document.getElementById("param-keyword");
  const decKwEl = document.getElementById("decrypt-keyword");
  if (kwEl && decKwEl) decKwEl.value = kwEl.value;
  switchTab("decrypt");
  executeDecrypt();
}

function pasteLastCipher() {
  const cipher = document.getElementById("result-ciphertext").value || currentCiphertext;
  if (!cipher) {
    alert("Nenhuma senha criptografada recente. Execute a cifragem na Aba 1 primeiro!");
    return;
  }
  document.getElementById("decrypt-input").value = cipher;
  document.getElementById("decrypt-key").value = document.getElementById("param-key").value;
  document.getElementById("decrypt-size").value = document.getElementById("param-size").value;
  const kwEl = document.getElementById("param-keyword");
  const decKwEl = document.getElementById("decrypt-keyword");
  if (kwEl && decKwEl) decKwEl.value = kwEl.value;
}

// Execução da Descriptografia Reversa com Mapeamento de Partição Paralela
async function executeDecrypt() {
  const cipher = document.getElementById("decrypt-input").value.trim();
  const key = parseInt(document.getElementById("decrypt-key").value || "84729");
  const size = parseInt(document.getElementById("decrypt-size").value || "10000000");
  const workers = parseInt(document.getElementById("decrypt-workers").value || "4");
  const keywordEl = document.getElementById("decrypt-keyword");
  const keyword = keywordEl ? keywordEl.value.trim() : "";

  if (!cipher) {
    alert("Por favor, cole ou digite uma senha criptografada para descriptografar.");
    return;
  }

  try {
    const res = await fetch("/api/decrypt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cipher, key, size, workers, keyword })
    });
    const data = await res.json();

    if (!data.success) {
      document.getElementById("decrypt-result-area").classList.add("hidden");
      alert("Erro ao descriptografar: " + (data.error || "Falha"));
      if (keywordEl && cipher.startsWith("KW2$")) keywordEl.focus();
      return;
    }

    const area = document.getElementById("decrypt-result-area");
    area.classList.remove("hidden");

    document.getElementById("decrypted-password-text").textContent = data.decrypted_password;

    const tbody = document.getElementById("decrypt-steps-body");
    tbody.innerHTML = "";
    data.steps.forEach((st, idx) => {
      const wColor = st.worker_id !== null ? WORKER_COLORS[st.worker_id % WORKER_COLORS.length] : "#64748b";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><code class="text-emerald">${st.token}</code></td>
        <td><code>${st.val !== null ? st.val : "N/A"}</code></td>
        <td><span class="password-char">'${st.char}'</span></td>
        <td><code>${st.ascii !== null ? st.ascii : "N/A"}</code></td>
        <td><strong class="text-accent">${st.index !== null ? st.index.toLocaleString("pt-BR") : "N/A"}</strong></td>
        <td><span class="worker-badge" style="border-color:${wColor}; color:${wColor};">Worker #${st.worker_id !== null ? st.worker_id : "?"} ${st.worker_range}</span></td>
        <td><span class="pill-badge ready">${st.status}</span></td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    alert("Erro ao conectar ao serviço de descriptografia: " + err.message);
  }
}

// Carregar Resultados Oficiais (5 Execuções Host + Docker)
async function loadOfficialBenchmarkResults() {
  try {
    const res = await fetch("/api/official_results");
    const data = await res.json();
    if (!data.success || !data.cenarios) return;

    document.getElementById("bench-table-source-badge").textContent =
      `Oficial: 5 Execuções/Cenário (N = 10.000.000 | T_seq = ${data.baseline_sequencial_s.toFixed(4)}s)`;

    populateBenchmarkUI(data.baseline_sequencial_s, data.cenarios);

    // Atualizar imagens estáticas PNG (cache busting)
    const ts = Date.now();
    ["img-g1", "img-g2", "img-g3"].forEach((id, i) => {
      const el = document.getElementById(id);
      if (el) {
        const names = ["grafico1_tempo.png", "grafico2_speedup.png", "grafico3_docker.png"];
        el.style.display = "block";
        el.src = `/results/${names[i]}?t=${ts}`;
      }
    });
  } catch (err) {
    console.warn("Resultados oficiais ainda em processamento:", err);
  }
}

// Execução de Benchmark ao Vivo
async function executeBenchmark() {
  const btn = document.getElementById("btn-run-bench");
  const btnIcon = document.getElementById("bench-btn-icon");
  const progress = document.getElementById("bench-progress");
  const size = parseInt(document.getElementById("bench-size").value);
  const key = parseInt(document.getElementById("param-key").value || "84729");

  btn.disabled = true;
  btnIcon.textContent = "⏳";
  progress.classList.remove("hidden");

  try {
    const res = await fetch("/api/benchmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ size, key, password: "AvaliacaoSO2" })
    });
    const data = await res.json();

    if (!data.success) {
      alert("Erro no benchmark: " + (data.error || "Erro"));
      return;
    }

    document.getElementById("bench-table-source-badge").textContent =
      `Execução ao Vivo Concluída (N = ${size.toLocaleString("pt-BR")} | T_seq = ${data.baseline_sequencial_s.toFixed(4)}s)`;

    populateBenchmarkUI(data.baseline_sequencial_s, data.cenarios);

  } catch (err) {
    alert("Falha no benchmark: " + err.message);
  } finally {
    btn.disabled = false;
    btnIcon.textContent = "⚡";
    progress.classList.add("hidden");
  }
}

function findScenario(cenarios, amb, impl, workers, cpus = "ilimitado") {
  return cenarios.find(
    c => c.ambiente === amb &&
         c.implementacao === impl &&
         Number(c.workers) === Number(workers) &&
         String(c.cpus_limit) === String(cpus)
  );
}

function populateBenchmarkUI(tSeq, cenarios) {
  const tbody = document.getElementById("bench-table-body");
  tbody.innerHTML = "";

  cenarios.forEach(sc => {
    if (sc.error) return;
    const isDocker = sc.ambiente === "docker";
    const ambBadge = isDocker
      ? `<span class="pill-badge" style="color:#fda4af; border-color:#f43f5e;">Docker (--cpus=${sc.cpus_limit})</span>`
      : `<span class="pill-badge ready">Host Físico</span>`;

    const sdStr = sc.desvio_geracao_s > 0 ? ` &plusmn; ${sc.desvio_geracao_s.toFixed(4)}` : "";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${ambBadge}</td>
      <td><strong>${sc.implementacao.toUpperCase()}</strong></td>
      <td><strong>${sc.workers}</strong></td>
      <td><code>${sc.cpus_limit}</code></td>
      <td>${sc.execucoes || 1}x</td>
      <td><strong>${sc.media_geracao_s.toFixed(6)}</strong>${sdStr} s</td>
      <td>${sc.media_total_s.toFixed(6)} s</td>
      <td><strong class="text-accent">${sc.speedup.toFixed(2)}x</strong></td>
      <td><span class="text-emerald">${sc.eficiencia_pct.toFixed(1)}%</span></td>
      <td><code>${sc.checksum}</code></td>
    `;
    tbody.appendChild(tr);
  });

  renderAllThreeMandatoryCharts(tSeq, cenarios);
}

function renderAllThreeMandatoryCharts(tSeq, cenarios) {
  if (typeof Chart === "undefined") return;

  const workersAxis = [1, 2, 4, 8];
  const labelsG1G2 = ["1 Worker", "2 Workers", "4 Workers", "8 Workers"];

  const seqTimes = workersAxis.map(() => tSeq);
  const procTimes = workersAxis.map(w => {
    const s = findScenario(cenarios, "host", "processos", w);
    return s ? s.media_geracao_s : tSeq;
  });
  const thrTimes = workersAxis.map(w => {
    const s = findScenario(cenarios, "host", "threads", w);
    return s ? s.media_geracao_s : tSeq;
  });

  const idealSpeedup = workersAxis.map(w => w);
  const procSpeedup = workersAxis.map(w => {
    const s = findScenario(cenarios, "host", "processos", w);
    return s ? s.speedup : 1.0;
  });
  const thrSpeedup = workersAxis.map(w => {
    const s = findScenario(cenarios, "host", "threads", w);
    return s ? s.speedup : 1.0;
  });

  // 1. GRÁFICO 1: TEMPO DE EXECUÇÃO (SÉRIES AGRUPADAS: SEQ, PROCESSOS, THREADS)
  const canvasTimes = document.getElementById("chart-times");
  if (canvasTimes) {
    if (chartTimesInstance) chartTimesInstance.destroy();
    chartTimesInstance = new Chart(canvasTimes.getContext("2d"), {
      type: "bar",
      data: {
        labels: labelsG1G2,
        datasets: [
          {
            label: "Sequencial (Baseline)",
            data: seqTimes,
            backgroundColor: "rgba(245, 158, 11, 0.85)",
            borderRadius: 4
          },
          {
            label: "Processos (fork + mmap)",
            data: procTimes,
            backgroundColor: "rgba(168, 85, 247, 0.85)",
            borderRadius: 4
          },
          {
            label: "Threads (std::thread)",
            data: thrTimes,
            backgroundColor: "rgba(14, 165, 233, 0.9)",
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { labels: { color: "#cbd5e1", font: { size: 11 } } }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Tempo (segundos)", color: "#94a3b8" },
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: { color: "#94a3b8" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#cbd5e1" }
          }
        }
      }
    });
  }

  // 2. GRÁFICO 2: SPEEDUP REAL VS. IDEAL LINEAR (LEI DE AMDAHL)
  const canvasSpeedup = document.getElementById("chart-speedup");
  if (canvasSpeedup) {
    if (chartSpeedupInstance) chartSpeedupInstance.destroy();
    chartSpeedupInstance = new Chart(canvasSpeedup.getContext("2d"), {
      type: "line",
      data: {
        labels: labelsG1G2,
        datasets: [
          {
            label: "Linear Ideal (y = P)",
            data: idealSpeedup,
            borderColor: "#64748b",
            borderDash: [6, 6],
            pointRadius: 4,
            tension: 0.1
          },
          {
            label: "Speedup Threads (std::thread)",
            data: thrSpeedup,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.2)",
            pointRadius: 5,
            borderWidth: 3,
            tension: 0.15
          },
          {
            label: "Speedup Processos (fork + mmap)",
            data: procSpeedup,
            borderColor: "#a855f7",
            backgroundColor: "rgba(168, 85, 247, 0.2)",
            pointRadius: 5,
            borderWidth: 3,
            tension: 0.15
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { labels: { color: "#cbd5e1", font: { size: 11 } } }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Speedup (Sp = T_seq / T_p)", color: "#94a3b8" },
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: { color: "#94a3b8" }
          },
          x: {
            grid: { color: "rgba(255, 255, 255, 0.04)" },
            ticks: { color: "#cbd5e1" }
          }
        }
      }
    });
  }

  // 3. GRÁFICO 3: HOST VS. DOCKER (--cpus="1", "2", "4") PARA 2, 4 E 8 WORKERS
  const canvasDocker = document.getElementById("chart-docker");
  if (canvasDocker) {
    if (chartDockerInstance) chartDockerInstance.destroy();
    const wDock = [2, 4, 8];
    const labelsG3 = ["2 Workers", "4 Workers", "8 Workers"];

    const getSeries = (amb, impl, cpus) =>
      wDock.map(w => {
        const s = findScenario(cenarios, amb, impl, w, cpus);
        return s ? s.media_geracao_s : 0;
      });

    chartDockerInstance = new Chart(canvasDocker.getContext("2d"), {
      type: "bar",
      data: {
        labels: labelsG3,
        datasets: [
          {
            label: 'Docker --cpus="1" (Threads - Contenção CFS)',
            data: getSeries("docker", "threads", "1"),
            backgroundColor: "rgba(239, 68, 68, 0.88)",
            borderRadius: 4
          },
          {
            label: 'Docker --cpus="1" (Processos - Contenção CFS)',
            data: getSeries("docker", "processos", "1"),
            backgroundColor: "rgba(249, 115, 22, 0.88)",
            borderRadius: 4
          },
          {
            label: 'Docker --cpus="2" (Threads)',
            data: getSeries("docker", "threads", "2"),
            backgroundColor: "rgba(234, 179, 8, 0.88)",
            borderRadius: 4
          },
          {
            label: 'Docker --cpus="2" (Processos)',
            data: getSeries("docker", "processos", "2"),
            backgroundColor: "rgba(236, 72, 153, 0.88)",
            borderRadius: 4
          },
          {
            label: 'Docker --cpus="4" (Threads)',
            data: getSeries("docker", "threads", "4"),
            backgroundColor: "rgba(59, 130, 246, 0.88)",
            borderRadius: 4
          },
          {
            label: 'Docker --cpus="4" (Processos)',
            data: getSeries("docker", "processos", "4"),
            backgroundColor: "rgba(6, 182, 212, 0.88)",
            borderRadius: 4
          },
          {
            label: "Host Físico Ilimitado (Processos)",
            data: getSeries("host", "processos", "ilimitado"),
            backgroundColor: "rgba(168, 85, 247, 0.88)",
            borderRadius: 4
          },
          {
            label: "Host Físico Ilimitado (Threads)",
            data: getSeries("host", "threads", "ilimitado"),
            backgroundColor: "rgba(16, 185, 129, 0.9)",
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { labels: { color: "#cbd5e1", font: { size: 11 } } }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Tempo de Execução (segundos)", color: "#94a3b8" },
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: { color: "#94a3b8" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#cbd5e1" }
          }
        }
      }
    });
  }
}

// Funções do Terminal (Aba 4)
function appendTerminalOutput(text) {
  const term = document.getElementById("terminal-stdout");
  if (term) {
    term.textContent = text;
  }
}

function clearTerminal() {
  const term = document.getElementById("terminal-stdout");
  if (term) {
    term.textContent = "$ Terminal limpo.\n";
  }
}

async function runQuickTerminalTest(paradigm, workers = 4, cpus_limit = "ilimitado") {
  const term = document.getElementById("terminal-stdout");
  term.textContent = `$ Executando ${paradigm} (${workers} workers, cpus=${cpus_limit})...\n`;

  const size = 10000000;
  const key = 84729;
  const password = "AvaliacaoSO2";

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paradigm, workers, cpus_limit, size, key, password })
    });
    const data = await res.json();
    term.textContent = `$ ${data.cmd_display}\n\n` + data.stdout;
  } catch (err) {
    term.textContent += `\nErro ao executar: ${err.message}`;
  }
}

async function runDiffEquivalenceTest() {
  const term = document.getElementById("terminal-stdout");
  term.textContent = "$ Executando validação cruzada diff entre ./sequencial/app, ./processos/app 4 e ./threads/app 4...\n";

  try {
    const res = await fetch("/api/diff_check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ size: 1000000, key: 84729, password: "AvaliacaoSO2" })
    });
    const data = await res.json();
    term.textContent = data.log;
  } catch (err) {
    term.textContent += `\nErro ao validar diff: ${err.message}`;
  }
}
