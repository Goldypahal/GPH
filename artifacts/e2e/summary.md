# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `904a2eed`
- **Execution Timestamp**: 2026-09-14T11:40:03.221915+00:00
- **Total Duration**: 123.71 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST7003')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-904a2eed-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-904a2eed-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '85f5a3c9-d07e-47bc-aa0f-1eeea215300a')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-904a2eed-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '7cb8b116-674f-42dc-bba8-63109486a98d')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-CEA165697E42')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
