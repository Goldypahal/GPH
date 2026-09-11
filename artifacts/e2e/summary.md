# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `b0962d8f`
- **Execution Timestamp**: 2026-09-11T02:39:00.536123+00:00
- **Total Duration**: 129.47 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST3340')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-b0962d8f-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-b0962d8f-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '20686ad1-9b6e-4087-9501-95d78cf511bb')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-b0962d8f-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'ae69978c-4a04-435a-846c-aa644b45e34f')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-CCC62033E78A')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
