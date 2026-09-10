// Section 65B Digital Evidence Certificate & Camera Onboarding Controller

async function openSection65BCertificate(sightingOrCamId) {
  const modal = document.getElementById("cert-modal");
  const content = document.getElementById("cert-content-render");
  if (!modal || !content) return;

  content.innerHTML = `<div style="text-align:center; padding:30px; color:var(--accent-cyan);">Generating cryptographically sealed Section 65B certificate...</div>`;
  openModal("cert-modal");

  try {
    const res = await fetch(`/api/evidence/${sightingOrCamId}/certificate`);
    if (!res.ok) {
      content.innerHTML = `<div style="text-align:center; padding:30px; color:#ef4444;">Unable to generate certificate for ID: ${sightingOrCamId}</div>`;
      return;
    }

    const cert = await res.json();
    const r = cert.electronic_record_details;
    const v = cert.cryptographic_verification;

    content.innerHTML = `
      <div class="cert-document">
        <div class="cert-header">
          <div class="cert-emblem">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1e293b" stroke-width="2"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path><path d="M7 21h10"></path><path d="M12 3v18"></path><path d="M3 7h18"></path></svg>
          </div>
          <div class="cert-h1">${cert.certificate_title}</div>
          <div class="cert-h2">[Issued under ${cert.legal_act_reference}]</div>
          <div style="font-size:11px; margin-top:4px; font-family:var(--font-mono); color:#475569;">
            Certificate Ref: <strong>${cert.certificate_id}</strong> | Date: ${cert.date_of_issuance}
          </div>
        </div>

        <div class="cert-body">
          <p>
            I, <strong>${cert.certifying_officer.name}</strong>, holding the post of <strong>${cert.certifying_officer.designation}</strong> at 
            <strong>${cert.certifying_officer.station}</strong>, being in lawful management and operational oversight of the computerized CCTV 
            video management apparatus, hereby solemnly certify and affirm as follows:
          </p>

          <div class="cert-grid">
            <div>
              <div><strong>Target Vehicle:</strong> ${r.target_vehicle_plate} (${r.vehicle_category}, ${r.vehicle_color})</div>
              <div><strong>Camera Identifier:</strong> ${r.camera_identifier}</div>
              <div><strong>Camera Name:</strong> ${r.camera_description}</div>
              <div><strong>Apparatus Hardware:</strong> ${r.device_hardware}</div>
            </div>
            <div>
              <div><strong>Time of Capture:</strong> ${r.timestamp_of_capture}</div>
              <div><strong>Location:</strong> ${r.geographical_coordinates.location_name}</div>
              <div><strong>GPS Coordinates:</strong> ${r.geographical_coordinates.latitude}° N, ${r.geographical_coordinates.longitude}° E</div>
              <div><strong>Recorded Speed & Confidence:</strong> ${r.speed_recorded_kmh} km/h (${r.detection_confidence})</div>
            </div>
          </div>

          <div style="font-weight:bold; margin-bottom:6px;">STATUTORY DECLARATIONS OF ACCURACY & PROPER OPERATION:</div>
          <ol style="margin-left:20px; font-size:12px; line-height:1.5;">
            ${cert.technical_integrity_declarations.map(d => `<li>${d.replace(/^\d+\.\s*/, '')}</li>`).join("")}
          </ol>

          <div class="cert-hash-box">
            <div><strong>CRYPTOGRAPHIC INTEGRITY SEAL (SHA-256):</strong></div>
            <div style="color:#0284c7; font-weight:bold;">${v.evidence_snapshot_sha256}</div>
            <div style="margin-top:4px;"><strong>HMAC-SHA256 LEGAL SIGNATURE:</strong></div>
            <div style="color:#16a34a; font-weight:bold;">${v.hmac_tamper_evident_signature}</div>
            <div style="margin-top:4px; color:#475569; font-size:11px;">
              Verification Status: <span style="color:#16a34a; font-weight:bold;">${v.verification_status}</span>
            </div>
            <div style="margin-top:8px; font-size:10px; color:#64748b; line-height:1.4; border-top:1px dashed #cbd5e1; padding-top:6px;">
              <strong>Legal Notice:</strong> Cryptographic integrity record prepared for authorized legal process. Actual statutory admissibility under Section 65B Indian Evidence Act 1872 / Section 63 Bharatiya Sakshya Adhiniyam 2023 requires execution of formal certificate affidavit by authorized custodian having lawful control of apparatus.
            </div>
          </div>

          <div class="cert-signature-block">
            <div>
              <div style="font-family:'Brush Script MT', cursive; font-size:24px; color:#0f172a; margin-bottom:4px;">V. K. Patel</div>
              <div class="cert-signature-line">
                <div><strong>${cert.certifying_officer.name}</strong></div>
                <div style="font-size:11px;">${cert.certifying_officer.designation}</div>
                <div style="font-size:11px;">Gujarat Police Technology Directorate</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

  } catch (err) {
    console.error("Certificate load error:", err);
  }
}

function openOnboardModal() {
  openModal("onboard-modal");
}

async function submitOnboardCamera(event) {
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
      alert(`Camera ${payload.logical_camera_id} onboarded successfully to GIVIN Registry!`);
      closeModal("onboard-modal");
      if (window.initGISMap) window.initGISMap();
      document.getElementById("onboard-form").reset();
    }
  } catch (err) {
    console.error("Failed to onboard camera:", err);
  }
}
