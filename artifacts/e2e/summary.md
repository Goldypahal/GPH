# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `0379d34b`
- **Execution Timestamp**: 2026-09-11T02:51:00.599385+00:00
- **Total Duration**: 134.97 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST4060')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-0379d34b-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-0379d34b-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '63d43651-cd46-4cdc-9b4b-4e0c50129c9d')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-0379d34b-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'b5e78713-c4c7-4550-8605-61b8b6c79be0')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-9D47349E6687')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
