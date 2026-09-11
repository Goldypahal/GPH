# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `d1856d2b`
- **Execution Timestamp**: 2026-09-11T07:17:42.956010+00:00
- **Total Duration**: 140.47 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST2062')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-d1856d2b-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-d1856d2b-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', 'bb296d46-1988-4188-beeb-117d22798ffd')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-d1856d2b-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '1fcbadf9-f283-46eb-9651-4da7a51683ea')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-4DB46BE57F19')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
