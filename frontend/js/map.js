// Leaflet GIS Mapping for Gujarat Statewide CCTV Network — Production Engine
let gisMap = null;
let cameraMarkers = [];
let trajectoryLayer = null;
let animatedVehicleMarker = null;
let allCamerasData = [];
let tileLayerInstance = null;

function getTileLayerUrl(theme) {
  if (theme === "dark") {
    return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  }
  return "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
}

window.updateMapTheme = function(theme) {
  if (gisMap && tileLayerInstance) {
    gisMap.removeLayer(tileLayerInstance);
    tileLayerInstance = L.tileLayer(getTileLayerUrl(theme), {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> | Gujarat Police GIVIN C4I',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(gisMap);
  }
  if (window.updateTracerMapTheme) {
    window.updateTracerMapTheme(theme);
  }
};

window.initGISMap = async function() {
  const container = document.getElementById("gis-map-container");
  if (!container || gisMap) return;

  // Center on Gujarat state (Gandhinagar / Ahmedabad region)
  gisMap = L.map("gis-map-container", {
    center: [22.45, 71.60],
    zoom: 7,
    zoomControl: true,
    minZoom: 6,
    maxZoom: 18
  });
  window.gisMap = gisMap;

  // Tile Layer
  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  tileLayerInstance = L.tileLayer(getTileLayerUrl(currentTheme), {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> | Gujarat Police GIVIN C4I',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(gisMap);

  // Fetch cameras
  try {
    const res = await fetch("/api/cameras");
    if (res.ok) {
      allCamerasData = await res.json();
      window.allCamerasData = allCamerasData;
      renderCameraMarkers(allCamerasData);
      renderCameraSidebarList(allCamerasData);
    }
  } catch (err) {
    console.error("Failed to load cameras on map:", err);
  }
};

function createCameraIcon(status, hasAlert = false) {
  let color = "#0284c7"; // Cyan Active
  if (status === "DEGRADED") color = "#d97706"; // Amber Degraded
  if (hasAlert) color = "#dc2626"; // Red Alert

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
  cameraMarkers.forEach(m => gisMap.removeLayer(m));
  cameraMarkers = [];

  cameras.forEach(cam => {
    const isAlertCam = (typeof activeAlertsList !== "undefined" && activeAlertsList.length > 0)
      ? activeAlertsList.some(a => a.camera_code === cam.logical_camera_id || a.camera_id === cam.id || a.camera_name === cam.name)
      : false;
    const icon = createCameraIcon(cam.status, isAlertCam);
    const marker = L.marker([cam.lat, cam.lng], { icon: icon });

    const latencyDisplay = cam.latency_ms != null ? `${cam.latency_ms}ms` : 'Awaiting Ping';
    const popupContent = `
      <div style="font-family:var(--font-sans, sans-serif); color:#0f172a; min-width:210px; padding:4px;">
        <div style="font-weight:700; font-size:13px; color:#0369a1; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin-bottom:6px;">
          ${cam.name}
        </div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Code:</strong> <span style="font-family:monospace;">${cam.logical_camera_id}</span></div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>District:</strong> ${cam.district}</div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Location:</strong> ${cam.location_name}</div>
        <div style="font-size:11px; margin-bottom:3px;"><strong>Hardware:</strong> ${cam.vendor} ${cam.resolution} (${cam.protocol})</div>
        <div style="font-size:11px; margin-bottom:8px;"><strong>Status:</strong> <span style="color:${cam.status === 'ACTIVE' ? '#059669' : '#d97706'}; font-weight:bold;">${cam.status}</span> | Latency: ${latencyDisplay}</div>
        <a href="javascript:void(0)" onclick="focusVideoWallCamera('${cam.logical_camera_id}')" style="display:inline-flex; align-items:center; gap:4px; background:#0284c7; color:#fff; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold;">
          <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg> View Live Stream
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
    <div class="camera-card" onclick="panToCamera(${cam.lat}, ${cam.lng}, '${cam.name}')">
      <div class="camera-card-top">
        <span class="camera-card-code">${cam.logical_camera_id}</span>
        <span style="font-size:0.68rem; font-weight:700; color:${cam.status === 'ACTIVE' ? 'var(--accent-green)' : 'var(--accent-amber)'}; font-family:var(--font-mono);">${cam.status}</span>
      </div>
      <div class="camera-card-title">${cam.name}</div>
      <div class="camera-card-meta">
        <span>${cam.district} District</span>
        <span>${cam.vendor} (${cam.protocol})</span>
      </div>
    </div>
  `).join("");
}

window.panToCamera = function(lat, lng, name) {
  if (gisMap) {
    gisMap.setView([lat, lng], 13, { animate: true });
    const marker = cameraMarkers.find(m => {
      const pos = m.getLatLng();
      return Math.abs(pos.lat - lat) < 0.0001 && Math.abs(pos.lng - lng) < 0.0001;
    });
    if (marker) marker.openPopup();
  }
};

window.focusMapOnCamera = function(logicalCode) {
  if (!allCamerasData || allCamerasData.length === 0) return;
  const cam = allCamerasData.find(c => c.logical_camera_id === logicalCode);
  if (cam) {
    panToCamera(cam.lat, cam.lng, cam.name);
  }
};

window.filterMapByDistrict = function(district) {
  if (!gisMap) return;
  
  // Update button active state
  const btns = document.querySelectorAll("#gis-view .quick-tag-btn");
  btns.forEach(b => b.classList.remove("active"));
  const clickedBtn = Array.from(btns).find(b => b.textContent.toLowerCase().includes(district.toLowerCase()));
  if (clickedBtn) clickedBtn.classList.add("active");

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
};

window.filterCameraList = function() {
  const query = document.getElementById("camera-filter-input").value.toLowerCase();
  const filtered = allCamerasData.filter(c => 
    c.name.toLowerCase().includes(query) ||
    c.logical_camera_id.toLowerCase().includes(query) ||
    c.district.toLowerCase().includes(query) ||
    c.vendor.toLowerCase().includes(query)
  );
  renderCameraSidebarList(filtered);
};

// Draw reconstructed vehicle trajectory on GIS map
window.drawTrajectoryOnMap = function(trajectoryPoints, autoFit = true) {
  if (!gisMap || !trajectoryPoints || trajectoryPoints.length === 0) return;

  if (trajectoryLayer) gisMap.removeLayer(trajectoryLayer);
  if (animatedVehicleMarker) gisMap.removeLayer(animatedVehicleMarker);

  const latlngs = trajectoryPoints.map(p => [p.lat, p.lng]);
  const group = L.featureGroup();

  // Glowing Route Polyline
  const routeLine = L.polyline(latlngs, {
    color: "#0284c7",
    weight: 5,
    opacity: 0.85,
    dashArray: "10, 8",
    lineCap: "round"
  });
  group.addLayer(routeLine);

  // Numbered Waypoints
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

  if (autoFit) {
    gisMap.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
  }

  // Car icon
  const carIcon = L.divIcon({
    html: `<div style="background:#ef4444; border:2px solid #fff; border-radius:4px; width:28px; height:28px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 10px rgba(239,68,68,0.5);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg></div>`,
    className: "car-anim-pin",
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  animatedVehicleMarker = L.marker(latlngs[0], { icon: carIcon }).addTo(gisMap);

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
// LIVE PURSUIT MODE: Real-time Dead-Reckoned Tracking Blip & Heading Cone
// ==========================================================================
let livePursuitState = {
  active: false,
  plate: null,
  pollTimer: null,
  marker: null,
  nextCamMarker: null,
  trailLine: null
};

window.toggleLivePursuit = function() {
  if (livePursuitState.active) {
    stopLivePursuit();
    return;
  }
  if (typeof currentTrajectoryData === "undefined" || !currentTrajectoryData || !currentTrajectoryData.plate_number) {
    if (window.showToast) {
      window.showToast("TRACKING REQUIRED", "Track a vehicle journey first, then start Live Track.", "HIGH");
    }
    return;
  }
  startLivePursuit(currentTrajectoryData.plate_number);
};

function startLivePursuit(plate) {
  livePursuitState.active = true;
  livePursuitState.plate = plate;

  const btn = document.getElementById("live-pursuit-toggle-btn");
  if (btn) {
    btn.innerHTML = `<svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none" style="margin-right:4px;"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>STOP LIVE TRACK`;
    btn.style.background = "#7f1d1d";
  }

  document.getElementById("lp-hud-plate").textContent = plate;
  document.getElementById("live-pursuit-hud").style.display = "block";

  // Focus GIS Map view
  const tabGis = document.getElementById("tab-gis");
  if (tabGis) tabGis.click();

  if (window.showToast) {
    window.showToast("LIVE PURSUIT ACTIVATED", `Dead-reckoned telemetry enabled for target ${plate}.`, "CRITICAL");
  }

  pollLivePursuit();
  livePursuitState.pollTimer = setInterval(pollLivePursuit, 2500);
}

function stopLivePursuit() {
  livePursuitState.active = false;
  if (livePursuitState.pollTimer) clearInterval(livePursuitState.pollTimer);
  livePursuitState.pollTimer = null;

  const btn = document.getElementById("live-pursuit-toggle-btn");
  if (btn) {
    btn.innerHTML = `<svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>LIVE TRACK ON MAP`;
    btn.style.background = "var(--accent-red)";
  }

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

  const pill = document.getElementById("lp-hud-status-pill");
  pill.textContent = isStale ? "SIGNAL STALE" : "LIVE (PREDICTED)";
  pill.className = "lp-hud-status-pill " + (isStale ? "lp-stale-pill" : "lp-live");

  const dot = document.getElementById("lp-status-dot");
  dot.style.background = isStale ? "var(--accent-amber)" : "var(--accent-red)";

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

  // Trail
  if (livePursuitState.trailLine) gisMap.removeLayer(livePursuitState.trailLine);
  if (pos.trail && pos.trail.length > 1) {
    livePursuitState.trailLine = L.polyline(pos.trail, {
      color: "#dc2626", weight: 3, opacity: 0.45, dashArray: "4, 6"
    }).addTo(gisMap);
  }

  // Live blip with directional heading cone
  const html = `
    <div class="lp-vehicle-marker-wrap">
      <div class="lp-heading-cone" style="transform:rotate(${pos.heading_deg}deg);"></div>
      <div class="lp-vehicle-dot ${isStale ? 'lp-stale' : ''}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
      </div>
    </div>
  `;
  const icon = L.divIcon({ html, className: "lp-marker-icon", iconSize: [46, 46], iconAnchor: [23, 23] });

  if (!livePursuitState.marker) {
    livePursuitState.marker = L.marker([pos.lat, pos.lng], { icon, zIndexOffset: 1000 }).addTo(gisMap);
    gisMap.setView([pos.lat, pos.lng], 10, { animate: false });
  } else {
    livePursuitState.marker.setIcon(icon);
    livePursuitState.marker.setLatLng([pos.lat, pos.lng]);
  }
  livePursuitState.marker.bindPopup(`
    <div style="font-family:sans-serif; color:#0f172a; min-width:200px; padding:4px;">
      <div style="font-weight:bold; color:#dc2626; display:flex; align-items:center; gap:6px;">
        <svg class="ui-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
        ${pos.plate_number}: ${isStale ? 'SIGNAL STALE' : 'LIVE PREDICTED'}
      </div>
      <div style="font-size:11px; margin-top:4px;">${pos.watchlist_reason || 'Under active surveillance'}</div>
      <div style="font-size:11px;"><strong>Speed:</strong> ${pos.speed_kmh} km/h &nbsp; <strong>Heading:</strong> ${compassFromDeg(pos.heading_deg)}</div>
    </div>
  `);

  // Predicted next camera pin
  if (livePursuitState.nextCamMarker) gisMap.removeLayer(livePursuitState.nextCamMarker);
  if (pos.predicted_next_camera && pos.predicted_next_lat) {
    const camIcon = L.divIcon({
      html: `<div class="lp-next-camera-icon" style="display:flex; align-items:center; justify-content:center; width:24px; height:24px; background:#0284c7; border:2px solid #fff; border-radius:4px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="22" y1="12" x2="18" y2="12"></line><line x1="6" y1="12" x2="2" y2="12"></line><line x1="12" y1="6" x2="12" y2="2"></line><line x1="12" y1="22" x2="12" y2="18"></line></svg></div>`,
      className: "lp-next-cam-pin", iconSize: [24, 24], iconAnchor: [12, 12]
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
