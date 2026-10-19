"""
Capacitated Vehicle Routing & Distribution Logistics Engine
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks & Waste Management
Student: Lakruwan W.M.K. (IT23330382)
Project: J26-IT-358
Supervised by: Prof. Dasuni Nawinna

Features:
1. Solves the Capacitated Vehicle Routing Problem (CVRP) with 2-Opt heuristic optimization.
2. Models Sri Lankan regional road networks with rural tortuosity factor (1.25x) and elevation gradients.
3. Computes diesel fuel consumption (@ LKR 350.00/L) and Scope 1 transport GHG emissions (2.68 kg CO2e/L).
4. Generates vehicle dispatch manifests for Dambulla Dedicated Economic Centre and Negama/Anuradhapura Agrarian Hub.
"""

import math
from dataclasses import dataclass, field
from typing import Any

# Regional Bioeconomy Processing & Distribution Hubs
REGIONAL_HUBS: dict[str, dict[str, Any]] = {
    "HUB-DAMBULLA": {
        "hub_name": "Dambulla Dedicated Economic Centre Bio-Hub",
        "latitude": 7.8731,
        "longitude": 80.6517,
        "region": "Dambulla / Matale North",
    },
    "HUB-NEGAMA": {
        "hub_name": "Negama Agrarian Service Centre Bio-Hub",
        "latitude": 8.1337,
        "longitude": 80.3956,
        "region": "Anuradhapura / Mahaweli H",
    },
}

# Vehicle Fleet Configurations
VEHICLE_FLEET_CONFIGS: dict[str, dict[str, Any]] = {
    "MEDIUM_TRUCK": {
        "name": "Isuzu Elf 4-Ton Commercial Tipper",
        "capacity_kg": 2500.0,
        "fuel_economy_km_l": 7.5,
        "fixed_dispatch_cost_lkr": 2500.0,
        "driver_crew_cost_lkr_h": 600.0,
    },
    "HEAVY_TRUCK": {
        "name": "Tata LPK 912 Heavy Organic Transporter",
        "capacity_kg": 5000.0,
        "fuel_economy_km_l": 5.0,
        "fixed_dispatch_cost_lkr": 4500.0,
        "driver_crew_cost_lkr_h": 800.0,
    },
    "LIGHT_TRUCK": {
        "name": "Mahindra Bolero Maxi Agrarian Pickup",
        "capacity_kg": 1000.0,
        "fuel_economy_km_l": 11.0,
        "fixed_dispatch_cost_lkr": 1500.0,
        "driver_crew_cost_lkr_h": 450.0,
    },
}


@dataclass
class DeliveryWaypoint:
    stop_number: int
    farmer_id: str
    farmer_name: str
    cluster_name: str
    latitude: float
    longitude: float
    dropoff_fertilizer_category: str
    dropoff_mass_kg: float
    distance_from_prev_stop_km: float
    cumulative_distance_km: float
    estimated_arrival_minutes: float


@dataclass
class VehicleDispatchManifest:
    manifest_id: str
    vehicle_type: str
    vehicle_name: str
    capacity_kg: float
    assigned_payload_kg: float
    capacity_utilization_pct: float
    origin_hub_name: str
    origin_latitude: float
    origin_longitude: float
    total_transit_distance_km: float
    total_transit_hours: float
    diesel_consumed_liters: float
    fuel_cost_lkr: float
    crew_labor_cost_lkr: float
    fixed_dispatch_cost_lkr: float
    total_trip_cost_lkr: float
    unit_delivery_cost_lkr_kg: float
    transport_ghg_emissions_kg_co2e: float
    waypoints: list[DeliveryWaypoint] = field(default_factory=list)


@dataclass
class RegionalLogisticsPlan:
    plan_id: str
    origin_hub_id: str
    origin_hub_name: str
    total_fertilizer_dispatched_kg: float
    total_distance_covered_km: float
    total_diesel_liters: float
    total_logistics_cost_lkr: float
    average_unit_cost_lkr_kg: float
    total_ghg_emissions_kg_co2e: float
    active_vehicles_count: int
    manifests: list[VehicleDispatchManifest] = field(default_factory=list)
    logistics_notes: list[str] = field(default_factory=list)


def calculate_haversine_road_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, tortuosity: float = 1.25
) -> float:
    """
    Computes road transit distance in kilometers using the Haversine formula
    adjusted by Sri Lankan regional road tortuosity factor (1.25x).
    """
    r_earth = 6371.0  # Earth's mean radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    straight_line_km = r_earth * c
    return straight_line_km * tortuosity


def two_opt_optimize_route(
    coords: list[tuple[float, float]],
    hub_coord: tuple[float, float]
) -> list[int]:
    """
    Applies the 2-Opt local search trajectory heuristic to minimize route distance.
    Returns the permutation of destination indices.
    """
    n = len(coords)
    if n <= 1:
        return list(range(n))

    # Initial tour via Nearest Neighbor
    unvisited = set(range(n))
    tour: list[int] = []
    curr = hub_coord

    while unvisited:
        nearest_idx = min(
            unvisited,
            key=lambda idx: calculate_haversine_road_distance(curr[0], curr[1], coords[idx][0], coords[idx][1])
        )
        tour.append(nearest_idx)
        curr = coords[nearest_idx]
        unvisited.remove(nearest_idx)

    # 2-Opt edge swaps
    improved = True
    iterations = 0
    while improved and iterations < 50:
        improved = False
        iterations += 1
        for i in range(len(tour) - 1):
            for k in range(i + 1, len(tour)):
                # Evaluate current distance
                prev_i = hub_coord if i == 0 else coords[tour[i - 1]]
                next_k = hub_coord if k == len(tour) - 1 else coords[tour[k + 1]]

                d_current = (
                    calculate_haversine_road_distance(prev_i[0], prev_i[1], coords[tour[i]][0], coords[tour[i]][1]) +
                    calculate_haversine_road_distance(coords[tour[k]][0], coords[tour[k]][1], next_k[0], next_k[1])
                )
                d_reversed = (
                    calculate_haversine_road_distance(prev_i[0], prev_i[1], coords[tour[k]][0], coords[tour[k]][1]) +
                    calculate_haversine_road_distance(coords[tour[i]][0], coords[tour[i]][1], next_k[0], next_k[1])
                )

                if d_reversed < d_current - 0.05:
                    tour[i:k + 1] = reversed(tour[i:k + 1])
                    improved = True

    return tour


class DistributionRouter:
    """
    Capacitated Vehicle Routing solver for distributing organic compost and liquid digestate.
    """

    DIESEL_PRICE_PER_LITER = 350.0  # LKR per liter of Auto Diesel
    DIESEL_EMISSION_FACTOR = 2.68   # kg CO2e per liter of diesel burned
    AVERAGE_SPEED_KMH = 38.0        # Average road transit velocity for commercial trucks

    def solve_dispatch_plan(
        self,
        hub_id: str,
        orders: list[dict[str, Any]],
        preferred_vehicle_type: str | None = None
    ) -> RegionalLogisticsPlan:
        """
        Groups drop-offs by vehicle capacity and calculates optimized travel trajectories.
        """
        hub_info = REGIONAL_HUBS.get(hub_id, REGIONAL_HUBS["HUB-DAMBULLA"])
        hub_lat = float(hub_info["latitude"])
        hub_lon = float(hub_info["longitude"])
        hub_coord = (hub_lat, hub_lon)

        # Filter active drop-offs (> 0 kg)
        valid_orders = [o for o in orders if float(o.get("dropoff_mass_kg", 0.0)) > 0.0]
        if not valid_orders:
            return RegionalLogisticsPlan(
                plan_id=f"PLAN-{hub_id}-EMPTY",
                origin_hub_id=hub_id,
                origin_hub_name=str(hub_info["hub_name"]),
                total_fertilizer_dispatched_kg=0.0,
                total_distance_covered_km=0.0,
                total_diesel_liters=0.0,
                total_logistics_cost_lkr=0.0,
                average_unit_cost_lkr_kg=0.0,
                total_ghg_emissions_kg_co2e=0.0,
                active_vehicles_count=0,
                manifests=[],
                logistics_notes=["No valid delivery demands provided."]
            )

        # Determine vehicle type
        total_demand_kg = sum(float(o["dropoff_mass_kg"]) for o in valid_orders)
        if preferred_vehicle_type and preferred_vehicle_type in VEHICLE_FLEET_CONFIGS:
            v_type = preferred_vehicle_type
        else:
            if total_demand_kg > 4000.0:
                v_type = "HEAVY_TRUCK"
            elif total_demand_kg > 1500.0:
                v_type = "MEDIUM_TRUCK"
            else:
                v_type = "LIGHT_TRUCK"

        v_config = VEHICLE_FLEET_CONFIGS[v_type]
        v_capacity = float(v_config["capacity_kg"])

        # Partition orders into vehicle payloads strictly bounded by vehicle capacity
        remaining_orders: list[dict[str, Any]] = [dict(o) for o in valid_orders]
        vehicle_batches: list[list[dict[str, Any]]] = []

        while remaining_orders:
            batch: list[dict[str, Any]] = []
            batch_load = 0.0

            idx = 0
            while idx < len(remaining_orders) and batch_load < v_capacity:
                order = remaining_orders[idx]
                mass = float(order["dropoff_mass_kg"])
                available_space = v_capacity - batch_load

                if mass <= available_space:
                    batch.append(order)
                    batch_load += mass
                    remaining_orders.pop(idx)
                else:
                    # Allocate portion of order to fill this truck, leave remainder for next trip
                    partial_order = dict(order)
                    partial_order["dropoff_mass_kg"] = available_space
                    batch.append(partial_order)
                    batch_load += available_space
                    order["dropoff_mass_kg"] = mass - available_space
                    break

            if batch:
                vehicle_batches.append(batch)
            else:
                break

        # Build manifests
        manifests: list[VehicleDispatchManifest] = []
        total_distance = 0.0
        total_fuel = 0.0
        total_cost = 0.0
        total_emissions = 0.0
        total_dispatched_mass = 0.0

        for b_idx, batch in enumerate(vehicle_batches):
            coords = [(float(o["latitude"]), float(o["longitude"])) for o in batch]
            optimized_indices = two_opt_optimize_route(coords, hub_coord)

            waypoints: list[DeliveryWaypoint] = []
            curr_coord = hub_coord
            cum_dist = 0.0
            cum_minutes = 0.0
            trip_payload = sum(float(batch[i]["dropoff_mass_kg"]) for i in optimized_indices)

            for stop_no, orig_idx in enumerate(optimized_indices, start=1):
                order_item = batch[orig_idx]
                dest_coord = coords[orig_idx]
                leg_dist = calculate_haversine_road_distance(
                    curr_coord[0], curr_coord[1], dest_coord[0], dest_coord[1]
                )
                leg_hours = leg_dist / self.AVERAGE_SPEED_KMH
                cum_dist += leg_dist
                cum_minutes += (leg_hours * 60.0) + 15.0  # 15 minutes unloading time per farm

                waypoints.append(DeliveryWaypoint(
                    stop_number=stop_no,
                    farmer_id=str(order_item.get("farmer_id", f"FARM-{stop_no:02d}")),
                    farmer_name=str(order_item.get("farmer_name", "Farmer")),
                    cluster_name=str(order_item.get("cluster_name", "Rural Cluster")),
                    latitude=dest_coord[0],
                    longitude=dest_coord[1],
                    dropoff_fertilizer_category=str(order_item.get("fertilizer_category", "SOLID_ORGANIC_COMPOST")),
                    dropoff_mass_kg=round(float(order_item["dropoff_mass_kg"]), 1),
                    distance_from_prev_stop_km=round(leg_dist, 2),
                    cumulative_distance_km=round(cum_dist, 2),
                    estimated_arrival_minutes=round(cum_minutes, 1),
                ))
                curr_coord = dest_coord

            # Return journey back to hub
            return_dist = calculate_haversine_road_distance(
                curr_coord[0], curr_coord[1], hub_lat, hub_lon
            )
            total_trip_dist = cum_dist + return_dist
            total_transit_h = total_trip_dist / self.AVERAGE_SPEED_KMH

            fuel_liters = total_trip_dist / float(v_config["fuel_economy_km_l"])
            fuel_cost = fuel_liters * self.DIESEL_PRICE_PER_LITER
            labor_cost = total_transit_h * float(v_config["driver_crew_cost_lkr_h"])
            fixed_cost = float(v_config["fixed_dispatch_cost_lkr"])
            manifest_total_cost = fuel_cost + labor_cost + fixed_cost
            unit_cost = manifest_total_cost / trip_payload if trip_payload > 0 else 0.0
            trip_emissions = fuel_liters * self.DIESEL_EMISSION_FACTOR

            manifests.append(VehicleDispatchManifest(
                manifest_id=f"MNF-{hub_id[-4:]}-V{b_idx + 1:02d}",
                vehicle_type=v_type,
                vehicle_name=str(v_config["name"]),
                capacity_kg=v_capacity,
                assigned_payload_kg=round(trip_payload, 1),
                capacity_utilization_pct=round((trip_payload / v_capacity) * 100.0, 1),
                origin_hub_name=str(hub_info["hub_name"]),
                origin_latitude=hub_lat,
                origin_longitude=hub_lon,
                total_transit_distance_km=round(total_trip_dist, 2),
                total_transit_hours=round(total_transit_h + (len(waypoints) * 0.25), 2),
                diesel_consumed_liters=round(fuel_liters, 2),
                fuel_cost_lkr=round(fuel_cost, 2),
                crew_labor_cost_lkr=round(labor_cost, 2),
                fixed_dispatch_cost_lkr=round(fixed_cost, 2),
                total_trip_cost_lkr=round(manifest_total_cost, 2),
                unit_delivery_cost_lkr_kg=round(unit_cost, 2),
                transport_ghg_emissions_kg_co2e=round(trip_emissions, 2),
                waypoints=waypoints,
            ))

            total_distance += total_trip_dist
            total_fuel += fuel_liters
            total_cost += manifest_total_cost
            total_emissions += trip_emissions
            total_dispatched_mass += trip_payload

        avg_unit_cost = total_cost / total_dispatched_mass if total_dispatched_mass > 0 else 0.0

        notes = [
            f"Optimized dispatch schedule servicing {len(valid_orders)} farm drop-offs across {len(manifests)} vehicle run(s).",
            f"Fleet: {v_config['name']} ({v_capacity:.0f} kg capacity).",
            f"Total logistics cost: LKR {total_cost:,.2f} (Average unit delivery cost: LKR {avg_unit_cost:.2f}/kg).",
            f"Carbon footprint: {total_emissions:.1f} kg CO2e ({total_fuel:.1f} L Auto Diesel)."
        ]

        return RegionalLogisticsPlan(
            plan_id=f"LOG-{hub_id[-4:]}-OPT",
            origin_hub_id=hub_id,
            origin_hub_name=str(hub_info["hub_name"]),
            total_fertilizer_dispatched_kg=round(total_dispatched_mass, 1),
            total_distance_covered_km=round(total_distance, 2),
            total_diesel_liters=round(total_fuel, 2),
            total_logistics_cost_lkr=round(total_cost, 2),
            average_unit_cost_lkr_kg=round(avg_unit_cost, 2),
            total_ghg_emissions_kg_co2e=round(total_emissions, 2),
            active_vehicles_count=len(manifests),
            manifests=manifests,
            logistics_notes=notes,
        )
