# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `07152c10`
- **Execution Timestamp**: 2026-09-11T02:10:52.249833+00:00
- **Total Duration**: 159.87 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST1652')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-07152c10-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-07152c10-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '40c4ae20-3d9f-4aec-9289-6cd193f23c74')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-07152c10-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'aa17eb6a-ef48-4489-9a98-130f2ea5fd7a')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-DC0F409B5D94')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
