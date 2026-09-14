// Designated Vehicle Search & Movement Journey Reconstructor — Dual-Pane Synchronized Console
let currentTrajectoryData = null;
let tracerRouteMap = null;
let tracerRouteTileLayer = null;
let tracerTrajectoryLayer = null;
let tracerVehicleMarker = null;

document.addEventListener("DOMContentLoaded", () => {
  // Initialize embedded tracer map when DOM is ready
  setTimeout(() => {
    initTracerRouteMap();
  }, 400);
});

function initTracerRouteMap() {
  const container = document.getElementById("tracer-route-map");
  if (!container || tracerRouteMap) return;

  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  const tileUrl = currentTheme === "dark" 
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  tracerRouteMap = L.map("tracer-route-map", {
    center: [22.45, 71.60],
    zoom: 7,
    zoomControl: true,
    minZoom: 6,
    maxZoom: 18
  });
  window.tracerRouteMap = tracerRouteMap;

  tracerRouteTileLayer = L.tileLayer(tileUrl, {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> | Gujarat Police GIVIN',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(tracerRouteMap);
}

// Support theme changes on the tracer map
window.updateTracerMapTheme = function(theme) {
  if (!tracerRouteMap) return;
  if (tracerRouteTileLayer) {
    tracerRouteMap.removeLayer(tracerRouteTileLayer);
  }
  const tileUrl = theme === "dark" 
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  tracerRouteTileLayer = L.tileLayer(tileUrl, {
    attribution: '&copy; CARTO | Gujarat Police GIVIN',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(tracerRouteMap);
};

// ==========================================================================
// VEHICLE SEARCH EXECUTION
// ==========================================================================
window.executeVehicleSearch = async function() {
  const inputEl = document.getElementById("vehicle-search-input");
  const plate = inputEl ? inputEl.value.trim().toUpperCase() : "GJ01AB1234";

  if (!plate) {
    if (window.showToast) {
      window.showToast("INPUT REQUIRED", "Please enter a valid vehicle registration plate number.", "HIGH");
    }
    return;
  }

  const nodesContainer = document.getElementById("journey-nodes-list");
  nodesContainer.innerHTML = `
    <div style="text-align:center; padding:40px; color:var(--accent-cyan); font-family:var(--font-mono);">
      <div style="font-weight:700; margin-bottom:8px;">CORRELATING STATEWIDE SIGHTINGS</div>
      <div style="font-size:0.8rem; color:var(--text-muted);">Querying 33 district edge databases for plate ${plate}...</div>
    </div>
  `;

  try {
    const res = await fetch(`/api/tracking/search?plate=${encodeURIComponent(plate)}`);
    if (!res.ok) {
      const err = await res.json();
      nodesContainer.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--accent-red);">
          <div style="font-weight:800; font-size:1.1rem; margin-bottom:6px;">NO SIGHTINGS FOUND</div>
          <div style="font-size:0.85rem; color:var(--text-muted);">${err.detail || "No camera records correlated for this license plate."}</div>
        </div>
      `;
      document.getElementById("journey-summary-panel").style.display = "none";
      return;
    }

    const data = await res.json();
    currentTrajectoryData = data;
    renderJourneyResults(data);

    // Render route on embedded tracer map
    drawTrajectoryOnTracerMap(data.trajectory);

    // Also prime main GIS map layer if needed
    if (window.drawTrajectoryOnMap) {
      window.drawTrajectoryOnMap(data.trajectory, false);
    }

  } catch (err) {
    console.error("Vehicle search failed:", err);
    nodesContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--accent-red);">Error communicating with intelligence server.</div>`;
  }
};

window.quickSearchVehicle = function(plate) {
  const inputEl = document.getElementById("vehicle-search-input");
  if (inputEl) inputEl.value = plate;
  executeVehicleSearch();
};

// ==========================================================================
// RENDER JOURNEY SUMMARY & CHECKPOINT CARDS
// ==========================================================================
function renderJourneyResults(data) {
  const summaryPanel = document.getElementById("journey-summary-panel");
  if (summaryPanel) summaryPanel.style.display = "block";

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
    descEl.innerHTML = `<strong>CRIME REGISTER:</strong> ${wl.reason} [FIR: ${wl.case_fir_number}] • Registered by ${wl.registered_authority}` +
      (data.route_confidence_pct ? ` • Route Confidence: <strong style="color:var(--accent-cyan);">${data.route_confidence_pct}% (${data.route_status || 'VERIFIED'})</strong>` : '');
  } else {
    riskBadge.className = "alert-risk-badge";
    riskBadge.style.background = "var(--accent-green)";
    riskBadge.textContent = "NORMAL TRANSIT";
    descEl.innerHTML = `Vehicle movement correlated across ${data.districts_traversed.join(", ")} without active police hotlist restrictions.` +
      (data.route_confidence_pct ? ` • Route Confidence: <strong style="color:var(--accent-green);">${data.route_confidence_pct}% (${data.route_status || 'VERIFIED'})</strong>` : '');
  }

  // Update map status banner
  const mapStatus = document.getElementById("tracer-map-status");
  if (mapStatus) {
    mapStatus.innerHTML = `<strong>${data.total_sightings} Checkpoints</strong> (${data.total_estimated_distance_km} km traversed)`;
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

        const isImpossibleSpeed = pt.link_status === 'IMPOSSIBLE_SPEED' || pt.speed_kmh > 140;

        return `
          <div class="journey-node-card" style="${isImpossibleSpeed ? 'border-left: 4px solid var(--accent-red);' : ''}" onclick="panTracerMapToWaypoint(${pt.lat}, ${pt.lng}, ${pt.sequence})">
            <div class="node-step-circle" style="${isImpossibleSpeed ? 'background:var(--accent-red);' : ''}">#${pt.sequence}</div>
            
            <div class="node-details">
              <div class="node-loc-name">${pt.location_name}</div>
              <div class="node-district-tag">${pt.district} District • ${pt.camera_name}</div>
              <div style="font-size:0.75rem; color:var(--text-muted); margin-top:3px;">
                Confidence: <strong>${(pt.confidence * 100).toFixed(1)}%</strong> • Estimated Speed: <strong>${pt.speed_kmh} km/h</strong>
                ${pt.match_method ? ` • <span style="color:var(--accent-cyan); font-weight:600;">[${pt.match_method}]</span>` : ''}
                ${pt.distance_km ? ` • Segment: +${pt.distance_km} km (${pt.time_delta_mins} mins)` : ''}
                ${isImpossibleSpeed ? ` • <span style="color:var(--accent-red); font-weight:800;">[IMPOSSIBLE SPEED ANOMALY]</span>` : ''}
              </div>
            </div>

            <div style="text-align:right; flex-shrink:0;">
              <div class="node-time-stat">${timeFormatted}</div>
              <div style="font-size:0.7rem; color:var(--text-dim);">${dateFormatted}</div>
            </div>

            <div style="text-align:right; flex-shrink:0;">
              <button class="quick-tag-btn" style="background:rgba(14,165,233,0.12); color:var(--accent-cyan); border-color:rgba(14,165,233,0.3);" onclick="event.stopPropagation(); openSection65BCertificate('${pt.sighting_id || pt.camera_id}')" title="Generate Section 65B Certificate">
                <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                <span>Sec 65B</span>
              </button>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

// ==========================================================================
// DUAL-PANE TRACER MAP TRAJECTORY PLOTTER
// ==========================================================================
function drawTrajectoryOnTracerMap(trajectoryPoints) {
  if (!trajectoryPoints || trajectoryPoints.length === 0) return;
  if (!tracerRouteMap) initTracerRouteMap();
  if (!tracerRouteMap) return;

  setTimeout(() => {
    tracerRouteMap.invalidateSize();
  }, 100);

  // Clear previous trajectory
  if (tracerTrajectoryLayer) tracerRouteMap.removeLayer(tracerTrajectoryLayer);
  if (tracerVehicleMarker) tracerRouteMap.removeLayer(tracerVehicleMarker);

  const latlngs = trajectoryPoints.map(p => [p.lat, p.lng]);
  const group = L.featureGroup();

  // Glowing Route Polyline
  const routeLine = L.polyline(latlngs, {
    color: "#0284c7",
    weight: 5,
    opacity: 0.9,
    dashArray: "10, 8",
    lineCap: "round"
  });
  group.addLayer(routeLine);

  // Waypoint pins
  trajectoryPoints.forEach(p => {
    const nodeIcon = L.divIcon({
      html: `<div style="background:#0284c7; color:#fff; border:2px solid #fff; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:11px; box-shadow:0 0 8px #0284c7;">${p.sequence}</div>`,
      className: "trajectory-node-pin",
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const nodeMarker = L.marker([p.lat, p.lng], { icon: nodeIcon });
    const timeStr = new Date(p.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    nodeMarker.bindPopup(`
      <div style="font-family:sans-serif; color:#0f172a; min-width:170px;">
        <div style="font-weight:bold; color:#0284c7; font-size:12px;">#${p.sequence}: ${p.location_name}</div>
        <div style="font-size:11px; margin-top:2px;"><strong>Time:</strong> ${timeStr}</div>
        <div style="font-size:11px;"><strong>Speed:</strong> ${p.speed_kmh} km/h</div>
        <div style="font-size:11px;"><strong>Camera:</strong> ${p.camera_name}</div>
      </div>
    `);
    group.addLayer(nodeMarker);
  });

  group.addTo(tracerRouteMap);
  tracerTrajectoryLayer = group;

  tracerRouteMap.fitBounds(routeLine.getBounds(), { padding: [40, 40] });

  // Animated Car Pin
  const carIcon = L.divIcon({
    html: `<div style="background:#ef4444; border:2px solid #fff; border-radius:4px; width:26px; height:26px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 10px rgba(239,68,68,0.6);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg></div>`,
    className: "car-anim-pin",
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  });

  tracerVehicleMarker = L.marker(latlngs[0], { icon: carIcon }).addTo(tracerRouteMap);

  let step = 0;
  const animInterval = setInterval(() => {
    step++;
    if (step < latlngs.length) {
      tracerVehicleMarker.setLatLng(latlngs[step]);
    } else {
      clearInterval(animInterval);
    }
  }, 1000);
}

window.panTracerMapToWaypoint = function(lat, lng, sequence) {
  if (tracerRouteMap) {
    tracerRouteMap.setView([lat, lng], 13, { animate: true });
  }
};

window.showJourneyOnMap = function() {
  if (!currentTrajectoryData || !currentTrajectoryData.trajectory) {
    if (window.showToast) {
      window.showToast("ACTION REQUIRED", "Please track a suspect vehicle first.", "HIGH");
    }
    return;
  }

  // Switch to GIS view tab
  const tabGis = document.getElementById("tab-gis");
  if (tabGis) tabGis.click();

  setTimeout(() => {
    if (window.drawTrajectoryOnMap) {
      window.drawTrajectoryOnMap(currentTrajectoryData.trajectory, true);
    }
  }, 250);
};
