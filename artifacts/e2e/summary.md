# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `daf4f08a`
- **Execution Timestamp**: 2026-09-10T11:52:35.522736+00:00
- **Total Duration**: 375.42 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST4155')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-daf4f08a-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-daf4f08a-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '2fe3434f-6c7b-4646-b10a-a3af5a52e32e')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-daf4f08a-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', '361735e7-78dc-4fa6-b61b-3993d37ee2d2')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-C2B4E3B0399D')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
