// Watchlist Database Controller (VAHAN & eGujCop) — Production Hotlist Engine
let allWatchlistItems = [];

window.loadWatchlist = async function() {
  const container = document.getElementById("watchlist-table-container");
  if (!container) return;

  try {
    const res = await fetch("/api/watchlist");
    if (res.ok) {
      allWatchlistItems = await res.json();
      renderWatchlistTable(allWatchlistItems);
    }
  } catch (err) {
    console.error("Failed to load watchlist:", err);
  }
};

function renderWatchlistTable(items) {
  const container = document.getElementById("watchlist-table-container");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">No entries found in active watchlist.</div>`;
    return;
  }

  container.innerHTML = `
    <div style="margin-bottom:10px;">
      <input type="text" id="watchlist-search-filter" class="form-input" placeholder="Filter hotlist by plate, make, FIR, reason..." onkeyup="filterWatchlistTable(this.value)" style="padding:6px 12px; font-size:0.8rem;">
    </div>
    <div style="overflow-x:auto;">
      <table class="data-table">
        <thead>
          <tr>
            <th>Plate Number</th>
            <th>Risk</th>
            <th>Vehicle Info</th>
            <th>Reason &amp; Case FIR</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="watchlist-tbody">
          ${items.map(item => `
            <tr>
              <td>
                <span class="alert-plate" style="font-size:0.85rem;">${item.vehicle_number}</span>
              </td>
              <td>
                <span class="alert-risk-badge risk-${item.risk_level}-badge">${item.risk_level}</span>
              </td>
              <td>
                <div style="font-weight:700; color:var(--text-main);">${item.vehicle_make_model}</div>
                <div style="font-size:0.7rem; color:var(--text-dim);">${item.vehicle_color} • ${item.registered_authority}</div>
              </td>
              <td>
                <div style="font-size:0.76rem; color:var(--text-muted);">${item.reason}</div>
                <div style="font-size:0.7rem; color:var(--accent-cyan); font-family:var(--font-mono); font-weight:600;">${item.case_fir_number}</div>
              </td>
              <td>
                <button class="quick-tag-btn" onclick="openVehicleJourney('${item.vehicle_number}')" title="Reconstruct Trajectory">
                  <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                  <span>Trace</span>
                </button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

window.filterWatchlistTable = function(query) {
  const q = query.trim().toLowerCase();
  const filtered = allWatchlistItems.filter(item => 
    item.vehicle_number.toLowerCase().includes(q) ||
    item.vehicle_make_model.toLowerCase().includes(q) ||
    item.case_fir_number.toLowerCase().includes(q) ||
    item.reason.toLowerCase().includes(q) ||
    item.risk_level.toLowerCase().includes(q)
  );

  const tbody = document.getElementById("watchlist-tbody");
  if (!tbody) return;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">No matching hotlist records.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(item => `
    <tr>
      <td>
        <span class="alert-plate" style="font-size:0.85rem;">${item.vehicle_number}</span>
      </td>
      <td>
        <span class="alert-risk-badge risk-${item.risk_level}-badge">${item.risk_level}</span>
      </td>
      <td>
        <div style="font-weight:700; color:var(--text-main);">${item.vehicle_make_model}</div>
        <div style="font-size:0.7rem; color:var(--text-dim);">${item.vehicle_color} • ${item.registered_authority}</div>
      </td>
      <td>
        <div style="font-size:0.76rem; color:var(--text-muted);">${item.reason}</div>
        <div style="font-size:0.7rem; color:var(--accent-cyan); font-family:var(--font-mono); font-weight:600;">${item.case_fir_number}</div>
      </td>
      <td>
        <button class="quick-tag-btn" onclick="openVehicleJourney('${item.vehicle_number}')">
          <svg class="ui-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          <span>Trace</span>
        </button>
      </td>
    </tr>
  `).join("");
};

window.openAddWatchlistModal = function() {
  openModal("watchlist-modal");
};

window.submitAddWatchlist = async function(event) {
  event.preventDefault();

  const payload = {
    vehicle_number: document.getElementById("wl-plate").value.trim().toUpperCase(),
    vehicle_make_model: document.getElementById("wl-model").value.trim(),
    vehicle_color: document.getElementById("wl-color").value.trim(),
    risk_level: document.getElementById("wl-risk").value,
    case_fir_number: document.getElementById("wl-fir").value.trim(),
    reason: document.getElementById("wl-reason").value.trim(),
    registered_authority: "Gujarat Police C4I / eGujCop",
    list_name: "State Police Central Hotlist"
  };

  try {
    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeModal("watchlist-modal");
      if (window.showToast) {
        window.showToast("REGISTERED TO HOTLIST", `Vehicle ${payload.vehicle_number} broadcast to statewide cameras.`, "success");
      }
      loadWatchlist();
      document.getElementById("watchlist-form").reset();
    } else {
      const err = await res.json();
      if (window.showToast) {
        window.showToast("REGISTRATION FAILED", err.detail || "Failed to register vehicle.", "CRITICAL");
      }
    }
  } catch (err) {
    console.error("Failed to add suspect:", err);
  }
};
