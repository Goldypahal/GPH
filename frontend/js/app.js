// GIVIN Master App Controller — Production Real-Time & Navigation Engine
let alertsWebSocket = null;
let wsReconnectTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initClock();
  initNavigation();
  initCommandPalette();
  initWebSocketAlerts();
  loadInitialData();
});

// ==========================================================================
// THEME MANAGEMENT
// ==========================================================================
function initTheme() {
  const savedTheme = localStorage.getItem("givin-theme") || "light";
  setTheme(savedTheme);
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("givin-theme", theme);
  const toggleBtn = document.getElementById("theme-toggle-btn");
  if (toggleBtn) {
    if (theme === "dark") {
      toggleBtn.innerHTML = `
        <svg class="ui-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
        <span>Light Mode</span>
      `;
    } else {
      toggleBtn.innerHTML = `
        <svg class="ui-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        <span>Dark Mode</span>
      `;
    }
  }
  if (window.updateMapTheme) {
    window.updateMapTheme(theme);
  }
}

window.toggleTheme = function() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  setTheme(next);
};

// ==========================================================================
// CLOCK & TELEMETRY
// ==========================================================================
function initClock() {
  const clockEl = document.getElementById("realtime-clock");
  if (!clockEl) return;
  const update = () => {
    const now = new Date();
    const istTime = now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
    clockEl.textContent = `${istTime} IST | ${now.toUTCString().slice(17, 25)} UTC`;
  };
  update();
  setInterval(update, 1000);
}

// ==========================================================================
// NAVIGATION & VIEWPORT SWITCHING
// ==========================================================================
function initNavigation() {
  const tabBtns = document.querySelectorAll(".nav-tab-btn");
  const views = document.querySelectorAll(".view-section");
  const navMenu = document.getElementById("main-nav-tabs");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetView = btn.getAttribute("data-view");
      tabBtns.forEach(b => b.classList.remove("active"));
      views.forEach(v => v.classList.remove("active"));

      btn.classList.add("active");
      const activeSection = document.getElementById(targetView);
      if (activeSection) {
        activeSection.classList.add("active");
      }

      // Close mobile menu if open
      if (navMenu && navMenu.classList.contains("mobile-open")) {
        navMenu.classList.remove("mobile-open");
      }

      // Trigger Leaflet resize if GIS map tab is activated
      if (targetView === "gis-view" && window.gisMap) {
        setTimeout(() => {
          window.gisMap.invalidateSize();
        }, 150);
      }
      
      // Trigger Leaflet resize on tracer route map
      if (targetView === "tracer-view" && window.tracerRouteMap) {
        setTimeout(() => {
          window.tracerRouteMap.invalidateSize();
        }, 150);
      }

      // Ensure Video Wall is refreshed if activated
      if (targetView === "videowall-view" && window.renderVideoWall) {
        window.renderVideoWall();
      }
    });
  });
}

window.toggleMobileNav = function() {
  const navMenu = document.getElementById("main-nav-tabs");
  if (navMenu) {
    navMenu.classList.toggle("mobile-open");
  }
};

// ==========================================================================
// WEBSOCKET REAL-TIME ALERTS BROADCAST
// ==========================================================================
function initWebSocketAlerts() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;

  try {
    alertsWebSocket = new WebSocket(wsUrl);

    alertsWebSocket.onopen = () => {
      console.log("Connected to GIVIN Live Alert WebSocket:", wsUrl);
      const statusText = document.getElementById("system-status-text");
      if (statusText) statusText.textContent = "HIGH ASSURANCE LIVE";
    };

    alertsWebSocket.onmessage = (event) => {
      try {
        const alertData = JSON.parse(event.data);
        handleIncomingWebSocketAlert(alertData);
      } catch (e) {
        console.warn("WebSocket payload parse error:", e);
      }
    };

    alertsWebSocket.onclose = () => {
      console.warn("WebSocket disconnected. Retrying in 5s...");
      scheduleWebSocketReconnect();
    };

    alertsWebSocket.onerror = (err) => {
      console.warn("WebSocket connection error:", err);
      alertsWebSocket.close();
    };
  } catch (err) {
    console.error("Failed to establish WebSocket:", err);
    scheduleWebSocketReconnect();
  }
}

function scheduleWebSocketReconnect() {
  if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
  wsReconnectTimer = setTimeout(() => {
    initWebSocketAlerts();
  }, 5000);
}

function handleIncomingWebSocketAlert(data) {
  // Update Ticker
  const tickerText = document.getElementById("ticker-alert-text");
  if (tickerText) {
    tickerText.textContent = `[${data.alert_uid || 'PRIORITY-HIT'}] ${data.risk_level || 'HOTLIST'}: ${data.plate_text || data.plate} detected at ${data.camera_name || data.camera} (${data.district || 'Gujarat'})!`;
  }

  // Play audio chime
  if (window.playAlarmChime) {
    window.playAlarmChime();
  }

  // Show Toast
  showToast(
    `PRIORITY HOTLIST HIT: ${data.plate_text || data.plate}`,
    `${data.risk_level || 'CRITICAL'} hit at ${data.camera_name || 'Checkpoint'}. Immediate tactical action required.`,
    data.risk_level === "CRITICAL" ? "CRITICAL" : "HIGH"
  );

  // Reload alerts list
  if (window.loadAlerts) {
    window.loadAlerts();
  }
}

// ==========================================================================
// TOAST NOTIFICATION SYSTEM
// ==========================================================================
window.showToast = function(title, message, type = "info", duration = 5000) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast-alert risk-${type} toast-${type}`;
  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-msg">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()" aria-label="Dismiss">&times;</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 250);
  }, duration);
};

// ==========================================================================
// UNIVERSAL COMMAND PALETTE (CTRL+K / CMD+K)
// ==========================================================================
function initCommandPalette() {
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      openCommandPalette();
    }
    if (e.key === "Escape") {
      closeModal("cmd-palette-modal");
    }
  });
}

window.openCommandPalette = function() {
  openModal("cmd-palette-modal");
  const input = document.getElementById("cmd-palette-input");
  if (input) {
    input.value = "";
    input.focus();
    renderCommandPaletteDefault();
  }
};

function renderCommandPaletteDefault() {
  const resultsContainer = document.getElementById("cmd-palette-results");
  if (!resultsContainer) return;

  resultsContainer.innerHTML = `
    <div style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase; font-weight:700; padding:6px 10px;">Quick Actions &amp; Frequent Searches</div>
    <div class="cmd-result-item" onclick="openVehicleJourney('GJ01AB1234'); closeModal('cmd-palette-modal');">
      <div>
        <div style="font-weight:700; font-family:var(--font-mono);">GJ01AB1234 (Red Swift)</div>
        <div style="font-size:0.74rem; color:var(--text-muted);">Armed Robbery Suspect • High Risk Checkpoints</div>
      </div>
      <span class="alert-risk-badge risk-CRITICAL-badge">CRITICAL</span>
    </div>
    <div class="cmd-result-item" onclick="openVehicleJourney('GJ06XY9876'); closeModal('cmd-palette-modal');">
      <div>
        <div style="font-weight:700; font-family:var(--font-mono);">GJ06XY9876 (White Creta)</div>
        <div style="font-size:0.74rem; color:var(--text-muted);">Stolen Vehicle • Vadodara Expressway</div>
      </div>
      <span class="alert-risk-badge risk-HIGH-badge">HIGH</span>
    </div>
    <div class="cmd-result-item" onclick="switchToView('videowall-view'); closeModal('cmd-palette-modal');">
      <div>
        <div style="font-weight:700;">Switch to Live Video Wall (Grid)</div>
        <div style="font-size:0.74rem; color:var(--text-muted);">Live MJPEG surveillance matrix (cam01 - cam30)</div>
      </div>
      <span class="quick-tag-btn" style="font-size:0.68rem;">VIEW</span>
    </div>
    <div class="cmd-result-item" onclick="switchToView('scale-view'); closeModal('cmd-palette-modal');">
      <div>
        <div style="font-weight:700;">80,000 Statewide Capacity Calculator</div>
        <div style="font-size:0.74rem; color:var(--text-muted);">TCO bandwidth comparison &amp; in-process stress test</div>
      </div>
      <span class="quick-tag-btn" style="font-size:0.68rem;">TOOL</span>
    </div>
  `;
}

window.handleCommandPaletteSearch = function(event) {
  const query = event.target.value.trim().toLowerCase();
  const resultsContainer = document.getElementById("cmd-palette-results");
  if (!resultsContainer) return;

  if (!query) {
    renderCommandPaletteDefault();
    return;
  }

  const matches = [];

  // 1. Search Cameras
  if (window.allCamerasData && window.allCamerasData.length > 0) {
    window.allCamerasData.forEach(c => {
      if (
        c.name.toLowerCase().includes(query) ||
        c.logical_camera_id.toLowerCase().includes(query) ||
        c.district.toLowerCase().includes(query) ||
        c.vendor.toLowerCase().includes(query)
      ) {
        matches.push({
          type: "CAMERA",
          title: `${c.logical_camera_id}: ${c.name}`,
          subtitle: `${c.district} District • ${c.vendor} • ${c.resolution}`,
          action: () => {
            switchToView('gis-view');
            if (window.focusMapOnCamera) window.focusMapOnCamera(c.logical_camera_id);
          }
        });
      }
    });
  }

  // 2. Check evaluation test plates
  const testPlates = [
    { plate: "GJ01AB1234", desc: "Red Swift - Armed Robbery Hit", risk: "CRITICAL" },
    { plate: "GJ06XY9876", desc: "White Creta - Stolen Vehicle", risk: "HIGH" },
    { plate: "GJ05CD5521", desc: "Black Scorpio - Wanted Warrant", risk: "HIGH" },
    { plate: "GJ27EF8890", desc: "Blue Truck - Interstate Smuggling", risk: "MEDIUM" }
  ];

  testPlates.forEach(p => {
    if (p.plate.toLowerCase().includes(query) || p.desc.toLowerCase().includes(query)) {
      matches.push({
        type: "VEHICLE",
        title: `${p.plate} [${p.risk}]`,
        subtitle: p.desc,
        action: () => {
          openVehicleJourney(p.plate);
        }
      });
    }
  });

  if (matches.length === 0) {
    resultsContainer.innerHTML = `
      <div style="text-align:center; padding:24px; color:var(--text-muted);">
        No matching plates or cameras found for "<strong>${query}</strong>".
        <div style="margin-top:10px;">
          <button class="primary-search-btn" style="padding:6px 14px; font-size:0.75rem;" onclick="openVehicleJourney('${query.toUpperCase()}'); closeModal('cmd-palette-modal');">
            Track "${query.toUpperCase()}" as License Plate
          </button>
        </div>
      </div>
    `;
    return;
  }

  resultsContainer.innerHTML = matches.slice(0, 8).map((m, idx) => `
    <div class="cmd-result-item" onclick="matches[${idx}].action(); closeModal('cmd-palette-modal');">
      <div>
        <div style="font-weight:700;">${m.title}</div>
        <div style="font-size:0.74rem; color:var(--text-muted);">${m.subtitle}</div>
      </div>
      <span class="quick-tag-btn" style="font-size:0.68rem;">${m.type}</span>
    </div>
  `).join("");

  window._cmdMatches = matches;
};

function switchToView(viewId) {
  const btn = document.querySelector(`.nav-tab-btn[data-view="${viewId}"]`);
  if (btn) btn.click();
}

// ==========================================================================
// INITIAL DATA LOADER
// ==========================================================================
async function loadInitialData() {
  try {
    // 1. Load Camera Stats Summary
    const statsRes = await fetch("/api/cameras/stats/summary");
    if (statsRes.ok) {
      const stats = await statsRes.json();
      const totalEl = document.getElementById("stat-total-cams");
      const onlineEl = document.getElementById("stat-online-cams");
      const subEl = document.getElementById("stat-online-sub");

      if (totalEl) totalEl.textContent = stats.total_onboarded;
      if (onlineEl) onlineEl.textContent = stats.online_count;
      if (subEl) {
        const pct = stats.total_onboarded > 0 ? ((stats.online_count / stats.total_onboarded) * 100).toFixed(1) : "0.0";
        subEl.textContent = `${pct}% Live Measured Availability`;
      }
    }

    // 2. Initialize GIS Map & Load Cameras
    if (window.initGISMap) {
      await window.initGISMap();
    }

    // 3. Initialize Video Wall
    if (window.initVideoWall) {
      await window.initVideoWall();
    }

    // 4. Load Alerts
    if (window.loadAlerts) {
      await window.loadAlerts();
    }

    // 5. Load Watchlists
    if (window.loadWatchlist) {
      await window.loadWatchlist();
    }

    // 6. Initialize Scalability Simulator
    if (window.updateScaleSimulation) {
      window.updateScaleSimulation();
    }

  } catch (err) {
    console.error("Initial data load error:", err);
  }
}

// ==========================================================================
// MODAL UTILITIES
// ==========================================================================
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
};

window.closeModalOnBackdrop = function(event, modalId) {
  if (event.target && event.target.classList.contains("modal-backdrop")) {
    closeModal(modalId);
  }
};

// Quick trigger helper for vehicle journey
window.openVehicleJourney = function(plate) {
  switchToView("tracer-view");
  const searchInput = document.getElementById("vehicle-search-input");
  if (searchInput) searchInput.value = plate;
  if (window.executeVehicleSearch) {
    window.executeVehicleSearch();
  }
};
