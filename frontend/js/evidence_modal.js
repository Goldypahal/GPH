// Section 65B Digital Evidence Certificate & Camera Onboarding Controller
window.openSection65BCertificate = async function(sightingOrCamId) {
  const modal = document.getElementById("cert-modal");
  const content = document.getElementById("cert-content-render");
  if (!modal || !content) return;

  content.innerHTML = `<div style="text-align:center; padding:40px; color:var(--accent-cyan); font-family:var(--font-mono);">Generating cryptographically sealed Section 65B certificate...</div>`;
  openModal("cert-modal");

  try {
    const res = await fetch(`/api/evidence/${sightingOrCamId}/certificate`);
    if (!res.ok) {
      content.innerHTML = `<div style="text-align:center; padding:30px; color:var(--accent-red);">Unable to generate certificate for ID: ${sightingOrCamId}</div>`;
      return;
    }

    const cert = await res.json();
    const r = cert.electronic_record_details;
    const v = cert.cryptographic_verification;

    content.innerHTML = `
      <div class="cert-document">
        <div class="cert-header">
          <div class="cert-emblem">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path><path d="M7 21h10"></path><path d="M12 3v18"></path><path d="M3 7h18"></path></svg>
          </div>
          <div class="cert-h1">${cert.certificate_title}</div>
          <div class="cert-h2">[Issued under ${cert.legal_act_reference}]</div>
          <div style="font-size:0.75rem; margin-top:6px; font-family:var(--font-mono); color:var(--text-dim);">
            Certificate Ref: <strong style="color:var(--text-main);">${cert.certificate_id}</strong> | Date: ${cert.date_of_issuance}
          </div>
        </div>

        <div class="cert-body">
          <p style="margin-bottom:12px;">
            I, <strong>${cert.certifying_officer.name}</strong>, holding the post of <strong>${cert.certifying_officer.designation}</strong> at 
            <strong>${cert.certifying_officer.station}</strong>, being in lawful management and operational oversight of the computerized CCTV 
            video management apparatus, hereby solemnly certify and affirm as follows:
          </p>

          <div class="cert-grid">
            <div>
              <div><strong>Target Vehicle:</strong> ${r.target_vehicle_plate} (${r.vehicle_category}, ${r.vehicle_color})</div>
              <div><strong>Camera Identifier:</strong> <span style="font-family:var(--font-mono);">${r.camera_identifier}</span></div>
              <div><strong>Camera Description:</strong> ${r.camera_description}</div>
              <div><strong>Apparatus Hardware:</strong> ${r.device_hardware}</div>
            </div>
            <div>
              <div><strong>Time of Capture:</strong> ${r.timestamp_of_capture}</div>
              <div><strong>Location:</strong> ${r.geographical_coordinates.location_name}</div>
              <div><strong>GPS Coordinates:</strong> ${r.geographical_coordinates.latitude}° N, ${r.geographical_coordinates.longitude}° E</div>
              <div><strong>Speed &amp; Confidence:</strong> ${r.speed_recorded_kmh} km/h (${r.detection_confidence})</div>
            </div>
          </div>

          <div style="font-weight:700; margin:14px 0 6px; text-transform:uppercase; font-size:0.8rem; color:var(--text-main);">
            STATUTORY DECLARATIONS OF ACCURACY &amp; PROPER OPERATION:
          </div>
          <ol style="margin-left:22px; font-size:0.8rem; line-height:1.6; color:var(--text-muted);">
            ${cert.technical_integrity_declarations.map(d => `<li>${d.replace(/^\d+\.\s*/, '')}</li>`).join("")}
          </ol>

          <div class="cert-hash-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <strong style="color:var(--text-main);">CRYPTOGRAPHIC INTEGRITY SEAL (SHA-256):</strong>
              <button class="quick-tag-btn" style="padding:1px 6px; font-size:0.65rem;" onclick="copyToClipboard('${v.evidence_snapshot_sha256}', 'SHA-256 Hash')">Copy Hash</button>
            </div>
            <div style="color:var(--accent-cyan); font-weight:700; font-size:0.75rem;">${v.evidence_snapshot_sha256}</div>
            
            <div style="margin-top:8px;"><strong>HMAC-SHA256 LEGAL SIGNATURE:</strong></div>
            <div style="color:var(--accent-green); font-weight:700; font-size:0.75rem;">${v.hmac_tamper_evident_signature}</div>
            
            <div style="margin-top:8px; color:var(--text-dim); font-size:0.72rem;">
              Verification Status: <span style="color:var(--accent-green); font-weight:bold;">${v.verification_status}</span>
            </div>
            <div style="margin-top:10px; font-size:0.7rem; color:var(--text-dim); line-height:1.4; border-top:1px dashed var(--border-color); padding-top:8px;">
              <strong>Legal Notice:</strong> Cryptographic integrity record prepared for authorized legal process. Statutory admissibility under Section 65B Indian Evidence Act 1872 / Section 63 Bharatiya Sakshya Adhiniyam 2023 requires execution of formal affidavit by authorized custodian having lawful control of apparatus.
            </div>
          </div>

          <div class="cert-signature-block">
            <div>
              <div style="font-family:'Brush Script MT', cursive; font-size:26px; color:var(--text-main); margin-bottom:4px;">V. K. Patel</div>
              <div class="cert-signature-line">
                <div style="font-weight:700; color:var(--text-main);">${cert.certifying_officer.name}</div>
                <div style="font-size:0.75rem; color:var(--text-muted);">${cert.certifying_officer.designation}</div>
                <div style="font-size:0.72rem; color:var(--text-dim);">Gujarat Police Technology Directorate</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

  } catch (err) {
    console.error("Certificate load error:", err);
  }
};

window.copyToClipboard = function(text, label) {
  navigator.clipboard.writeText(text).then(() => {
    if (window.showToast) {
      window.showToast("COPIED TO CLIPBOARD", `${label} copied for verification.`, "success");
    }
  });
};

window.openOnboardModal = function() {
  openModal("onboard-modal");
};

window.submitOnboardCamera = async function(event) {
  event.preventDefault();

  const payload = {
    logical_camera_id: document.getElementById("onboard-code").value.trim(),
    name: document.getElementById("onboard-name").value.trim(),
    district: document.getElementById("onboard-district").value.trim(),
    location_name: document.getElementById("onboard-name").value.trim(),
    department_id: document.getElementById("onboard-dept").value,
    lat: parseFloat(document.getElementById("onboard-lat").value),
    lng: parseFloat(document.getElementById("onboard-lng").value),
    vendor: document.getElementById("onboard-vendor").value,
    protocol: document.getElementById("onboard-proto").value,
    resolution: "1080p",
    fps: 25,
    status: "ACTIVE"
  };

  try {
    const res = await fetch("/api/cameras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeModal("onboard-modal");
      if (window.showToast) {
        window.showToast("CAMERA ONBOARDED", `Camera ${payload.logical_camera_id} registered into GIVIN C4I network.`, "success");
      }
      if (window.initGISMap) window.initGISMap();
      document.getElementById("onboard-form").reset();
    } else {
      const err = await res.json();
      if (window.showToast) {
        window.showToast("ONBOARDING FAILED", err.detail || "Error registering camera.", "CRITICAL");
      }
    }
  } catch (err) {
    console.error("Failed to onboard camera:", err);
  }
};
