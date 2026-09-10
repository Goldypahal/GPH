# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `d760adb5`
- **Execution Timestamp**: 2026-09-10T12:04:46.345325+00:00
- **Total Duration**: 166.05 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST4886')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-d760adb5-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-d760adb5-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '774fd62b-f048-48ee-a1d3-403d5913f11f')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-d760adb5-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '5d972063-dc80-4731-83a1-17e1dedb0cab')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-BC94348D45E7')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
