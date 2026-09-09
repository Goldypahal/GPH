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

        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:6px; border-top:1px solid rgba(255,255,255,0.08); padding-top:6px;">
          <button class="quick-tag-btn" onclick="openVehicleJourney('${a.plate_text}')">Trace Route</button>
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
