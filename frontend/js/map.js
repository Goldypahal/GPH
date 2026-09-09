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
