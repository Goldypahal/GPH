"""
Phase G Verification Test Suite:
Statewide Scalability (~80,000 Cameras), Mathematical Sizing Engine & Ingestion Stress Test.
"""

import os
import sys
import pytest

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.benchmarks.scale_benchmark import ScaleBenchmarkEngine


client = TestClient(app)


def test_scale_mathematical_model():
    """Validates mathematical bandwidth, storage, GPU, and financial models for 80,000 cameras."""
    model = ScaleBenchmarkEngine.calculate_architecture_comparison(
        camera_count=80000,
        resolution="1080p",
        retention_days=30,
        fps=25
    )

    assert model.camera_count == 80000
    assert model.central_model4_bandwidth_gbps == 320.0
    assert model.central_storage_petabytes > 100.0  # ~103.68 PB
    assert model.central_gpu_nodes_required == 5000

    # GIVIN Hybrid edge savings
    assert model.hybrid_model_bandwidth_gbps < 10.0
    assert model.hybrid_edge_storage_petabytes < 5.0
    assert model.bandwidth_savings_percentage >= 95.0
    assert model.storage_savings_percentage >= 95.0
    assert model.estimated_annual_cost_savings_inr_crores > 100.0  # > INR 100 Crores
    assert "MODELED" in model.verdict
    assert "Illustrative TCO" in model.tco_disclaimer
    assert "Derived estimate" in model.bandwidth_model_assumptions
    print(f"[PASS] test_scale_mathematical_model passed (Savings: {model.bandwidth_savings_percentage}% BW, INR {model.estimated_annual_cost_savings_inr_crores} Cr/yr).")


def test_synthetic_scale_ingestion_throughput():
    """Validates in-process real per-event latency, throughput, and packet acceptance."""
    res = ScaleBenchmarkEngine.run_synthetic_ingestion_benchmark(
        camera_count=5000,
        batch_size=250,
        max_events=5000
    )

    assert res.total_events_generated == 5000
    assert res.events_accepted == 5000
    assert res.events_failed == 0
    assert res.throughput_events_per_sec > 250.0  # High-throughput in-process pipeline throughput
    assert res.latency_p95_ms > 0.0  # True empirical per-event latency measured
    assert res.latency_p95_ms < 50.0  # Sub-50ms p95 latency
    assert res.packet_loss_percentage == 0.0
    assert "IN_PROCESS" in res.status
    assert res.benchmark_type == "APPLICATION_LAYER_SYNTHETIC_INGESTION"
    assert res.git_commit != ""
    assert res.environment["cpu_logical_cores"] > 0
    print(f"[PASS] test_synthetic_scale_ingestion_throughput passed (Throughput: {res.throughput_events_per_sec:,.0f} MPS, real per-event p95: {res.latency_p95_ms}ms).")


def test_scale_benchmark_api_endpoints():
    """Tests POST /api/system/scale-benchmark/run and GET /api/system/scale-benchmark/specs."""
    # 1. Run live benchmark via API
    post_res = client.post(
        "/api/system/scale-benchmark/run",
        json={"camera_count": 2000, "batch_size": 200, "max_events": 2000}
    )
    assert post_res.status_code == 200, post_res.text
    run_data = post_res.json()
    assert run_data["target_camera_count"] == 2000
    assert run_data["total_events_generated"] == 2000
    assert run_data["events_accepted"] == 2000
    assert run_data["events_failed"] == 0
    assert "IN_PROCESS" in run_data["status"]
    assert run_data["packet_loss_percentage"] == 0.0
    assert run_data["benchmark_type"] == "APPLICATION_LAYER_SYNTHETIC_INGESTION"
    assert "This is an application-layer synthetic benchmark" in run_data["methodology_disclaimer"]

    # 2. Query formal tender compliance specs
    specs_res = client.get("/api/system/scale-benchmark/specs")
    assert specs_res.status_code == 200, specs_res.text
    specs = specs_res.json()
    assert specs["statewide_scope"]["target_cameras"] == 80000
    assert specs["statewide_scope"]["governing_departments"] == 26
    assert specs["statewide_scope"]["districts_covered"] == 33
    assert "performance_targets" in specs
    assert "< 30 ms" in specs["performance_targets"]["anpr_latency_edge"]
    assert "Section 65B" in specs["legal_compliance"]["indian_evidence_act"]
    print(f"[PASS] test_scale_benchmark_api_endpoints passed (Live stress test & tender specs verified with explicit targets).")


def test_end_to_end_scale_calculator_api():
    """Tests GET /api/system/scale-calculator endpoint."""
    res = client.get("/api/system/scale-calculator?camera_count=80000&resolution=1080p&retention_days=30")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["camera_count"] == 80000
    assert data["bandwidth_savings_percentage"] > 90.0
    assert data["estimated_annual_cost_savings_inr_crores"] > 50.0
    print(f"[PASS] test_end_to_end_scale_calculator_api passed ({data['bandwidth_savings_percentage']}% savings).")


if __name__ == "__main__":
    test_scale_mathematical_model()
    test_synthetic_scale_ingestion_throughput()
    test_scale_benchmark_api_endpoints()
    test_end_to_end_scale_calculator_api()
    print("\n*** ALL PHASE G SCALE & SYSTEM TESTS PASSED WITH 100% SUCCESS!")
