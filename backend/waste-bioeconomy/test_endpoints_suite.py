"""
Comprehensive Integration Test Suite for Component 3 FastAPI Endpoints
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
"""

import os
import sys

# Set working directory to backend/waste-bioeconomy
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_and_health():
    print("\n[TEST 1] Testing Root & Health Endpoints...")
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Root returned {res_root.status_code}"
    root_json = res_root.json()
    assert root_json["component"] == "Component 03"
    print("  --> Root endpoint passed:", root_json["service"])

    res_health = client.get("/health")
    assert res_health.status_code == 200, f"Health returned {res_health.status_code}"
    health_json = res_health.json()
    assert health_json["status"] == "healthy"
    print("  --> Health endpoint passed: status =", health_json["status"])


def test_risk_prediction():
    print("\n[TEST 2] Testing Spoilage Risk Prediction Endpoint...")
    # Scenario A: Tomato in Open Truck (Conventional Stress)
    payload_a = {
        "crop_name": "Tomato",
        "payload_kg": 1000.0,
        "distance_km": 148.0,
        "transit_hours": 5.5,
        "ambient_temperature_c": 32.5,
        "ambient_humidity_pct": 78.0,
        "vehicle_type": "OPEN_TRUCK",
        "road_condition": "POOR",
        "packaging_type": "POLYSACK_MESH",
        "route": "DAMBULLA - COLOMBO",
        "season": "YALA"
    }
    res_a = client.post("/api/v1/risk/predict", json=payload_a)
    assert res_a.status_code == 200, f"Predict failed: {res_a.text}"
    data_a = res_a.json()
    assert data_a["risk_tier"] in ["LOW", "MEDIUM", "HIGH"]
    assert data_a["predicted_spoilage_loss_pct"] > 15.0
    # Mass conservation verification
    total_reconstructed = data_a["stream_1_fresh_produce_kg"] + data_a["stream_2_bioeconomy_feedstock_kg"]
    assert abs(total_reconstructed - 1000.0) < 0.1
    print(f"  --> Tomato (Open Truck): Loss={data_a['predicted_spoilage_loss_pct']}%, Tier={data_a['risk_tier']}")
    print(f"      Stream 1 Fresh: {data_a['stream_1_fresh_produce_kg']} kg | Stream 2 Cull: {data_a['stream_2_bioeconomy_feedstock_kg']} kg")

    # Scenario B: Tomato in Refrigerated Van (Cold Chain Mitigation)
    payload_b = {
        "crop_name": "Tomato",
        "payload_kg": 1000.0,
        "distance_km": 148.0,
        "transit_hours": 5.5,
        "ambient_temperature_c": 32.5,
        "ambient_humidity_pct": 78.0,
        "vehicle_type": "REFRIGERATED_VAN",
        "road_condition": "GOOD",
        "packaging_type": "PLASTIC_CRATE",
        "route": "DAMBULLA - COLOMBO",
        "season": "YALA"
    }
    res_b = client.post("/api/v1/risk/predict", json=payload_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["predicted_spoilage_loss_pct"] < data_a["predicted_spoilage_loss_pct"]
    assert data_b["risk_tier"] == "LOW"
    print(f"  --> Tomato (Cold Chain): Loss={data_b['predicted_spoilage_loss_pct']}%, Tier={data_b['risk_tier']}")


def test_benchmark_and_feature_importance():
    print("\n[TEST 3] Testing Benchmark & Feature Importance Endpoints...")
    res_bench = client.get("/api/v1/risk/benchmark")
    assert res_bench.status_code == 200
    bench_data = res_bench.json()
    assert len(bench_data["benchmark_comparison"]) >= 4
    xgb_row = next(r for r in bench_data["benchmark_comparison"] if "XGBoost" in r["model_name"])
    assert xgb_row["rmse_pct"] == 1.44
    assert xgb_row["accuracy_pct"] == 81.98
    print(f"  --> Benchmark Table Verified: XGBoost RMSE={xgb_row['rmse_pct']}%, Accuracy={xgb_row['accuracy_pct']}%")

    res_feat = client.get("/api/v1/risk/feature-importance")
    assert res_feat.status_code == 200
    feat_data = res_feat.json()
    assert "ranking" in feat_data
    top_feature = feat_data["ranking"][0]
    print(f"  --> Top Ranked Feature: {top_feature[0]} (Importance: {top_feature[1]:.4f})")

    res_crops = client.get("/api/v1/risk/crops")
    assert res_crops.status_code == 200
    crops = res_crops.json()
    assert "Tomato" in crops and "Big Onion" in crops and "Okra" in crops
    print(f"  --> Agronomic Crops Catalogue: {len(crops)} focal crops loaded.")


def test_feedstocks_and_compost_optimizer():
    print("\n[TEST 4] Testing Compost Optimization & Feedstocks Catalogue...")
    res_feed = client.get("/api/v1/compost/feedstocks")
    assert res_feed.status_code == 200
    feedstocks = res_feed.json()
    assert len(feedstocks) >= 7
    print(f"  --> Feedstock Database: {len(feedstocks)} items active.")

    # Aerobic composting optimization request
    blend_req = {
        "incoming_waste_name": "Tomato Cull Waste",
        "incoming_waste_kg": 250.0,
        "incoming_moisture_pct": 94.1,
        "incoming_c_n_ratio": 13.5,
        "target_batch_kg": 1000.0,
        "min_cn": 25.0,
        "max_cn": 30.0,
        "min_moisture": 55.0,
        "max_moisture": 65.0,
        "min_inoculant_pct": 5.0,
        "allow_biogas_fallback": False
    }
    res_opt = client.post("/api/v1/compost/optimize-blend", json=blend_req)
    assert res_opt.status_code == 200, f"Compost opt failed: {res_opt.text}"
    opt_data = res_opt.json()
    assert opt_data["is_feasible"] is True
    assert opt_data["routing_destination"] == "AEROBIC_COMPOSTING"
    assert 25.0 <= opt_data["mix_c_n_ratio"] <= 30.0
    assert 55.0 <= opt_data["mix_moisture_pct"] <= 65.0
    assert opt_data["slsi_compliance_audit"]["overall_certified_compliant"] is True
    print(f"  --> Aerobic Compost Recipe Solved: Batch={opt_data['total_batch_mass_kg']}kg, C:N={opt_data['mix_c_n_ratio']}:1, Moisture={opt_data['mix_moisture_pct']}%")
    print(f"      Total Cost: LKR {opt_data['total_batch_cost_lkr']:.2f} | SLSI 1246 Certified: {opt_data['slsi_compliance_audit']['overall_certified_compliant']}")


def test_biogas_fallback():
    print("\n[TEST 5] Testing Automated Anaerobic Biogas Fallback...")
    biogas_req = {
        "incoming_waste_name": "Hyper-Aqueous Rotting Tomato Slurry",
        "incoming_waste_kg": 500.0,
        "incoming_moisture_pct": 95.0,
        "incoming_c_n_ratio": 12.0,
        "allow_biogas_fallback": True
    }
    res_bio = client.post("/api/v1/compost/optimize-blend", json=biogas_req)
    assert res_bio.status_code == 200
    bio_data = res_bio.json()
    assert bio_data["routing_destination"] == "ANAEROBIC_BIOGAS_DIVERSION"
    assert bio_data["biogas_metrics"] is not None
    bm = bio_data["biogas_metrics"]
    print(f"  --> Biogas Fallback Triggered: Methane={bm['methane_yield_m3']} m3, Electricity={bm['green_electricity_kwh']} kWh, CO2e Avoided={bm['avoided_ghg_emissions_kg_co2e']} kg")


def test_end_to_end_consignment():
    print("\n[TEST 6] Testing End-to-End In-Transit Dispatch Endpoint...")
    telemetry_req = {
        "crop_name": "Tomato",
        "payload_kg": 1500.0,
        "distance_km": 148.0,
        "transit_hours": 6.0,
        "ambient_temperature_c": 33.0,
        "ambient_humidity_pct": 80.0,
        "vehicle_type": "COVERED_TRUCK",
        "road_condition": "POOR",
        "packaging_type": "POLYSACK_MESH",
        "route": "DAMBULLA - COLOMBO",
        "season": "YALA"
    }
    res_e2e = client.post("/api/v1/compost/end-to-end", json=telemetry_req)
    assert res_e2e.status_code == 200, f"End-to-End failed: {res_e2e.text}"
    e2e_data = res_e2e.json()
    summary = e2e_data["consignment_summary"]
    recipe = e2e_data["bioeconomy_solution"]
    assert summary["crop_name"] == "Tomato"
    assert summary["predicted_spoilage_loss_pct"] > 0
    assert recipe["is_feasible"] is True
    print(f"  --> End-to-End Success: Incoming={summary['total_payload_kg']}kg")
    print(f"      Stream 1 Fresh Produce: {summary['stream_1_fresh_produce_kg']}kg ({summary['stream_1_fresh_pct']}%) -> {summary['stream_1_recommended_channel']}")
    print(f"      Stream 2 Cull Waste   : {summary['stream_2_bioeconomy_feedstock_kg']}kg ({summary['stream_2_waste_pct']}%) -> {summary['stream_2_destination']}")
    print(f"      Recipe Batch Mass     : {recipe['total_batch_mass_kg']}kg (Mix C:N: {recipe['mix_c_n_ratio']}:1)")


def test_fertilizer_demand_matching():
    print("\n[TEST 7] Testing Fertilizer Demand Matching & Agronomic Growth-Stage Rules...")
    # 1. Fetch clusters and growth stages
    res_clusters = client.get("/api/v1/fertilizer/clusters")
    assert res_clusters.status_code == 200
    clusters = res_clusters.json()
    assert len(clusters) >= 6
    print(f"  --> Regional Clusters Loaded: {len(clusters)} clusters across Dambulla and Anuradhapura.")

    res_stages = client.get("/api/v1/fertilizer/growth-stages")
    assert res_stages.status_code == 200
    stages = res_stages.json()
    assert "FLOWERING_FRUIT_SET" in stages
    print("  --> DoA Growth-Stage Rules Verified.")

    # 2. Test Demand Matching Request
    match_payload = {
        "hub_id": "HUB-DAMBULLA",
        "demands": [
            {
                "farmer_id": "FARM-01",
                "farmer_name": "Sunil Bandara",
                "cluster_id": "CL-DAM-01",
                "cluster_name": "Kandalama North Cluster",
                "crop_name": "Tomato",
                "acreage_ha": 1.5,
                "growth_stage": "BASAL_LAND_PREP",
                "latitude": 7.8540,
                "longitude": 80.7020
            },
            {
                "farmer_id": "FARM-02",
                "farmer_name": "Anura Jayalath",
                "cluster_id": "CL-DAM-02",
                "cluster_name": "Galewela Mixed Vegetable",
                "crop_name": "Brinjal",
                "acreage_ha": 1.0,
                "growth_stage": "VEGETATIVE_GROWTH",
                "latitude": 7.7560,
                "longitude": 80.5720
            },
            {
                "farmer_id": "FARM-03",
                "farmer_name": "Gamini Wickramasinghe",
                "cluster_id": "CL-DAM-03",
                "cluster_name": "Sigiriya Agro-Forestry",
                "crop_name": "Tomato",
                "acreage_ha": 1.2,
                "growth_stage": "FLOWERING_FRUIT_SET",
                "latitude": 7.9540,
                "longitude": 80.7280
            }
        ]
    }
    res_match = client.post("/api/v1/fertilizer/match-demand", json=match_payload)
    assert res_match.status_code == 200, f"Match failed: {res_match.text}"
    m_data = res_match.json()
    assert m_data["total_farms_served"] == 3
    assert m_data["total_urea_displaced_kg"] > 0
    assert m_data["total_foreign_exchange_savings_lkr"] > 0

    # Verify DoA Growth Stage Rule: FARM-03 in FLOWERING_FRUIT_SET MUST NOT receive liquid digestate!
    farm_03_alloc = next(a for a in m_data["allocations"] if a["farmer_id"] == "FARM-03")
    assert farm_03_alloc["allocated_fertilizer_category"] == "SOLID_ORGANIC_COMPOST"
    assert farm_03_alloc["mismatch_warning"] is not None
    print(f"  --> DoA Agronomic Safety Filter Passed: {farm_03_alloc['mismatch_warning'][:80]}...")
    print(f"  --> Chemical Fertilizer Displaced: {m_data['total_urea_displaced_kg']:.1f}kg Urea, {m_data['total_tsp_displaced_kg']:.1f}kg TSP, {m_data['total_mop_displaced_kg']:.1f}kg MOP")
    print(f"  --> National Foreign Exchange Savings: LKR {m_data['total_foreign_exchange_savings_lkr']:,.2f}")


def test_logistics_dispatch_routing():
    print("\n[TEST 8] Testing Capacitated Vehicle Routing (CVRP) & Dispatch Manifests...")
    dispatch_payload = {
        "hub_id": "HUB-DAMBULLA",
        "preferred_vehicle_type": "MEDIUM_TRUCK"
    }
    res_disp = client.post("/api/v1/fertilizer/optimize-dispatch", json=dispatch_payload)
    assert res_disp.status_code == 200, f"Dispatch failed: {res_disp.text}"
    d_data = res_disp.json()
    assert len(d_data["manifests"]) >= 1
    m0 = d_data["manifests"][0]
    assert m0["total_transit_distance_km"] > 0
    assert m0["diesel_consumed_liters"] > 0
    assert m0["fuel_cost_lkr"] > 0
    assert len(m0["waypoints"]) >= 1
    print(f"  --> CVRP 2-Opt Manifest Generated: {m0['manifest_id']} ({m0['vehicle_name']})")
    print(f"      Assigned Payload: {m0['assigned_payload_kg']} kg ({m0['capacity_utilization_pct']}% utilization)")
    print(f"      Distance: {m0['total_transit_distance_km']} km | Fuel: {m0['diesel_consumed_liters']} L Diesel (@ LKR 350/L = LKR {m0['fuel_cost_lkr']:,.2f})")
    print(f"      Unit Delivery Cost: LKR {m0['unit_delivery_cost_lkr_kg']:.2f}/kg | Scope 1 GHG: {m0['transport_ghg_emissions_kg_co2e']:.2f} kg CO2e")


def test_circular_redistribution_end_to_end():
    print("\n[TEST 9] Testing Complete Closed-Loop Circular Bioeconomy Redistribution...")
    req_payload = {
        "hub_id": "HUB-DAMBULLA"
    }
    res_loop = client.post("/api/v1/fertilizer/end-to-end-redistribution", json=req_payload)
    assert res_loop.status_code == 200, f"Loop failed: {res_loop.text}"
    loop_data = res_loop.json()
    assert loop_data["status"] == "CIRCULAR_REDISTRIBUTION_SOLVED"
    assert "nutrient_demand_matching" in loop_data
    assert "logistics_dispatch_plan" in loop_data
    print("  --> Closed-loop circular redistribution successfully reconciled demand matching with delivery manifests!")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING COMPREHENSIVE FASTAPI & OPTIMIZATION INTEGRATION TEST SUITE")
    print("=" * 80)
    test_root_and_health()
    test_risk_prediction()
    test_benchmark_and_feature_importance()
    test_feedstocks_and_compost_optimizer()
    test_biogas_fallback()
    test_end_to_end_consignment()
    test_fertilizer_demand_matching()
    test_logistics_dispatch_routing()
    test_circular_redistribution_end_to_end()
    print("\n" + "=" * 80)
    print("ALL 9 TEST PHASES PASSED WITH 100% SUCCESS!")
    print("=" * 80)

