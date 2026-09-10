# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `8219fe3e`
- **Execution Timestamp**: 2026-09-10T11:12:05.000811+00:00
- **Total Duration**: 202.01 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST1724')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-8219fe3e-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-8219fe3e-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', 'b7c3e0ad-52e4-4cd2-a58f-ba9774c40269')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-8219fe3e-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '7a04b8b9-08d3-42dd-ab0e-75b5c2978769')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-36F488F6256C')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
