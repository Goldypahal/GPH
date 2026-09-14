# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `b71d01cb`
- **Execution Timestamp**: 2026-09-14T09:01:33.784753+00:00
- **Total Duration**: 172.39 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST6493')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-b71d01cb-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-b71d01cb-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '71fad2ac-83c7-4f7e-9a99-614d7bbfda29')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-b71d01cb-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'fd23a337-b674-42a3-8e08-bdccead5ff36')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-601E2A8D53AA')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
