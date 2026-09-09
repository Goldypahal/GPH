// Leaflet GIS Mapping for Gujarat Statewide CCTV Network
let gisMap = null;
let cameraMarkers = [];
let trajectoryLayer = null;
let animatedVehicleMarker = null;
let allCamerasData = [];

window.initGISMap = async function() {
  const container = document.getElementById("gis-map-container");
  if (!container) return;

  // Center on Gujarat state (Gandhinagar / Ahmedabad region)
  gisMap = L.map("gis-map-container", {
    center: [22.45, 71.60],
    zoom: 7,
    zoomControl: true,
    minZoom: 6,
    maxZoom: 18
  });
  window.gisMap = gisMap;

  // Tactical Dark Tile Layer (CartoDB Dark Matter)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> | Gujarat Police GIVIN C4I',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(gisMap);

  // Fetch all 50 cameras
  try {
    const res = await fetch("/api/cameras");
    if (res.ok) {
      allCamerasData = await res.json();
      renderCameraMarkers(allCamerasData);
      renderCameraSidebarList(allCamerasData);
    }
  } catch (err) {
    console.error("Failed to load cameras on map:", err);
  }
};

function createCameraIcon(status, hasAlert = false) {
  let color = "#0ea5e9"; // Cyan Active
  if (status === "DEGRADED") color = "#f59e0b"; // Amber Degraded
  if (hasAlert) color = "#ef4444"; // Red Alert

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28">
      <circle cx="12" cy="12" r="10" fill="${color}" fill-opacity="0.25" stroke="${color}" stroke-width="2"/>
      <circle cx="12" cy="12" r="4" fill="${color}"/>
      <path d="M12 2 L12 6 M12 18 L12 22 M2 12 L6 12 M18 12 L22 12" stroke="${color}" stroke-width="1.5"/>
    </svg>
  `;

  return L.divIcon({
    html: svg,
    className: "custom-cam-pin",
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14]
  });
}

function renderCameraMarkers(cameras) {
  // Clear existing
  cameraMarkers.forEach(m => gisMap.removeLayer(m));
  cameraMarkers = [];

  cameras.forEach(cam => {
    const isAlertCam = (cam.logical_camera_id === "CAM-GJ-VLS-01" || cam.logical_camera_id === "CAM-GJ-AHM-01");
    const icon = createCameraIcon(cam.status, isAlertCam);
    const marker = L.marker([cam.lat, cam.lng], { icon: icon });

    const popupContent = `
      <div style="font-family:sans-serif; color:#0f172a; min-width:210px;">
        <div style="font-weight:bold; font-size:13px; color:#0369a1; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin-bottom:6px;">
          ${cam.name}
        </div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Code:</strong> ${cam.logical_camera_id}</div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>District:</strong> ${cam.district}</div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Location:</strong> ${cam.location_name}</div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Hardware:</strong> ${cam.vendor} ${cam.resolution} (${cam.protocol})</div>
        <div style="font-size:11px; margin-bottom:8px;"><strong>Status:</strong> <span style="color:${cam.status === 'ACTIVE' ? '#16a34a' : '#ea580c'}; font-weight:bold;">${cam.status}</span> | Latency: ${cam.latency_ms || 40}ms</div>
        <a href="javascript:void(0)" onclick="focusVideoWallCamera('${cam.logical_camera_id}')" style="display:inline-block; background:#0284c7; color:#fff; text-decoration:none; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold;">
          📹 View Live Feed
        </a>
      </div>
    `;

    marker.bindPopup(popupContent);
    marker.addTo(gisMap);
    cameraMarkers.push(marker);
  });
}

function renderCameraSidebarList(cameras) {
  const container = document.getElementById("camera-sidebar-list");
  if (!container) return;

  container.innerHTML = cameras.map(cam => `
    <div class="alert-item-card" style="border-left-color:${cam.status === 'ACTIVE' ? '#0ea5e9' : '#f59e0b'}; padding:8px 12px; margin-bottom:8px; cursor:pointer;" onclick="panToCamera(${cam.lat}, ${cam.lng}, '${cam.name}')">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:bold; font-size:0.8rem; color:#fff;">${cam.logical_camera_id}</span>
        <span style="font-size:0.68rem; color:${cam.status === 'ACTIVE' ? '#34d399' : '#fbbf24'}; font-family:var(--font-mono);">${cam.status}</span>
      </div>
      <div style="font-size:0.75rem; color:var(--text-muted); margin:2px 0;">${cam.name}</div>
      <div style="font-size:0.7rem; color:var(--text-dim); display:flex; justify-content:space-between;">
        <span>${cam.district}</span>
        <span>${cam.vendor} (${cam.protocol})</span>
      </div>
    </div>
  `).join("");
}

function panToCamera(lat, lng, name) {
  if (gisMap) {
    gisMap.setView([lat, lng], 13, { animate: true });
    // Find marker and open popup
    const marker = cameraMarkers.find(m => {
      const pos = m.getLatLng();
      return Math.abs(pos.lat - lat) < 0.0001 && Math.abs(pos.lng - lng) < 0.0001;
    });
    if (marker) marker.openPopup();
  }
}

function filterMapByDistrict(district) {
  if (!gisMap) return;
  if (district === "all") {
    gisMap.setView([22.45, 71.60], 7);
    renderCameraMarkers(allCamerasData);
    renderCameraSidebarList(allCamerasData);
    return;
  }

  const filtered = allCamerasData.filter(c => c.district.toLowerCase() === district.toLowerCase());
  renderCameraMarkers(filtered);
  renderCameraSidebarList(filtered);

  const districtCenters = {
    "Ahmedabad": [23.03, 72.58, 11],
    "Surat": [21.20, 72.84, 11],
    "Vadodara": [22.31, 73.19, 11],
    "Valsad": [20.35, 72.91, 10]
  };

  const center = districtCenters[district];
  if (center) {
    gisMap.setView([center[0], center[1]], center[2], { animate: true });
  }
}

function filterCameraList() {
  const query = document.getElementById("camera-filter-input").value.toLowerCase();
  const filtered = allCamerasData.filter(c => 
    c.name.toLowerCase().includes(query) ||
    c.logical_camera_id.toLowerCase().includes(query) ||
    c.district.toLowerCase().includes(query) ||
    c.vendor.toLowerCase().includes(query)
  );
  renderCameraSidebarList(filtered);
}

// Draw reconstructed vehicle trajectory on GIS map
window.drawTrajectoryOnMap = function(trajectoryPoints) {
  if (!gisMap || !trajectoryPoints || trajectoryPoints.length === 0) return;

  // Clear previous trajectory
  if (trajectoryLayer) gisMap.removeLayer(trajectoryLayer);
  if (animatedVehicleMarker) gisMap.removeLayer(animatedVehicleMarker);

  const latlngs = trajectoryPoints.map(p => [p.lat, p.lng]);

  // Create trajectory group
  const group = L.featureGroup();

  // Draw Glowing Route Polyline
  const routeLine = L.polyline(latlngs, {
    color: "#0ea5e9",
    weight: 5,
    opacity: 0.85,
    dashArray: "10, 8",
    lineCap: "round"
  });
  group.addLayer(routeLine);

  // Add numbered waypoint nodes for each checkpoint
  trajectoryPoints.forEach(p => {
    const nodeIcon = L.divIcon({
      html: `<div style="background:#0284c7; color:#fff; border:2px solid #fff; border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:12px; box-shadow:0 0 10px #0284c7;">${p.sequence}</div>`,
      className: "trajectory-node-pin",
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const nodeMarker = L.marker([p.lat, p.lng], { icon: nodeIcon });
    const timeStr = new Date(p.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    nodeMarker.bindPopup(`
      <div style="font-family:sans-serif; color:#0f172a; min-width:180px;">
        <div style="font-weight:bold; color:#0284c7; font-size:12px;">Checkpoint #${p.sequence}: ${p.location_name}</div>
        <div style="font-size:11px;"><strong>Time:</strong> ${timeStr}</div>
        <div style="font-size:11px;"><strong>Speed:</strong> ${p.speed_kmh} km/h</div>
        <div style="font-size:11px;"><strong>Camera:</strong> ${p.camera_name}</div>
      </div>
    `);
    group.addLayer(nodeMarker);
  });

  group.addTo(gisMap);
  trajectoryLayer = group;

  // Fit bounds to entire route
  gisMap.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

  // Add animated vehicle marker at start position
  const carIcon = L.divIcon({
    html: `<div style="background:#ef4444; border:2px solid #fff; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-size:15px; box-shadow:0 0 18px #ef4444; animation:pulse 1.2s infinite;">🚗</div>`,
    className: "car-anim-pin",
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });

  animatedVehicleMarker = L.marker(latlngs[0], { icon: carIcon }).addTo(gisMap);

  // Stepwise animation along checkpoints
  let step = 0;
  const interval = setInterval(() => {
    step++;
    if (step < latlngs.length) {
      animatedVehicleMarker.setLatLng(latlngs[step]);
    } else {
      clearInterval(interval);
    }
  }, 1200);
};

// ==========================================================================
// LIVE PURSUIT MODE — GTA5-style live tracking blip for a stolen vehicle.
// Polls /api/tracking/live/{plate}, which dead-reckons a moving position
// from the vehicle's last two confirmed ANPR sightings (heading + speed),
// and animates a pulsing marker + heading cone + predicted-next-camera
// pin on the GIS map, alongside a live HUD readout.
// ==========================================================================
let livePursuitState = {
  active: false,
  plate: null,
  pollTimer: null,
  marker: null,
  nextCamMarker: null,
  trailLine: null
};

function toggleLivePursuit() {
  if (livePursuitState.active) {
    stopLivePursuit();
    return;
  }
  if (typeof currentTrajectoryData === "undefined" || !currentTrajectoryData || !currentTrajectoryData.plate_number) {
    alert("Track a vehicle's journey first, then start Live Track.");
    return;
  }
  startLivePursuit(currentTrajectoryData.plate_number);
}

function startLivePursuit(plate) {
  livePursuitState.active = true;
  livePursuitState.plate = plate;

  const btn = document.getElementById("live-pursuit-toggle-btn");
  if (btn) { btn.innerHTML = "<span>⏹</span> STOP LIVE TRACK"; btn.style.background = "#7f1d1d"; }

  document.getElementById("lp-hud-plate").textContent = plate;
  document.getElementById("live-pursuit-hud").style.display = "block";

  // Jump to the GIS map view so the officer sees the live blip immediately.
  const tabGis = document.getElementById("tab-gis");
  if (tabGis) tabGis.click();

  pollLivePursuit(); // immediate first fetch
  livePursuitState.pollTimer = setInterval(pollLivePursuit, 2500);
}

function stopLivePursuit() {
  livePursuitState.active = false;
  if (livePursuitState.pollTimer) clearInterval(livePursuitState.pollTimer);
  livePursuitState.pollTimer = null;

  const btn = document.getElementById("live-pursuit-toggle-btn");
  if (btn) { btn.innerHTML = "<span>🚨</span> LIVE TRACK ON MAP"; btn.style.background = "#dc2626"; }

  document.getElementById("live-pursuit-hud").style.display = "none";

  if (gisMap) {
    if (livePursuitState.marker) gisMap.removeLayer(livePursuitState.marker);
    if (livePursuitState.nextCamMarker) gisMap.removeLayer(livePursuitState.nextCamMarker);
    if (livePursuitState.trailLine) gisMap.removeLayer(livePursuitState.trailLine);
  }
  livePursuitState.marker = null;
  livePursuitState.nextCamMarker = null;
  livePursuitState.trailLine = null;
}

async function pollLivePursuit() {
  if (!livePursuitState.active || !livePursuitState.plate) return;
  try {
    const res = await fetch(`/api/tracking/live/${encodeURIComponent(livePursuitState.plate)}`);
    if (!res.ok) {
      document.getElementById("lp-hud-status-pill").textContent = "NO SIGNAL";
      return;
    }
    const pos = await res.json();
    renderLivePursuitPosition(pos);
  } catch (err) {
    console.error("Live pursuit poll failed:", err);
  }
}

function renderLivePursuitPosition(pos) {
  const isStale = pos.status === "STALE";

  // --- HUD readout ---
  const pill = document.getElementById("lp-hud-status-pill");
  pill.textContent = isStale ? "SIGNAL STALE" : "LIVE (PREDICTED)";
  pill.className = "lp-hud-status-pill " + (isStale ? "lp-stale-pill" : "lp-live");

  const dot = document.getElementById("lp-status-dot");
  dot.style.background = isStale ? "#f59e0b" : "#ef4444";

  document.getElementById("lp-hud-speed").textContent = `${pos.speed_kmh} km/h`;
  document.getElementById("lp-hud-heading").textContent = `${compassFromDeg(pos.heading_deg)} (${pos.heading_deg}°)`;
  document.getElementById("lp-hud-last-cam").textContent = `${pos.last_confirmed_camera} (${pos.last_confirmed_district})`;
  document.getElementById("lp-hud-age").textContent = formatAgeSeconds(pos.seconds_since_confirmed);
  document.getElementById("lp-hud-next-cam").textContent = pos.predicted_next_camera
    ? `${pos.predicted_next_camera} (${pos.predicted_next_district})`
    : "No camera ahead on heading";
  document.getElementById("lp-hud-eta").textContent = pos.eta_to_next_camera_sec
    ? `~${Math.round(pos.eta_to_next_camera_sec / 60)} min`
    : "–";

  if (!gisMap) return;

  // --- Trail (fading line of recent confirmed checkpoints) ---
  if (livePursuitState.trailLine) gisMap.removeLayer(livePursuitState.trailLine);
  if (pos.trail && pos.trail.length > 1) {
    livePursuitState.trailLine = L.polyline(pos.trail, {
      color: "#ef4444", weight: 3, opacity: 0.4, dashArray: "4, 6"
    }).addTo(gisMap);
  }

  // --- Live pulsing blip with heading cone (radar-style) ---
  const html = `
    <div class="lp-vehicle-marker-wrap">
      <div class="lp-radar-ring"></div>
      <div class="lp-heading-cone" style="transform:rotate(${pos.heading_deg}deg);"></div>
      <div class="lp-vehicle-dot ${isStale ? 'lp-stale' : ''}">🚓</div>
    </div>
  `;
  const icon = L.divIcon({ html, className: "lp-marker-icon", iconSize: [46, 46], iconAnchor: [23, 23] });

  if (!livePursuitState.marker) {
    livePursuitState.marker = L.marker([pos.lat, pos.lng], { icon, zIndexOffset: 1000 }).addTo(gisMap);
    gisMap.setView([pos.lat, pos.lng], 10, { animate: true });
  } else {
    livePursuitState.marker.setIcon(icon);
    livePursuitState.marker.setLatLng([pos.lat, pos.lng]); // Leaflet marker CSS transition eases this visually
  }
  livePursuitState.marker.bindPopup(`
    <div style="font-family:sans-serif; color:#0f172a; min-width:200px;">
      <div style="font-weight:bold; color:#dc2626;">🚨 ${pos.plate_number} — ${isStale ? 'SIGNAL STALE' : 'LIVE PREDICTED'}</div>
      <div style="font-size:11px; margin-top:4px;">${pos.watchlist_reason || 'Under active surveillance'}</div>
      <div style="font-size:11px;"><strong>Speed:</strong> ${pos.speed_kmh} km/h &nbsp; <strong>Heading:</strong> ${compassFromDeg(pos.heading_deg)}</div>
    </div>
  `);

  // --- Predicted next camera pin ---
  if (livePursuitState.nextCamMarker) gisMap.removeLayer(livePursuitState.nextCamMarker);
  if (pos.predicted_next_camera && pos.predicted_next_lat) {
    const camIcon = L.divIcon({
      html: `<div class="lp-next-camera-icon" style="font-size:22px;">🎯</div>`,
      className: "lp-next-cam-pin", iconSize: [26, 26], iconAnchor: [13, 13]
    });
    livePursuitState.nextCamMarker = L.marker([pos.predicted_next_lat, pos.predicted_next_lng], { icon: camIcon })
      .bindTooltip(`Likely next reconfirmation: ${pos.predicted_next_camera}`, { permanent: false })
      .addTo(gisMap);
  }
}

function compassFromDeg(deg) {
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

function formatAgeSeconds(sec) {
  if (sec < 60) return `${Math.round(sec)}s ago`;
  const mins = Math.floor(sec / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m ago`;
}
