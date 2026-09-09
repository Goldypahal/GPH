// Designated Vehicle Search & Movement Journey Reconstructor
let currentTrajectoryData = null;

async function executeVehicleSearch() {
  const inputEl = document.getElementById("vehicle-search-input");
  const plate = inputEl ? inputEl.value.trim() : "GJ01AB1234";

  if (!plate) {
    alert("Please enter a valid vehicle registration plate number.");
    return;
  }

  const nodesContainer = document.getElementById("journey-nodes-list");
  nodesContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--accent-cyan); font-family:var(--font-mono);">
    <span>⚡ Correlating video events across 50 statewide cameras...</span>
  </div>`;

  try {
    const res = await fetch(`/api/tracking/search?plate=${encodeURIComponent(plate)}`);
    if (!res.ok) {
      const err = await res.json();
      nodesContainer.innerHTML = `<div style="text-align:center; padding:30px; color:#ef4444;">
        ⚠️ ${err.detail || "No sightings found for this vehicle."}
      </div>`;
      document.getElementById("journey-summary-panel").style.display = "none";
      return;
    }

    const data = await res.json();
    currentTrajectoryData = data;
    renderJourneyResults(data);

  } catch (err) {
    console.error("Vehicle search failed:", err);
    nodesContainer.innerHTML = `<div style="text-align:center; padding:30px; color:#ef4444;">Error communicating with intelligence server.</div>`;
  }
}

function quickSearchVehicle(plate) {
  const inputEl = document.getElementById("vehicle-search-input");
  if (inputEl) inputEl.value = plate;
  executeVehicleSearch();
}

function renderJourneyResults(data) {
  const summaryPanel = document.getElementById("journey-summary-panel");
  summaryPanel.style.display = "block";

  // Update Summary Banner
  document.getElementById("sum-plate").textContent = data.plate_number;
  document.getElementById("sum-sightings").textContent = data.total_sightings;
  document.getElementById("sum-distance").textContent = `${data.total_estimated_distance_km} km`;
  document.getElementById("sum-speed").textContent = `${data.average_speed_kmh} km/h`;

  const riskBadge = document.getElementById("sum-risk-badge");
  const descEl = document.getElementById("sum-desc");

  if (data.matched_watchlist) {
    const wl = data.matched_watchlist;
    riskBadge.className = `alert-risk-badge risk-${wl.risk_level}-badge`;
    riskBadge.textContent = `${wl.risk_level} HOTLIST HIT`;
    descEl.innerHTML = `CRIME REGISTER: ${wl.reason} [${wl.case_fir_number}] | Registered by ${wl.registered_authority}` +
      (data.route_confidence_pct ? ` | Route Confidence: <strong style="color:#38bdf8;">${data.route_confidence_pct}% (${data.route_status || 'VERIFIED'})</strong>` : '');
  } else {
    riskBadge.className = "alert-risk-badge";
    riskBadge.style.background = "#10b981";
    riskBadge.textContent = "NORMAL TRANSIT";
    descEl.innerHTML = `Vehicle movement correlated across ${data.districts_traversed.join(", ")} without active police hotlist restrictions.` +
      (data.route_confidence_pct ? ` | Route Confidence: <strong style="color:#10b981;">${data.route_confidence_pct}% (${data.route_status || 'VERIFIED'})</strong>` : '');
  }

  // Render Chronological Timeline Nodes
  const nodesContainer = document.getElementById("journey-nodes-list");
  nodesContainer.innerHTML = `
    <div class="journey-timeline-container">
      ${data.trajectory.map(pt => {
        const timeFormatted = new Date(pt.timestamp).toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        const dateFormatted = new Date(pt.timestamp).toLocaleDateString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric"
        });

        return `
          <div class="journey-node-card">
            <div class="node-step-circle">#${pt.sequence}</div>
            
            <div class="node-details">
              <div class="node-loc-name">${pt.location_name}</div>
              <div class="node-district-tag">${pt.district} District | ${pt.camera_name}</div>
              <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
                Confidence: ${(pt.confidence * 100).toFixed(1)}% | Estimated Speed: <strong>${pt.speed_kmh} km/h</strong>
                ${pt.match_method ? ` | <span style="color:#38bdf8; font-weight:600;">[${pt.match_method}]</span>` : ''}
                ${pt.distance_km ? ` | Segment: +${pt.distance_km} km (${pt.time_delta_mins} mins)` : ''}
                ${pt.link_status === 'IMPOSSIBLE_SPEED' ? ` | <span style="color:#ef4444; font-weight:bold;">⚠️ IMPOSSIBLE SPEED ANOMALY</span>` : ''}
              </div>
            </div>

            <div style="text-align:right;">
              <div class="node-time-stat">${timeFormatted}</div>
              <div style="font-size:0.7rem; color:var(--text-dim);">${dateFormatted}</div>
            </div>

            <div style="text-align:right;">
              <button class="quick-tag-btn" style="background:rgba(14,165,233,0.15); color:var(--accent-cyan); border-color:rgba(14,165,233,0.4);" onclick="openSection65BCertificate('${pt.camera_id}')">
                📜 Sec 65B
              </button>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function showJourneyOnMap() {
  if (!currentTrajectoryData || !currentTrajectoryData.trajectory) {
    alert("Please track a vehicle first.");
    return;
  }

  // Switch to GIS view tab
  const tabGis = document.getElementById("tab-gis");
  if (tabGis) tabGis.click();

  setTimeout(() => {
    if (window.drawTrajectoryOnMap) {
      window.drawTrajectoryOnMap(currentTrajectoryData.trajectory);
    }
  }, 300);
}
