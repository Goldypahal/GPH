// Real-time Watchlist & Alert Engine Controller — Production Dispatch Workflow
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
    container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted);">No active alarms reported across statewide network.</div>`;
    return;
  }

  container.innerHTML = alerts.map(a => {
    const timeStr = new Date(a.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const isNew = a.status === "NEW";

    return `
      <div class="alert-item-card risk-${a.risk_level}">
        <div class="alert-top">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="alert-plate">${a.plate_text}</span>
            <span class="alert-risk-badge risk-${a.risk_level}-badge">${a.risk_level}</span>
            ${isNew ? '<span style="background:#ef4444; color:#fff; font-size:0.62rem; padding:1px 6px; border-radius:3px; font-weight:800; letter-spacing:0.5px;">NEW</span>' : ''}
          </div>
          <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-dim);">${timeStr}</span>
        </div>

        <div class="alert-desc">
          <strong>${a.camera_name || 'Checkpoint Camera'}</strong> (${a.district || 'Gujarat'})
          <div style="margin-top:4px; font-size:0.76rem; color:var(--text-muted);">${a.remarks || 'Automated ANPR Watchlist Match'}</div>
        </div>

        <div class="alert-meta">
          <span>UID: <strong>${a.alert_uid}</strong></span>
          <span>Status: <strong style="color:${a.status === 'NEW' ? 'var(--accent-red)' : 'var(--accent-green)'}">${a.status}</strong></span>
        </div>

        <div class="alert-actions">
          <button class="quick-tag-btn" onclick="openVehicleJourney('${a.plate_text}')" title="Trace Route">
            <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <span>Reconstruct Route</span>
          </button>
          <button class="quick-tag-btn" onclick="openGovIntelModal('${a.plate_text}')" title="National Intelligence Dossier">
            <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
            <span>National Dossier</span>
          </button>
          <button class="quick-tag-btn" onclick="createCaseAndDownloadEvidence('${a.id}')" title="Create Case & Export ZIP">
            <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            <span>Case &amp; ZIP</span>
          </button>
          ${isNew ? `
            <button class="primary-search-btn" style="background:var(--accent-red); border-color:#b91c1c; padding:4px 12px; font-size:0.75rem;" onclick="openDispatchModal('${a.id}')">
              <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
              <span>Dispatch Unit</span>
            </button>
          ` : `
            <span class="quick-tag-btn" style="color:var(--accent-green); background:rgba(16,185,129,0.1); border-color:rgba(16,185,129,0.3);">
              ✓ Dispatched (${a.dispatched_unit || 'Unit Active'})
            </span>
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

// ==========================================================================
// IN-APP PATROL DISPATCH MODAL (NO WINDOW.PROMPT)
// ==========================================================================
window.openDispatchModal = function(alertId) {
  const alertObj = activeAlertsList.find(a => String(a.id) === String(alertId));
  if (!alertObj) return;

  document.getElementById("dispatch-alert-id").value = alertId;
  document.getElementById("dispatch-plate-text").textContent = alertObj.plate_text;
  
  const riskBadge = document.getElementById("dispatch-risk-text");
  if (riskBadge) {
    riskBadge.textContent = alertObj.risk_level;
    riskBadge.className = `alert-risk-badge risk-${alertObj.risk_level}-badge`;
  }

  const locText = document.getElementById("dispatch-location-text");
  if (locText) {
    locText.textContent = `${alertObj.camera_name || 'Checkpoint'} (${alertObj.district || 'Gujarat'})`;
  }

  // Reset custom unit wrap
  const customWrap = document.getElementById("dispatch-custom-unit-wrap");
  if (customWrap) customWrap.style.display = "none";
  const unitSelect = document.getElementById("dispatch-unit-select");
  if (unitSelect) unitSelect.value = "PCR Interceptor 12 - Highway Rapid Response";

  openModal("dispatch-modal");
};

window.handleUnitSelectChange = function(val) {
  const customWrap = document.getElementById("dispatch-custom-unit-wrap");
  if (customWrap) {
    customWrap.style.display = val === "CUSTOM" ? "block" : "none";
    if (val === "CUSTOM") {
      document.getElementById("dispatch-custom-unit-input").focus();
    }
  }
};

window.submitDispatchAction = async function(event) {
  event.preventDefault();
  const alertId = document.getElementById("dispatch-alert-id").value;
  let pcrUnit = document.getElementById("dispatch-unit-select").value;
  if (pcrUnit === "CUSTOM") {
    pcrUnit = document.getElementById("dispatch-custom-unit-input").value.trim() || "PCR Interceptor Special Unit";
  }

  const operator = document.getElementById("dispatch-operator-input").value.trim();
  const remarks = document.getElementById("dispatch-remarks-input").value.trim();

  try {
    const res = await fetch(`/api/alerts/${alertId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "INVESTIGATING",
        dispatched_unit: pcrUnit,
        remarks: remarks,
        operator_name: operator
      })
    });

    if (res.ok) {
      closeModal("dispatch-modal");
      if (window.showToast) {
        window.showToast("INTERCEPTOR DISPATCHED", `Target dispatched to ${pcrUnit}. Status updated to INVESTIGATING.`, "success");
      }
      loadAlerts();
    } else {
      const err = await res.json();
      if (window.showToast) {
        window.showToast("DISPATCH ERROR", err.detail || "Failed to transmit dispatch orders.", "CRITICAL");
      }
    }
  } catch (err) {
    console.error("Failed to acknowledge alert:", err);
    if (window.showToast) {
      window.showToast("NETWORK ERROR", "Unable to connect to dispatch broker.", "CRITICAL");
    }
  }
};

// ==========================================================================
// SIMULATED ALERT TRIGGER
// ==========================================================================
window.triggerSimulatedAlert = async function() {
  playAlarmChime();
  try {
    const res = await fetch("/api/alerts/simulate?plate=GJ01AB1234&camera_code=CAM-GJ-VLS-01", {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      const tickerText = document.getElementById("ticker-alert-text");
      if (tickerText) {
        tickerText.textContent = `[${data.alert_uid}] PRIORITY HIT: ${data.plate} intercepted at ${data.camera} (${data.district})!`;
      }
      if (window.showToast) {
        window.showToast("SIMULATED HOTLIST HIT", `${data.plate} detected at ${data.camera}. Red alert dispatched.`, "CRITICAL");
      }
      loadAlerts();
    }
  } catch (err) {
    console.error("Alert simulation error:", err);
  }
};

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
    // AudioContext requires interaction on some browsers
  }
}

// ==========================================================================
// NATIONAL INTELLIGENCE DOSSIER (VAHAN, SARTHI, eGujCop, AFIS)
// ==========================================================================
window.openGovIntelModal = async function(plate) {
  openModal("gov-intel-modal");
  const container = document.getElementById("gov-intel-content");
  container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--accent-cyan); font-family:var(--font-mono);">Querying National & State Registries (VAHAN, SARTHI, eGujCop, AFIS) for ${plate}...</div>`;

  try {
    const res = await fetch(`/api/system/gov/intel-bundle/${plate}`);
    if (!res.ok) {
      container.innerHTML = `<div style="color:var(--accent-red); padding:30px; text-align:center;">Failed to retrieve government intelligence (HTTP ${res.status})</div>`;
      return;
    }
    const data = await res.json();
    const isCritical = data.composite_risk_score >= 80;
    const isHigh = data.composite_risk_score >= 50;
    const badgeColor = isCritical ? 'var(--accent-red)' : (isHigh ? 'var(--accent-amber)' : 'var(--accent-green)');

    container.innerHTML = `
      <div class="sub-panel-card" style="margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="font-size:1.4rem; font-weight:800; font-family:var(--font-mono); color:var(--text-main);">${data.normalized_plate}</div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Source Signature: <span style="font-family:var(--font-mono); color:var(--accent-cyan);">${data.composite_signature_hash.slice(0, 24)}...</span></div>
          </div>
          <div style="text-align:right;">
            <div style="background:${badgeColor}; color:#fff; font-weight:800; padding:6px 14px; border-radius:var(--radius-sm); font-size:0.88rem; display:inline-block; letter-spacing:0.5px;">
              COMPOSITE THREAT: ${data.composite_risk_score}/100 • ${data.threat_assessment}
            </div>
          </div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
        <!-- VAHAN Panel -->
        <div class="sub-panel-card">
          <div style="font-weight:700; color:var(--accent-cyan); margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
            <span style="display:inline-flex; align-items:center; gap:6px;">
              <svg class="ui-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
              <span>VAHAN 4.0 (MoRTH)</span>
            </span>
            <span style="font-size:0.7rem; font-weight:bold; color:${data.vahan_record.stolen_vehicle_alert ? 'var(--accent-red)' : 'var(--accent-green)'};">
              ${data.vahan_record.stolen_vehicle_alert ? '[STOLEN ALERT]' : '[CLEAR]'}
            </span>
          </div>
          <div style="font-size:0.82rem; line-height:1.7; color:var(--text-muted);">
            <div><strong style="color:var(--text-main);">Owner:</strong> ${data.vahan_record.owner_name}</div>
            <div><strong style="color:var(--text-main);">Vehicle:</strong> ${data.vahan_record.make_model} (${data.vahan_record.vehicle_class})</div>
            <div><strong style="color:var(--text-main);">Registering RTO:</strong> ${data.vahan_record.registering_authority}</div>
            <div><strong style="color:var(--text-main);">Chassis No:</strong> <span style="font-family:var(--font-mono); font-size:0.75rem;">${data.vahan_record.chassis_number}</span></div>
          </div>
        </div>

        <!-- eGujCop / CCTNS Panel -->
        <div class="sub-panel-card">
          <div style="font-weight:700; color:var(--accent-red); margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
            <span style="display:inline-flex; align-items:center; gap:6px;">
              <svg class="ui-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
              <span>eGujCop / CCTNS Crime Records</span>
            </span>
            <span style="font-size:0.7rem; font-weight:bold; color:${data.egujcop_record.active_lookout_notice ? 'var(--accent-red)' : 'var(--accent-green)'};">
              ${data.egujcop_record.active_lookout_notice ? '[ACTIVE LOOKOUT]' : '[NO ACTIVE WARRANT]'}
            </span>
          </div>
          <div style="font-size:0.82rem; line-height:1.7; color:var(--text-muted);">
            <div><strong style="color:var(--text-main);">Warrants:</strong> ${data.egujcop_record.warrant_status}</div>
            <div><strong style="color:var(--text-main);">FIR History:</strong> ${data.egujcop_record.fir_history ? data.egujcop_record.fir_history.join(", ") : "None Recorded"}</div>
            <div><strong style="color:var(--text-main);">Stolen Vehicle Record:</strong> ${data.egujcop_record.stolen_vehicle_record ? "Confirmed Stolen" : "Clear"}</div>
            <div><strong style="color:var(--text-main);">Court Case Ref:</strong> <span style="font-family:var(--font-mono); font-size:0.75rem;">CR-2026/AHM-SEC120B</span></div>
          </div>
        </div>

        <!-- SARTHI DL Panel -->
        <div class="sub-panel-card">
          <div style="font-weight:700; color:var(--accent-amber); margin-bottom:10px; display:inline-flex; align-items:center; gap:6px;">
            <svg class="ui-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
            <span>SARTHI (Driver License Record)</span>
          </div>
          <div style="font-size:0.82rem; line-height:1.7; color:var(--text-muted);">
            <div><strong style="color:var(--text-main);">License No:</strong> <span style="font-family:var(--font-mono);">${data.sarathi_record.license_number}</span></div>
            <div><strong style="color:var(--text-main);">Holder Name:</strong> ${data.sarathi_record.driver_name}</div>
            <div><strong style="color:var(--text-main);">License Status:</strong> <span style="color:${data.sarathi_record.license_status === 'VALID' ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight:700;">${data.sarathi_record.license_status}</span></div>
            <div><strong style="color:var(--text-main);">Disqualified Driver:</strong> ${data.sarathi_record.disqualified ? "YES (Revoked)" : "No"}</div>
          </div>
        </div>

        <!-- AFIS Biometrics Panel -->
        <div class="sub-panel-card">
          <div style="font-weight:700; color:var(--accent-cyan); margin-bottom:10px; display:inline-flex; align-items:center; gap:6px;">
            <svg class="ui-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12h20M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2"></path></svg>
            <span>AFIS / NAFIS Biometrics</span>
          </div>
          <div style="font-size:0.82rem; line-height:1.7; color:var(--text-muted);">
            <div><strong style="color:var(--text-main);">Biometric Match:</strong> <span style="color:${data.afis_record.match_found ? 'var(--accent-red)' : 'var(--accent-green)'}; font-weight:700;">${data.afis_record.match_found ? 'MATCH FOUND' : 'NO RECORD'}</span></div>
            <div><strong style="color:var(--text-main);">Suspect Identified:</strong> ${data.afis_record.suspect_name || 'N/A'}</div>
            <div><strong style="color:var(--text-main);">Match Confidence:</strong> ${data.afis_record.match_confidence ? (data.afis_record.match_confidence * 100).toFixed(1) + '%' : 'N/A'}</div>
            <div><strong style="color:var(--text-main);">Known Aliases:</strong> ${data.afis_record.known_aliases ? data.afis_record.known_aliases.join(", ") : "None"}</div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Gov intel modal error:", err);
    container.innerHTML = `<div style="color:var(--accent-red); padding:30px; text-align:center;">Network error querying government registries</div>`;
  }
};

// ==========================================================================
// CASE CREATION & SECTION 65B EVIDENCE ZIP EXPORT
// ==========================================================================
window.createCaseAndDownloadEvidence = async function(alertId) {
  try {
    if (window.showToast) {
      window.showToast("INITIALIZING CASE DOCKET", "Creating investigation case record and packaging digital evidence bundle...", "info");
    }

    const res = await fetch(`/api/cases/from-alert/${alertId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Automated Surveillance Intercept Docket",
        assigned_investigator: "Inspector V. Patel (C4I Netram)",
        priority: "HIGH"
      })
    });

    if (!res.ok) {
      if (window.showToast) {
        window.showToast("CASE CREATION FAILED", `HTTP ${res.status}: Failed to create case docket.`, "CRITICAL");
      }
      return;
    }

    const caseData = await res.json();
    if (window.showToast) {
      window.showToast("CASE DOCKET READY", `Case #${caseData.case_number} created. Downloading Section 65B Evidence ZIP...`, "success");
    }

    // Trigger download of ZIP bundle
    window.location.href = `/api/cases/${caseData.id}/evidence-bundle`;
  } catch (err) {
    console.error("Case creation error:", err);
    if (window.showToast) {
      window.showToast("EXPORT ERROR", "Error exporting Section 65B evidence bundle.", "CRITICAL");
    }
  }
};
