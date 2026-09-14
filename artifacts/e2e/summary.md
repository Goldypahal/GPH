# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `fdd93178`
- **Execution Timestamp**: 2026-09-14T06:15:18.100585+00:00
- **Total Duration**: 116.45 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST5517')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-fdd93178-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-fdd93178-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '34ba6a22-6455-4b60-929c-aed3d64740f1')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-fdd93178-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '8911e7d8-28fb-4aab-aa05-12ff336cc246')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-012DF5044B65')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
