// Watchlist Database Controller (VAHAN & eGujCop)
window.loadWatchlist = async function() {
  const container = document.getElementById("watchlist-table-container");
  if (!container) return;

  try {
    const res = await fetch("/api/watchlist");
    if (res.ok) {
      const items = await res.json();
      renderWatchlistTable(items);
    }
  } catch (err) {
    console.error("Failed to load watchlist:", err);
  }
};

function renderWatchlistTable(items) {
  const container = document.getElementById("watchlist-table-container");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">No entries in active watchlist.</div>`;
    return;
  }

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Plate Number</th>
          <th>Risk</th>
          <th>Vehicle Info</th>
          <th>Reason & Case FIR</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        ${items.map(item => `
          <tr>
            <td>
              <span class="alert-plate" style="font-size:0.85rem;">${item.vehicle_number}</span>
            </td>
            <td>
              <span class="alert-risk-badge risk-${item.risk_level}-badge">${item.risk_level}</span>
            </td>
            <td>
              <div style="font-weight:600;">${item.vehicle_make_model}</div>
              <div style="font-size:0.7rem; color:var(--text-dim);">${item.vehicle_color} | ${item.registered_authority}</div>
            </td>
            <td>
              <div style="font-size:0.75rem;">${item.reason}</div>
              <div style="font-size:0.7rem; color:var(--accent-cyan); font-family:var(--font-mono);">${item.case_fir_number}</div>
            </td>
            <td>
              <button class="quick-tag-btn" onclick="openVehicleJourney('${item.vehicle_number}')">Trace</button>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function openAddWatchlistModal() {
  openModal("watchlist-modal");
}

async function submitAddWatchlist(event) {
  event.preventDefault();

  const payload = {
    vehicle_number: document.getElementById("wl-plate").value.trim(),
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
      alert(`Vehicle ${payload.vehicle_number} successfully registered to statewide hotlist!`);
      closeModal("watchlist-modal");
      loadWatchlist();
      document.getElementById("watchlist-form").reset();
    }
  } catch (err) {
    console.error("Failed to add suspect:", err);
  }
}
