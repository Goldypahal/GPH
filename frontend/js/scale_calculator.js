// Statewide Scalability Simulator (~80,000 Cameras), Stress Test & Audit Log Controller

async function updateScaleSimulation() {
  const slider = document.getElementById("scale-cam-slider");
  const count = slider ? parseInt(slider.value) : 80000;
  
  const camValLabel = document.getElementById("scale-cam-val");
  if (camValLabel) camValLabel.textContent = count.toLocaleString();

  const resSelect = document.getElementById("scale-res-select");
  const resolution = resSelect ? resSelect.value : "1080p";

  const retSelect = document.getElementById("scale-ret-select");
  const retention = retSelect ? parseInt(retSelect.value) : 30;

  try {
    const url = `/api/system/scale-calculator?camera_count=${count}&resolution=${resolution}&retention_days=${retention}&fps=25`;
    const res = await fetch(url);
    if (res.ok) {
      const sim = await res.json();

      document.getElementById("calc-central-bw").textContent = `${sim.central_model4_bandwidth_gbps.toLocaleString()} Gbps`;
      document.getElementById("calc-hybrid-bw").textContent = `${sim.hybrid_model_bandwidth_gbps.toLocaleString()} Gbps`;
      document.getElementById("calc-savings-pct").textContent = `${sim.bandwidth_savings_percentage}% Saved`;
      document.getElementById("calc-savings-cost").textContent = `₹${sim.estimated_annual_cost_savings_inr_crores} Cr`;
      document.getElementById("calc-storage-pb").textContent = `${sim.central_storage_petabytes} PB (Central) vs ${sim.hybrid_edge_storage_petabytes} PB (Edge Incident)`;
    }
  } catch (err) {
    console.error("Scale simulation error:", err);
  }
}

async function runLiveStressTest() {
  const btn = document.getElementById("btn-run-stress-test");
  const statusElem = document.getElementById("stress-test-status");
  const resultsCard = document.getElementById("stress-results-card");
  
  const slider = document.getElementById("scale-cam-slider");
  const camCount = slider ? parseInt(slider.value) : 10000;

  if (btn) {
    btn.disabled = true;
    btn.textContent = "⚡ Streaming Synthetic Batch Load...";
  }
  if (statusElem) {
    statusElem.style.display = "block";
    statusElem.innerHTML = `<span style="color:var(--accent-cyan);">Testing high-concurrency partitioned Kafka ingestion (${camCount.toLocaleString()} devices)...</span>`;
  }

  try {
    const res = await fetch("/api/system/scale-benchmark/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ camera_count: camCount, batch_size: 500, max_events: 10000 })
    });

    if (res.ok) {
      const data = await res.json();
      if (resultsCard) resultsCard.style.display = "grid";
      
      const tputElem = document.getElementById("stress-tput");
      if (tputElem) tputElem.textContent = `${data.throughput_events_per_sec.toLocaleString()} MPS`;

      const latElem = document.getElementById("stress-lat");
      if (latElem) latElem.textContent = `${data.latency_p95_ms} ms`;

      const durElem = document.getElementById("stress-dur");
      if (durElem) durElem.textContent = `${data.events_accepted.toLocaleString()} / ${data.total_events_generated.toLocaleString()}`;

      const lossElem = document.getElementById("stress-loss");
      if (lossElem) lossElem.textContent = `${data.packet_loss_percentage}%`;

      const noteElem = document.getElementById("stress-methodology-note");
      if (noteElem) {
        noteElem.style.display = "block";
        noteElem.innerHTML = `
          <div><strong>Engine:</strong> ${data.execution_engine}</div>
          <div><strong>Benchmark Type:</strong> ${data.benchmark_type} (Git: ${data.git_commit})</div>
          <div><strong>Host Env:</strong> ${data.environment.os || 'N/A'}, Python ${data.environment.python}, ${data.environment.cpu_logical_cores} Cores, ${data.environment.system_ram_gb} GB RAM</div>
          <div style="margin-top:4px; color:#cbd5e1;"><em>${data.methodology_disclaimer}</em></div>
        `;
      }

      if (statusElem) {
        statusElem.innerHTML = `<span style="color:#34d399; font-weight:bold;">✔ TEST COMPLETE: Processed ${data.events_accepted.toLocaleString()} events (80K Modeled Sizing → ${data.events_accepted.toLocaleString()}-event application execution sample) at ${data.throughput_events_per_sec.toLocaleString()} MPS. Real per-event p95 latency: ${data.latency_p95_ms}ms.</span>`;
      }
    } else {
      if (statusElem) statusElem.innerHTML = `<span style="color:#ef4444;">Stress test failed with HTTP ${res.status}</span>`;
    }
  } catch (err) {
    console.error("Stress test error:", err);
    if (statusElem) statusElem.innerHTML = `<span style="color:#ef4444;">Network error running benchmark</span>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "⚡ Run Benchmark";
    }
  }
}

async function viewAuditTrail() {
  openModal("audit-modal");
  const container = document.getElementById("audit-table-content");
  container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--accent-cyan);">Fetching tamper-evident cryptographic audit trail...</div>`;

  try {
    const res = await fetch("/api/evidence/audit-logs");
    if (res.ok) {
      const logs = await res.json();
      container.innerHTML = `
        <table class="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Officer / Identity</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Cryptographic Hash</th>
            </tr>
          </thead>
          <tbody>
            ${logs.map(l => `
              <tr>
                <td style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-dim);">
                  ${new Date(l.timestamp).toLocaleString("en-IN")}
                </td>
                <td style="font-weight:600; color:#fff;">${l.user_id}</td>
                <td><span class="quick-tag-btn" style="font-size:0.68rem;">${l.action}</span></td>
                <td style="font-family:var(--font-mono); font-size:0.75rem;">${l.resource}</td>
                <td style="font-family:var(--font-mono); font-size:0.7rem; color:var(--accent-cyan);">
                  ${l.signature_hash ? l.signature_hash.slice(0, 16) + '...' : 'SEALED'}
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }
  } catch (err) {
    console.error("Failed to load audit logs:", err);
  }
}
