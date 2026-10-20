import urllib.request
import json

def check(crop, dist, hrs, veh, pack, temp, hum, is_rain, mat, cooling):
    payload = {
        "items": [{
            "id": "lot-test",
            "barcode_no": "BC-000001",
            "crop_category": "Vegetable",
            "food_name": crop,
            "kg": 250,
            "destination_center": "Dambulla Dedicated Economic Centre",
            "origin_district": "Matale",
            "distance_km": dist,
            "transit_hours": hrs,
            "harvest_datetime": "2026-10-20T06:00:00Z",
            "transport_date": "2026-10-20",
            "transport_time": "08:00",
            "transport_type": veh,
            "vehicle_no": "NC-CP-1010",
            "packing_type": pack,
            "maturity": mat,
            "is_covered": True if "COVERED" in veh or "REFRIGERATED" in veh else False,
            "has_cooling": cooling,
            "is_washed": True,
            "is_graded": True,
            "ambient_temp_c": temp,
            "ambient_humidity_pct": hum,
            "is_rainy": is_rain
        }]
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8003/api/transport/predict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            item = data["items"][0]
            print(f"{crop:8} | {veh:16} | {pack:14} | {dist:3.0f}km | {hrs:3.1f}h | {temp:4.1f}C | {mat:10} | Rain:{str(is_rain):5} => Loss: {item['predicted_waste_pct']:5.2f}% | Tier: {item['risk_level']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("-" * 115)
    print("Crop     | Vehicle          | Packaging      | Dist  | Time | Temp  | Maturity   | Rain  => Spoilage % | Risk Tier")
    print("-" * 115)
    # Sturdy crops / cold chain (LOW)
    check("Potato", 25, 0.6, "COVERED_TRUCK", "PLASTIC_CRATE", 24.0, 70.0, False, "Under-ripe", False)
    check("Tomato", 20, 0.5, "REFRIGERATED_VAN", "PLASTIC_CRATE", 18.0, 65.0, False, "Under-ripe", True)
    check("Cabbage", 35, 0.8, "COVERED_TRUCK", "PLASTIC_CRATE", 22.0, 70.0, False, "Under-ripe", False)
    
    # Moderate regional trips (MEDIUM)
    check("Tomato", 30, 0.7, "COVERED_TRUCK", "PLASTIC_CRATE", 24.0, 75.0, False, "Ripe", False)
    check("Beans", 50, 1.2, "COVERED_TRUCK", "PLASTIC_CRATE", 26.0, 80.0, False, "Ripe", False)
    check("Carrot", 65, 1.5, "COVERED_TRUCK", "VENTILATED_BOX", 26.0, 75.0, False, "Ripe", False)

    # Adverse / High Loss trips (HIGH)
    check("Tomato", 48, 1.1, "OPEN_TRUCK", "PLASTIC_CRATE", 26.0, 92.0, True, "Ripe", False)
    check("Tomato", 95, 2.2, "OPEN_TRUCK", "POLYSACK_MESH", 32.0, 85.0, False, "Ripe", False)
    check("Tomato", 180, 4.5, "OPEN_TRUCK", "POLYSACK_MESH", 34.0, 90.0, True, "Over-ripe", False)
    print("-" * 115)
