# GIVIN — Day 1 End-to-End Pipeline Execution Summary

- **Run ID**: `55dc5ded`
- **Execution Timestamp**: 2026-09-14T06:30:10.578203+00:00
- **Total Duration**: 140.9 ms
- **Stages Passed**: 16 / 16 (100%)
- **Pipeline Verdict**: **PASSED_100_PERCENT**

## Functional Stage Breakdown

| # | Pipeline Stage | Status | Provenance / Key Metric |
|---|---|---|---|
| 1 | Camera Ingestion | **PASSED** | `MEASURED_STREAM_SOCKET` |
| 2 | Pts Timing | **PASSED** | `AUTHORITATIVE_MEDIA_PTS` |
| 3 | Vehicle Detection | **PASSED** | `('vehicle_type', 'SUV')` |
| 4 | Plate Localization | **PASSED** | `('plate_bbox', [120, 240, 280, 310])` |
| 5 | Anpr Ocr Normalization | **PASSED** | `('raw_text', 'GJ01ST6410')` |
| 6 | Bytetrack Tracking | **PASSED** | `('track_id', 'trk-55dc5ded-001')` |
| 7 | Canonical Sighting | **PASSED** | `('sighting_id', 'sight-55dc5ded-01')` |
| 8 | Event Bus Dispatch | **PASSED** | `('topic', 'camera.sightings')` |
| 9 | Watchlist Matching | **PASSED** | `('watchlist_id', '9f0d92bb-77f9-44ae-be8f-ef379d7a63a7')` |
| 10 |  Alert Generation | **PASSED** | `('alert_id', 'alt-55dc5ded-01')` |
| 11 |  Websocket Fanout | **PASSED** | `('endpoint', '/ws/alerts')` |
| 12 |  Cross Camera Correlation | **PASSED** | `GEODESIC_ESTIMATE` |
| 13 |  Case Management | **PASSED** | `('case_id', 'ef1ea041-e993-414a-8621-7317175db5f8')` |
| 14 |  Worm Evidence Vault | **PASSED** | `('evidence_id', 'EVID-B19032886CB9')` |
| 15 |  Evidence Integrity Verification | **PASSED** | `INTEGRITY_CONFIRMED` |
| 16 |  Audit And Custody Trail | **PASSED** | `('custody_entries', 2)` |
