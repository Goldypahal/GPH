# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `d71a2864`
- **Execution Timestamp**: 2026-09-14T05:21:04.410116+00:00
- **Total Duration**: 246.22 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST2264')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-d71a2864-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-d71a2864-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', 'c60138dd-5dc9-412e-aca2-0f64c9594266')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-d71a2864-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'e00f8614-6087-4f1a-962c-f1a80570b54d')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-52D1F7696E4E')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
