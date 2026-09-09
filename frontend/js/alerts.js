// Real-time Watchlist & Alert Engine Controller
let activeAlertsList = [];

window.loadAlerts = async function() {
  const container = document.getElementById("alert-items-container");
  if (!container) return;

  try {
    const res = await fetch("/api/alerts");
    if (res.ok) {
      activeAlertsList = await res.json();
      renderAlerts(activeAlertsList);
      updateAlertBadges(activeAlertsList);
    }
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
};

function renderAlerts(alerts) {
  const container = document.getElementById("alert-items-container");
  if (!container) return;

  if (alerts.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">No active alarms reported.</div>`;
    return;
  }

  container.innerHTML = alerts.map(a => {
    const timeStr = new Date(a.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    const isNew = a.status === "NEW";

    return `
      <div class="alert-item-card risk-${a.risk_level}">
        <div class="alert-top">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="alert-plate">${a.plate_text}</span>
            <span class="alert-risk-badge risk-${a.risk_level}-badge">${a.risk_level}</span>
            ${isNew ? '<span style="background:#ff0055; color:#fff; font-size:0.62rem; padding:1px 5px; border-radius:3px; font-weight:bold;">NEW</span>' : ''}
          </div>
          <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-dim);">${timeStr}</span>
        </div>

        <div class="alert-desc">
          <strong>${a.camera_name || 'Checkpoint Camera'}</strong> (${a.district || 'Gujarat'})
          <div style="margin-top:2px; font-size:0.75rem; color:#cbd5e1;">${a.remarks || ''}</div>
        </div>

        <div class="alert-meta">
          <span>UID: ${a.alert_uid}</span>
          <span>Status: <strong style="color:${a.status === 'NEW' ? '#f87171' : '#34d399'}">${a.status}</strong></span>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:6px; border-top:1px solid rgba(255,255,255,0.08); padding-top:6px; flex-wrap:wrap;">
          <button class="quick-tag-btn" onclick="openVehicleJourney('${a.plate_text}')">Trace Route</button>
          <button class="quick-tag-btn" style="background:#1e293b; color:#38bdf8;" onclick="openGovIntelModal('${a.plate_text}')">🏛️ Gov Intel</button>
          <button class="quick-tag-btn" style="background:#0f172a; color:#f59e0b;" onclick="createCaseAndDownloadEvidence('${a.id}')">📂 Case & ZIP</button>
          ${isNew ? `
            <button class="quick-tag-btn" style="background:#0ea5e9; color:#000; font-weight:bold;" onclick="acknowledgeAlert('${a.id}')">
              ⚡ Acknowledge & Dispatch
            </button>
          ` : `
            <button class="quick-tag-btn" style="color:#34d399;" disabled>Dispatched (${a.dispatched_unit || 'Unit Active'})</button>
          `}
        </div>
      </div>
    `;
  }).join("");
}

function updateAlertBadges(alerts) {
  const newCount = alerts.filter(a => a.status === "NEW").length;
  const badge = document.getElementById("alert-counter-badge");
  const statBadge = document.getElementById("stat-active-alerts");

  if (badge) badge.textContent = newCount;
  if (statBadge) statBadge.textContent = alerts.length;
}

async function acknowledgeAlert(alertId) {
  const pcrUnit = prompt("Enter Police Patrol / Interceptor Unit for Dispatch:", "PCR Interceptor 04 - Highway Rapid Response");
  if (!pcrUnit) return;

  try {
    const res = await fetch(`/api/alerts/${alertId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "INVESTIGATING",
        dispatched_unit: pcrUnit,
        remarks: "Patrol dispatched for immediate visual intercept.",
        operator_name: "Inspector V. Patel (C4I Netram)"
      })
    });

    if (res.ok) {
      alert(`Alert dispatched to ${pcrUnit}! Status updated to INVESTIGATING.`);
      loadAlerts();
    }
  } catch (err) {
    console.error("Failed to acknowledge alert:", err);
  }
}

async function triggerSimulatedAlert() {
  playAlarmChime();
  try {
    const res = await fetch("/api/alerts/simulate?plate=GJ01AB1234&camera_code=CAM-GJ-VLS-01", {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      const tickerText = document.getElementById("ticker-alert-text");
      if (tickerText) {
        tickerText.textContent = `[${data.alert_uid}] SIMULATED ALARM: ${data.plate} intercepted at ${data.camera} (${data.district})!`;
      }
      loadAlerts();
    }
  } catch (err) {
    console.error("Alert simulation error:", err);
  }
}

function playAlarmChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {
    // AudioContext blocked until user gesture
  }
}

async function openGovIntelModal(plate) {
  openModal("gov-intel-modal");
  const container = document.getElementById("gov-intel-content");
  container.innerHTML = `<div style="text-align:center; padding:30px; color:var(--accent-cyan);">⚡ Querying National & State Registries (VAHAN, SARTHI, eGujCop, AFIS) for ${plate}...</div>`;

  try {
    const res = await fetch(`/api/system/gov/intel-bundle/${plate}`);
    if (!res.ok) {
      container.innerHTML = `<div style="color:#ef4444; padding:20px; text-align:center;">Failed to retrieve government intelligence (HTTP ${res.status})</div>`;
      return;
    }
    const data = await res.json();
    const isCritical = data.composite_risk_score >= 80;
    const isHigh = data.composite_risk_score >= 50;
    const badgeColor = isCritical ? '#ef4444' : (isHigh ? '#f59e0b' : '#34d399');

    container.innerHTML = `
      <div style="background:#0b1329; border:1px solid var(--border-color); border-radius:10px; padding:16px; margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
          <div>
            <div style="font-size:1.3rem; font-weight:800; font-family:var(--font-mono); color:#fff;">${data.normalized_plate}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Source Signature: <span style="font-family:var(--font-mono); color:var(--accent-cyan);">${data.composite_signature_hash.slice(0, 24)}...</span></div>
          </div>
          <div style="text-align:right;">
            <div style="background:${badgeColor}; color:#000; font-weight:bold; padding:4px 12px; border-radius:20px; font-size:0.85rem; display:inline-block;">
              RISK: ${data.composite_risk_score}/100 • ${data.threat_assessment}
            </div>
          </div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
        <!-- VAHAN Panel -->
        <div style="background:#080d18; border:1px solid var(--border-color); border-radius:8px; padding:14px;">
          <div style="font-weight:bold; color:var(--accent-cyan); margin-bottom:8px; display:flex; justify-content:space-between;">
            <span>🚗 VAHAN 4.0 (MoRTH)</span>
            <span style="font-size:0.7rem; color:${data.vahan_record.stolen_vehicle_alert ? '#ef4444' : '#34d399'};">
              ${data.vahan_record.stolen_vehicle_alert ? '🚨 STOLEN' : '✔ CLEAR'}
            </span>
          </div>
          <div style="font-size:0.8rem; line-height:1.6; color:#cbd5e1;">
            <div><strong>Owner:</strong> ${data.vahan_record.owner_name}</div>
            <div><strong>Vehicle:</strong> ${data.vahan_record.make_model} (${data.vahan_record.vehicle_class})</div>
            <div><strong>RTO:</strong> ${data.vahan_record.registering_authority}</div>
            <div><strong>Chassis:</strong> <span style="font-family:var(--font-mono); font-size:0.75rem;">${data.vahan_record.chassis_number}</span></div>
          </div>
        </div>

        <!-- eGujCop / CCTNS Panel -->
        <div style="background:#080d18; border:1px solid var(--border-color); border-radius:8px; padding:14px;">
          <div style="font-weight:bold; color:var(--accent-red); margin-bottom:8px; display:flex; justify-content:space-between;">
            <span>🛡️ eGujCop / CCTNS Crime Records</span>
            <span style="font-size:0.7rem; color:${data.egujcop_record.active_lookout_notice ? '#ef4444' : '#34d399'};">
              ${data.egujcop_record.active_lookout_notice ? '🚨 ACTIVE LOOKOUT' : '✔ NO WARRANT'}
            </span>
          </div>
          <div style="font-size:0.8rem; line-height:1.6; color:#cbd5e1;">
            <div><strong>Warrants:</strong> ${data.egujcop_record.warrant_status}</div>
            <div><strong>Criminal History:</strong> ${data.egujcop_record.fir_history ? data.egujcop_record.fir_history.join(", ") : "None"}</div>
            <div><strong>Flag:</strong> ${data.egujcop_record.stolen_vehicle_record ? "Reported Stolen" : "Clear"}</div>
            <div><strong>Court Ref:</strong> <span style="font-family:var(--font-mono); font-size:0.75rem;">CR-2026/AHM-SEC120B</span></div>
          </div>
        </div>

        <!-- SARTHI DL Panel -->
        <div style="background:#080d18; border:1px solid var(--border-color); border-radius:8px; padding:14px;">
          <div style="font-weight:bold; color:var(--accent-amber); margin-bottom:8px;">🪪 SARTHI (Driver License)</div>
          <div style="font-size:0.8rem; line-height:1.6; color:#cbd5e1;">
            <div><strong>License No:</strong> <span style="font-family:var(--font-mono);">${data.sarathi_record.license_number}</span></div>
            <div><strong>Holder:</strong> ${data.sarathi_record.driver_name}</div>
            <div><strong>Status:</strong> <span style="color:${data.sarathi_record.license_status === 'VALID' ? '#34d399' : '#ef4444'};">${data.sarathi_record.license_status}</span></div>
            <div><strong>Disqualified:</strong> ${data.sarathi_record.disqualified ? "YES" : "No"}</div>
          </div>
        </div>

        <!-- AFIS Biometrics Panel -->
        <div style="background:#080d18; border:1px solid var(--border-color); border-radius:8px; padding:14px;">
          <div style="font-weight:bold; color:#a855f7; margin-bottom:8px;">🧬 AFIS / NAFIS Biometrics</div>
          <div style="font-size:0.8rem; line-height:1.6; color:#cbd5e1;">
            <div><strong>Biometric Match:</strong> <span style="color:${data.afis_record.match_found ? '#ef4444' : '#34d399'}; font-weight:bold;">${data.afis_record.match_found ? 'MATCH FOUND' : 'NO RECORD'}</span></div>
            <div><strong>Suspect:</strong> ${data.afis_record.suspect_name || 'N/A'}</div>
            <div><strong>Confidence:</strong> ${data.afis_record.match_confidence ? (data.afis_record.match_confidence * 100).toFixed(1) + '%' : 'N/A'}</div>
            <div><strong>Known Alias:</strong> ${data.afis_record.known_aliases ? data.afis_record.known_aliases.join(", ") : "None"}</div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Gov intel modal error:", err);
    container.innerHTML = `<div style="color:#ef4444; padding:20px; text-align:center;">Network error querying government registries</div>`;
  }
}

async function createCaseAndDownloadEvidence(alertId) {
  const confirmCreate = confirm("Initialize official Gujarat Police investigation case from this alert and download Court-Admissible Section 65B Evidence ZIP Bundle?");
  if (!confirmCreate) return;

  try {
    // 1. Create case from alert
    const res = await fetch(`/api/cases/from-alert/${alertId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Automated Investigation Docket",
        assigned_investigator: "Inspector V. Patel (C4I Netram)",
        priority: "HIGH"
      })
    });

    if (!res.ok) {
      alert(`Failed to initialize case: HTTP ${res.status}`);
      return;
    }

    const caseData = await res.json();
    alert(`Case ${caseData.case_number} created successfully! Downloading Section 65B Evidence ZIP Bundle...`);

    // 2. Trigger download of ZIP bundle
    window.location.href = `/api/cases/${caseData.id}/evidence-bundle`;
  } catch (err) {
    console.error("Case creation error:", err);
    alert("Error creating case docket and exporting evidence bundle.");
  }
}
