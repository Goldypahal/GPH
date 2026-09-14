// GIVIN Master App Controller
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initClock();
  initNavigation();
  loadInitialData();
});

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

function initClock() {
  const clockEl = document.getElementById("realtime-clock");
  const update = () => {
    const now = new Date();
    const istTime = now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
    clockEl.textContent = `${istTime} IST | ${now.toUTCString().slice(17, 25)} UTC`;
  };
  update();
  setInterval(update, 1000);
}

function initNavigation() {
  const tabBtns = document.querySelectorAll(".nav-tab-btn");
  const views = document.querySelectorAll(".view-section");

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

      // If GIS view selected, trigger Leaflet resize
      if (targetView === "gis-view" && window.gisMap) {
        setTimeout(() => {
          window.gisMap.invalidateSize();
        }, 150);
      }
      
      // If Video Wall selected, ensure feeds running
      if (targetView === "videowall-view" && window.renderVideoWall) {
        window.renderVideoWall();
      }
    });
  });
}

async function loadInitialData() {
  try {
    // 1. Load Camera Stats Summary
    const statsRes = await fetch("/api/cameras/stats/summary");
    if (statsRes.ok) {
      const stats = await statsRes.json();
      document.getElementById("stat-total-cams").textContent = stats.total_onboarded;
      document.getElementById("stat-online-cams").textContent = stats.online_count;
      const subEl = document.getElementById("stat-online-sub");
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

// Modal utilities
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
}

// Quick trigger helper for vehicle journey
function openVehicleJourney(plate) {
  const tabTracer = document.getElementById("tab-tracer");
  if (tabTracer) tabTracer.click();
  const searchInput = document.getElementById("vehicle-search-input");
  if (searchInput) searchInput.value = plate;
  if (window.executeVehicleSearch) {
    window.executeVehicleSearch();
  }
}
