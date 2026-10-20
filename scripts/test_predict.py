import urllib.request
import json

def test_scenario(name, item):
    payload = {"items": [item]}
    req = urllib.request.Request(
        "http://127.0.0.1:8003/api/transport/predict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            pred_item = data["items"][0]
            print(f"=== {name} ===")
            print(f"Crop: {pred_item['food_name']}, Distance: {pred_item['distance_km']} km, Vehicle: {pred_item['transport_type']}, Packaging: {pred_item['packing_type']}")
            print(f"Loss Pct: {pred_item['predicted_waste_pct']}%, Loss Kg: {pred_item['predicted_waste_kg']} kg")
            print(f"Risk Tier: {pred_item['risk_level']}")
            print(f"Advice: {pred_item.get('advice', [])[:1]}")
            print()
    except Exception as e:
        print(f"Error testing {name}: {e}")

if __name__ == "__main__":
    # 1. Optimal Low Risk
    test_scenario("LOW RISK SCENARIO", {
        "id": "item-low",
        "barcode_no": "BC-000001",
        "crop_category": "Vegetable",
        "food_name": "Tomato",
        "kg": 200,
        "destination_center": "Dambulla Dedicated Economic Centre",
        "origin_district": "Matale",
        "distance_km": 18,
        "transit_hours": 0.5,
        "harvest_datetime": "2026-10-20T06:00:00Z",
        "transport_date": "2026-10-20",
        "transport_time": "07:00",
        "transport_type": "REFRIGERATED_VAN",
        "vehicle_no": "NC-CP-1111",
        "packing_type": "PLASTIC_CRATE",
        "maturity": "Under-ripe",
        "is_covered": True,
        "has_cooling": True,
        "is_washed": True,
        "is_graded": True,
        "ambient_temp_c": 22.0,
        "ambient_humidity_pct": 65.0,
        "is_rainy": False
    })

    # 2. Moderate Medium Risk
    test_scenario("MEDIUM RISK SCENARIO", {
        "id": "item-med",
        "barcode_no": "BC-000002",
        "crop_category": "Vegetable",
        "food_name": "Tomato",
        "kg": 350,
        "destination_center": "Dambulla Dedicated Economic Centre",
        "origin_district": "Matale",
        "distance_km": 48,
        "transit_hours": 1.1,
        "harvest_datetime": "2026-10-20T06:00:00Z",
        "transport_date": "2026-10-20",
        "transport_time": "08:00",
        "transport_type": "COVERED_TRUCK",
        "vehicle_no": "NC-CP-2222",
        "packing_type": "PLASTIC_CRATE",
        "maturity": "Ripe",
        "is_covered": True,
        "has_cooling": False,
        "is_washed": True,
        "is_graded": True,
        "ambient_temp_c": 26.0,
        "ambient_humidity_pct": 75.0,
        "is_rainy": False
    })

    # 3. High Risk
    test_scenario("HIGH RISK SCENARIO", {
        "id": "item-high",
        "barcode_no": "BC-000003",
        "crop_category": "Vegetable",
        "food_name": "Tomato",
        "kg": 500,
        "destination_center": "Meegoda Dedicated Economic Centre",
        "origin_district": "Jaffna",
        "distance_km": 380,
        "transit_hours": 8.0,
        "harvest_datetime": "2026-10-18T06:00:00Z",
        "transport_date": "2026-10-20",
        "transport_time": "12:00",
        "transport_type": "OPEN_TRUCK",
        "vehicle_no": "NC-CP-3333",
        "packing_type": "POLYSACK_MESH",
        "maturity": "Over-ripe",
        "is_covered": False,
        "has_cooling": False,
        "is_washed": False,
        "is_graded": False,
        "ambient_temp_c": 34.0,
        "ambient_humidity_pct": 92.0,
        "is_rainy": True
    })
