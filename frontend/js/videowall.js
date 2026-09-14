// Unified C4I Video Wall Controller (Model 2 & 3) — Production Matrix Engine
let currentGridSize = 4; // 2x2 by default
let allLoadedCameras = [];
let currentCameras = [];
let activeCategory = "sentinel"; // default to Sentinel live feeds (cam01 - cam30)

window.initVideoWall = async function() {
  await loadVideoWallCameras();
  applyVideoWallFilter(activeCategory);
};

async function loadVideoWallCameras() {
  try {
    const res = await fetch("/api/cameras");
    if (res.ok) {
      allLoadedCameras = await res.json();
    }
  } catch (err) {
    console.error("Failed to load video wall cameras:", err);
  }
}

function applyVideoWallFilter(cat) {
  activeCategory = cat;
  if (!allLoadedCameras || allLoadedCameras.length === 0) return;

  if (cat === "sentinel") {
    // Prioritize Sentinel live streams cam01 - cam30
    currentCameras = allLoadedCameras.filter(c => 
      c.logical_camera_id.toLowerCase().startsWith("cam") && 
      !c.logical_camera_id.toUpperCase().startsWith("CAM-GJ")
    );
    if (currentCameras.length === 0) {
      currentCameras = allLoadedCameras.filter(c => c.vendor === "Sentinel-MediaMTX");
    }
    if (currentCameras.length === 0) {
      currentCameras = allLoadedCameras;
    }
  } else if (cat === "all") {
    currentCameras = [...allLoadedCameras];
  } else {
    // District filter
    currentCameras = allLoadedCameras.filter(c => c.district && c.district.toLowerCase() === cat.toLowerCase());
  }

  const sel = document.getElementById("videowall-source-select");
  if (sel && sel.value !== cat) {
    sel.value = cat;
  }

  renderVideoWall();
}
window.applyVideoWallFilter = applyVideoWallFilter;
window.filterVideoWallCategory = applyVideoWallFilter;

window.setVideoWallGrid = function(size) {
  currentGridSize = size * size;
  const container = document.getElementById("videowall-container");
  const buttons = document.querySelectorAll(".grid-btn");

  buttons.forEach(b => b.classList.remove("active"));
  const activeBtn = Array.from(buttons).find(b => b.textContent.trim() === `${size}x${size}`);
  if (activeBtn) activeBtn.classList.add("active");

  if (container) {
    container.className = `videowall-grid grid-${size}x${size}`;
  }
  renderVideoWall();
};

function renderVideoWall() {
  const container = document.getElementById("videowall-container");
  if (!container) return;

  if (currentCameras.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); text-align:center; padding:60px; font-size:0.9rem;">No cameras available for the selected filter category.</div>`;
    return;
  }

  const camsToDisplay = currentCameras.slice(0, currentGridSize);

  container.innerHTML = camsToDisplay.map((cam) => `
    <div class="cam-feed-tile" ondblclick="focusVideoWallCamera('${cam.logical_camera_id}')" title="Double click to expand to 1x1 full-screen">
      <div class="feed-header">
        <div class="feed-name">
          <span style="color:var(--accent-green); font-size:0.75rem;">●</span>
          <span>${cam.logical_camera_id}</span>
          <span style="font-size:0.7rem; color:var(--text-dim);">(${cam.district})</span>
        </div>
        <div style="display:flex; gap:6px; align-items:center;">
          <span class="feed-badge">${cam.resolution}</span>
          <span class="feed-badge" style="background:rgba(16,185,129,0.2); color:#34d399; border-color:rgba(16,185,129,0.4);">AI ANPR</span>
          <button class="quick-tag-btn" style="padding:1px 6px; font-size:0.65rem; background:rgba(0,0,0,0.6); color:#fff; border-color:rgba(255,255,255,0.2);" onclick="focusVideoWallCamera('${cam.logical_camera_id}')" title="Expand Feed">
            <svg class="ui-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
          </button>
        </div>
      </div>

      <!-- Live Stream MJPEG Image from Backend Connector -->
      <img src="/api/cameras/stream/${cam.logical_camera_id}" class="feed-media" alt="${cam.name}" loading="lazy" onerror="this.onerror=null; this.src='/static/assets/feed_placeholder.jpg';">

      <div class="feed-overlay-tag">
        <span><svg class="ui-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>${cam.location_name.slice(0, 26)}</span>
        <span>${cam.vendor}</span>
      </div>
    </div>
  `).join("");
}
window.renderVideoWall = renderVideoWall;

window.refreshVideoStreams = function() {
  if (window.showToast) {
    window.showToast("REFRESHING FEEDS", "Re-negotiating MJPEG stream pipelines...", "info", 2000);
  }
  renderVideoWall();
};

window.focusVideoWallCamera = function(logicalCode) {
  const tabBtn = document.getElementById("tab-videowall");
  if (tabBtn) tabBtn.click();

  const idx = allLoadedCameras.findIndex(c => c.logical_camera_id === logicalCode);
  if (idx !== -1) {
    const selected = allLoadedCameras[idx];
    currentCameras = [selected, ...allLoadedCameras.filter(c => c.logical_camera_id !== logicalCode)];
  }
  window.setVideoWallGrid(1); // switch to 1x1 full screen
};
