// Statewide Scalability Simulator (~80,000 Cameras) & Audit Log Controller

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
