// Unified C4I Video Wall Controller (Model 2 & 3)
let currentGridSize = 4; // 2x2 by default
let currentCameras = [];

window.initVideoWall = async function() {
  await loadVideoWallCameras();
  renderVideoWall();
};

async function loadVideoWallCameras() {
  try {
    const res = await fetch("/api/cameras");
    if (res.ok) {
      currentCameras = await res.json();
    }
  } catch (err) {
    console.error("Failed to load video wall cameras:", err);
  }
}

function setVideoWallGrid(size) {
  currentGridSize = size * size;
  const container = document.getElementById("videowall-container");
  const buttons = document.querySelectorAll(".grid-btn");

  buttons.forEach(b => b.classList.remove("active"));
  const activeBtn = Array.from(buttons).find(b => b.textContent.trim() === `${size}x${size}`);
  if (activeBtn) activeBtn.classList.add("active");

  container.className = `videowall-grid grid-${size}x${size}`;
  renderVideoWall();
}

function renderVideoWall() {
  const container = document.getElementById("videowall-container");
  if (!container) return;

  if (currentCameras.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); text-align:center; padding:40px;">Loading live camera feeds...</div>`;
    return;
  }

  const camsToDisplay = currentCameras.slice(0, currentGridSize);

  container.innerHTML = camsToDisplay.map((cam, idx) => `
    <div class="cam-feed-tile">
      <div class="feed-header">
        <div class="feed-name">
          <span style="color:#10b981;">●</span>
          <span>${cam.logical_camera_id}</span>
          <span style="font-size:0.7rem; color:var(--text-dim);">(${cam.district})</span>
        </div>
        <div style="display:flex; gap:6px;">
          <span class="feed-badge">${cam.resolution}</span>
          <span class="feed-badge" style="background:rgba(16,185,129,0.15); color:#34d399; border-color:rgba(16,185,129,0.3);">AI ANPR</span>
        </div>
      </div>

      <!-- Live Stream MJPEG Image from Backend Connector -->
      <img src="/api/cameras/stream/${cam.logical_camera_id}" class="feed-media" alt="${cam.name}" loading="lazy" onerror="this.src='/static/assets/feed_placeholder.jpg';">

      <div class="feed-overlay-tag">
        <span>📍 ${cam.location_name.slice(0, 24)}</span>
        <span>| ${cam.vendor}</span>
      </div>
    </div>
  `).join("");
}

function refreshVideoStreams() {
  renderVideoWall();
}

function focusVideoWallCamera(logicalCode) {
  const tabBtn = document.getElementById("tab-videowall");
  if (tabBtn) tabBtn.click();

  // Find camera and put it as first in list
  const idx = currentCameras.findIndex(c => c.logical_camera_id === logicalCode);
  if (idx !== -1) {
    const selected = currentCameras.splice(idx, 1)[0];
    currentCameras.unshift(selected);
  }
  setVideoWallGrid(1); // switch to 1x1 full screen
}
