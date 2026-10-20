"""FastAPI route handlers for Farmer Transport Tracking, Crate Barcode Verification & ML Risk Scoring.
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.core.risk_service import RiskScoringService
from app.core.transport_db import get_db_connection
from app.schemas.risk import RiskPredictionRequest
from app.schemas.transport import (
    AvailableBarcodesResponse,
    BarcodeValidationRequest,
    BarcodeValidationResponse,
    BatchPredictRequest,
    BatchPredictResponse,
    ConfirmTransportRequest,
    ConfirmTransportResponse,
    DispatchTransportRequest,
    FarmerTransportHistoryResponse,
    ReceiveTransportRequest,
    TimelineEvent,
    TransportLotItem,
    TransportTrackingDetailResponse,
)

router = APIRouter(prefix="/api/transport", tags=["Farmer Transport Tracking & Risk Prediction"])


def generate_safety_advice(item: TransportLotItem, waste_pct: float, risk_tier: str) -> List[str]:
    """Generates tailored rule-based agronomic & post-harvest logistics recommendations."""
    advice: List[str] = []

    # 1. Packaging advice
    packing = item.packing_type.upper()
    if "POLYSACK" in packing or "GUNNY" in packing:
        advice.append(
            "CRITICAL: Polysack mesh bags cause high mechanical vibration stress and bottom-layer crushing loss. "
            "Switch to rigid ventilated plastic crates (DoA approved) to reduce spoilage loss by up to 14%."
        )
    elif "LOOSE" in packing:
        advice.append(
            "HIGH LOSS HAZARD: Loose bulk loading causes severe compression and bruise injury. "
            "Stack in modular crates to protect fruit firmness."
        )
    elif "CARDBOARD" in packing and item.is_rainy:
        advice.append(
            "MOISTURE RISK: Cardboard boxes soften and collapse in humid/rainy conditions. "
            "Ensure waterproof tarp covering and adequate bottom pallet elevation."
        )

    # 2. Thermal & Vehicle insulation advice
    veh = item.transport_type.upper()
    if "OPEN" in veh and not item.is_covered:
        advice.append(
            "SOLAR EXPOSURE WARNING: Open truck direct sun exposure accelerates internal pulp respiration (Q10 index > 2.5). "
            "Install a reflective tarpaulin canopy with side ventilation."
        )
    if not item.has_cooling and (item.ambient_temp_c or 31.0) > 30.0:
        advice.append(
            f"HIGH TEMPERATURE ALERT ({item.ambient_temp_c or 31.0}°C): Pre-cool produce before loading or schedule transport "
            "during cooler night/early morning hours (depart before 06:00 AM) to curb microbial proliferation."
        )

    # 3. Maturity & Harvest interval
    if item.maturity == "Over-ripe":
        advice.append(
            "SENESCENCE WARNING: Over-ripe produce has low shear tolerance and high ethylene emission. "
            "Prioritize shortest route corridor or consider immediate diversion to local economic processing."
        )

    # 4. Long transit corridor
    if item.transit_hours > 3.0:
        advice.append(
            f"LONG CORRIDOR ({item.distance_km} km / {item.transit_hours} hrs): Ensure constant vehicle speed and avoid prolonged "
            "unventilated stops at midday collection checkpoints."
        )

    # 5. General tier advice
    if risk_tier == "HIGH":
        advice.append(
            "HIGH LOSS PROJECTION: Projected cull loss exceeds safe threshold. Stream 2 bioeconomy allocation will capture "
            "estimated cull mass for secondary aerobic composting / organic fertilizer."
        )
    elif risk_tier == "MEDIUM":
        advice.append(
            "MODERATE RISK: Grade produce carefully at collection center receiving dock to separate first-grade commercial retail."
        )
    else:
        advice.append(
            "OPTIMAL CARGO CONDITIONS: Spoilage risk is safely within bounds (<15%). Maintain current ventilation practices."
        )

    return advice


@router.get("/barcode/available", response_model=AvailableBarcodesResponse)
def get_available_barcodes() -> AvailableBarcodesResponse:
    """Returns all pre-issued crate barcode stickers currently available for transport registration."""
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT barcode_no FROM barcode_stickers WHERE status = 'available' ORDER BY barcode_no ASC"
            ).fetchall()
            codes = [r["barcode_no"] for r in rows]
            return AvailableBarcodesResponse(total=len(codes), barcodes=codes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error reading available barcodes: {exc!s}"
        ) from exc


@router.post("/barcode/validate", response_model=BarcodeValidationResponse)
def validate_barcode(payload: BarcodeValidationRequest) -> BarcodeValidationResponse:
    """Validates whether a scanned barcode sticker exists and is ready for produce assignment."""
    code = payload.barcode_no.strip().upper()
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT barcode_no, status, assigned_farmer_id, issued_at FROM barcode_stickers WHERE barcode_no = ?",
                (code,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Barcode sticker '{code}' not recognized in pre-issued series."
                )

            st = row["status"]
            if st != "available":
                return BarcodeValidationResponse(
                    valid=False,
                    barcode_no=code,
                    status=st,
                    assigned_farmer_id=row["assigned_farmer_id"],
                    issued_at=row["issued_at"],
                    message=f"Barcode sticker '{code}' is already {st}."
                )

            return BarcodeValidationResponse(
                valid=True,
                barcode_no=code,
                status="available",
                assigned_farmer_id=None,
                issued_at=row["issued_at"],
                message=f"Barcode sticker '{code}' is valid and available for produce registration."
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error verifying barcode: {exc!s}"
        ) from exc


@router.post("/predict", response_model=BatchPredictResponse)
def predict_transport_risk(payload: BatchPredictRequest) -> BatchPredictResponse:
    """Executes trained XGBoost Regressor & Classifier on produce lot items."""
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one produce lot item required.")

    service = RiskScoringService.get_instance()
    processed_items: List[TransportLotItem] = []
    total_gross_kg = 0.0
    total_waste_kg = 0.0

    for item in payload.items:
        # Map vehicle type and road condition
        veh_clean = item.transport_type.upper()
        if "REFRIGERATED" in veh_clean:
            mapped_veh = "REFRIGERATED_VAN"
        elif "THREE" in veh_clean:
            mapped_veh = "THREE_WHEELER"
        elif "COVERED" in veh_clean:
            mapped_veh = "COVERED_TRUCK"
        else:
            mapped_veh = "OPEN_TRUCK"

        # Packaging mapping
        pack_clean = item.packing_type.upper()
        if "PLASTIC" in pack_clean:
            mapped_pack = "PLASTIC_CRATE"
        elif "VENTILATED" in pack_clean:
            mapped_pack = "VENTILATED_BOX"
        elif "CARDBOARD" in pack_clean:
            mapped_pack = "CARDBOARD_BOX"
        else:
            mapped_pack = "POLYSACK_MESH"

        # Build ML prediction request
        ml_req = RiskPredictionRequest(
            crop_name=item.food_name,
            payload_kg=item.kg,
            distance_km=item.distance_km,
            transit_hours=item.transit_hours,
            ambient_temperature_c=item.ambient_temp_c or 31.0,
            ambient_humidity_pct=item.ambient_humidity_pct or 75.0,
            vehicle_type=mapped_veh,
            road_condition="MODERATE" if not item.is_rainy else "POOR",
            packaging_type=mapped_pack,
            route=f"{item.origin_district.upper()} - {item.destination_center.split()[0].upper()}",
            season="YALA",
        )

        try:
            pred = service.predict_risk(ml_req)
            waste_pct = pred.predicted_spoilage_loss_pct
            risk_tier = pred.risk_tier
            fresh_kg = pred.stream_1_fresh_produce_kg
            waste_kg = pred.stream_2_bioeconomy_feedstock_kg
            destination = pred.stream_2_destination
        except Exception:
            # Fallback heuristic calculation if crop name is outside focal baseline
            waste_pct = round(min(45.0, max(2.5, 3.5 + (item.distance_km * 0.08) + (item.transit_hours * 1.5))), 2)
            if "POLYSACK" in mapped_pack:
                waste_pct = min(60.0, waste_pct + 8.5)
            if mapped_veh == "REFRIGERATED_VAN":
                waste_pct = max(1.2, waste_pct * 0.35)
            fresh_kg = round(item.kg * (1.0 - waste_pct / 100.0), 2)
            waste_kg = round(item.kg * (waste_pct / 100.0), 2)
            risk_tier = "LOW" if waste_pct < 15.0 else "MEDIUM" if waste_pct <= 20.0 else "HIGH"
            destination = "AEROBIC_COMPOSTING" if waste_pct < 25.0 else "ANAEROBIC_BIOGAS_DIVERSION"

        advice = generate_safety_advice(item, waste_pct, risk_tier)

        updated_item = item.model_copy(
            update={
                "predicted_waste_pct": waste_pct,
                "predicted_waste_kg": waste_kg,
                "risk_level": risk_tier,
                "stream_1_fresh_kg": fresh_kg,
                "stream_2_waste_kg": waste_kg,
                "bioeconomy_destination": destination,
                "advice": advice,
            }
        )

        total_gross_kg += item.kg
        total_waste_kg += waste_kg
        processed_items.append(updated_item)

    overall_pct = round((total_waste_kg / total_gross_kg) * 100.0, 2) if total_gross_kg > 0 else 0.0
    overall_tier = "LOW" if overall_pct < 15.0 else "MEDIUM" if overall_pct <= 20.0 else "HIGH"

    return BatchPredictResponse(
        total_lots=len(processed_items),
        total_kg=round(total_gross_kg, 2),
        total_predicted_waste_kg=round(total_waste_kg, 2),
        overall_waste_pct=overall_pct,
        overall_risk_level=overall_tier,
        items=processed_items,
    )


@router.post("/confirm", response_model=ConfirmTransportResponse)
def confirm_transport(payload: ConfirmTransportRequest) -> ConfirmTransportResponse:
    """Confirms produce transport batch, creates DB record with status 'Ready', and locks barcodes."""
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot confirm transport with no produce lots.")

    transport_id = f"TRP-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    total_kg = sum(it.kg for it in payload.items)
    total_waste_kg = sum(it.predicted_waste_kg or 0.0 for it in payload.items)
    overall_waste_pct = round((total_waste_kg / total_kg) * 100.0, 2) if total_kg > 0 else 0.0
    overall_risk = "LOW" if overall_waste_pct < 15.0 else "MEDIUM" if overall_waste_pct <= 20.0 else "HIGH"

    try:
        with get_db_connection() as conn:
            # 1. Insert into transports
            conn.execute(
                """
                INSERT INTO transports (id, farmer_id, status, destination_center, total_kg, created_at, updated_at)
                VALUES (?, ?, 'Ready', ?, ?, ?, ?)
                """,
                (transport_id, payload.farmer_id, payload.destination_center, total_kg, now_iso, now_iso)
            )

            # 2. Insert items and update barcode status
            for item in payload.items:
                item_id = item.id or f"ITEM-{uuid.uuid4().hex[:8].upper()}"
                advice_str = json.dumps(item.advice or [])

                conn.execute(
                    """
                    INSERT INTO transport_items (
                        id, transport_id, barcode_no, crop_category, food_name, kg,
                        destination_center, origin_district, distance_km, transit_hours,
                        harvest_datetime, transport_date, transport_time, transport_type,
                        vehicle_no, packing_type, maturity, is_covered, has_cooling,
                        is_washed, is_graded, ambient_temp_c, ambient_humidity_pct,
                        is_rainy, predicted_waste_pct, predicted_waste_kg, risk_level,
                        advice_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id, transport_id, item.barcode_no, item.crop_category, item.food_name, item.kg,
                        item.destination_center, item.origin_district, item.distance_km, item.transit_hours,
                        item.harvest_datetime, item.transport_date, item.transport_time, item.transport_type,
                        item.vehicle_no, item.packing_type, item.maturity, 1 if item.is_covered else 0,
                        1 if item.has_cooling else 0, 1 if item.is_washed else 0, 1 if item.is_graded else 0,
                        item.ambient_temp_c, item.ambient_humidity_pct, 1 if item.is_rainy else 0,
                        item.predicted_waste_pct, item.predicted_waste_kg, item.risk_level, advice_str, now_iso
                    )
                )

                # Update barcode sticker status to assigned
                conn.execute(
                    """
                    UPDATE barcode_stickers
                    SET status = 'assigned', assigned_farmer_id = ?, assigned_transport_id = ?, updated_at = ?
                    WHERE barcode_no = ?
                    """,
                    (payload.farmer_id, transport_id, now_iso, item.barcode_no)
                )

            conn.commit()

        return ConfirmTransportResponse(
            transport_id=transport_id,
            farmer_id=payload.farmer_id,
            status="Ready",
            destination_center=payload.destination_center,
            total_kg=round(total_kg, 2),
            total_lots=len(payload.items),
            total_predicted_waste_kg=round(total_waste_kg, 2),
            overall_risk_level=overall_risk,
            confirmed_at=now_iso,
            message="Transport batch successfully confirmed with status 'Ready for Transport'. Crate barcodes officially locked."
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error confirming transport: {exc!s}"
        ) from exc


def _row_to_transport_item(row: dict) -> TransportLotItem:
    """Helper to convert a transport_items DB row to a TransportLotItem schema."""
    advice_list: List[str] = []
    if row.get("advice_json"):
        try:
            advice_list = json.loads(row["advice_json"])
        except Exception:
            advice_list = []

    return TransportLotItem(
        id=row.get("id"),
        barcode_no=row["barcode_no"],
        crop_category=row["crop_category"],
        food_name=row["food_name"],
        kg=float(row["kg"]),
        destination_center=row["destination_center"],
        origin_district=row["origin_district"],
        distance_km=float(row["distance_km"]),
        transit_hours=float(row["transit_hours"]),
        harvest_datetime=row["harvest_datetime"],
        transport_date=row["transport_date"],
        transport_time=row["transport_time"],
        transport_type=row["transport_type"],
        vehicle_no=row["vehicle_no"],
        packing_type=row["packing_type"],
        maturity=row["maturity"],
        is_covered=bool(row["is_covered"]),
        has_cooling=bool(row["has_cooling"]),
        is_washed=bool(row["is_washed"]),
        is_graded=bool(row["is_graded"]),
        ambient_temp_c=float(row["ambient_temp_c"]) if row.get("ambient_temp_c") is not None else None,
        ambient_humidity_pct=float(row["ambient_humidity_pct"]) if row.get("ambient_humidity_pct") is not None else None,
        is_rainy=bool(row["is_rainy"]),
        predicted_waste_pct=float(row["predicted_waste_pct"]) if row.get("predicted_waste_pct") is not None else None,
        predicted_waste_kg=float(row["predicted_waste_kg"]) if row.get("predicted_waste_kg") is not None else None,
        risk_level=row.get("risk_level"),
        actual_received_kg=float(row["actual_received_kg"]) if row.get("actual_received_kg") is not None else None,
        accepted_fresh_kg=float(row["accepted_fresh_kg"]) if row.get("accepted_fresh_kg") is not None else None,
        cull_waste_kg=float(row["cull_waste_kg"]) if row.get("cull_waste_kg") is not None else None,
        item_status=row.get("item_status") or "Ready",
        advice=advice_list,
        created_at=row.get("created_at"),
    )


def _build_transport_timeline(t_dict: dict, items: List[TransportLotItem]) -> List[TimelineEvent]:
    status = t_dict.get("status", "Ready")
    created_at = t_dict.get("created_at")
    dispatched_at = t_dict.get("dispatched_at")
    received_at = t_dict.get("received_at")
    dest = t_dict.get("destination_center", "Collection Centre")
    inspector = t_dict.get("inspector_name") or "Quality Officer"
    grade = t_dict.get("quality_grade") or "Grade A"
    fresh_kg = t_dict.get("accepted_fresh_kg")
    cull_kg = t_dict.get("cull_waste_kg")
    bio_action = t_dict.get("bioeconomy_action") or "Bioeconomy Organic Recovery"

    # Step 1: Registration
    t1 = TimelineEvent(
        step=1,
        title="Produce Lot Registered & Crate Barcodes Locked",
        status="completed",
        timestamp=created_at,
        description=f"{len(items)} produce lot(s) weighed and assigned official traceability barcodes.",
    )

    # Step 2: Dispatched
    if status == "Ready":
        t2 = TimelineEvent(
            step=2,
            title="Awaiting Farm Gate Departure",
            status="current",
            timestamp=None,
            description="Produce loaded into vehicle. Ready for transit dispatch.",
        )
    else:
        t2 = TimelineEvent(
            step=2,
            title="Dispatched & In Transit",
            status="completed",
            timestamp=dispatched_at or created_at,
            description=f"Cargo dispatched via road corridor to {dest}.",
        )

    # Step 3: Arrived at Collection Center
    if status in ["Ready"]:
        t3 = TimelineEvent(
            step=3,
            title=f"Arrival at {dest.split()[0]} DEC",
            status="pending",
            timestamp=None,
            description="Vehicle will check in at the reception bay.",
        )
    elif status == "In Transit":
        t3 = TimelineEvent(
            step=3,
            title=f"In Transit to {dest.split()[0]} DEC",
            status="current",
            timestamp=None,
            description=f"Estimated transit: {items[0].transit_hours if items else 1.0} hrs on road corridor.",
        )
    else:  # Delivered / Processed
        t3 = TimelineEvent(
            step=3,
            title=f"Arrived at {dest.split()[0]} DEC Reception",
            status="completed",
            timestamp=received_at or dispatched_at,
            description="Vehicle checked in at wholesale receiving dock.",
        )

    # Step 4: Inspected & Weighed
    if status in ["Ready", "In Transit"]:
        t4 = TimelineEvent(
            step=4,
            title="Dock Weighing & SLSI Quality Inspection",
            status="pending",
            timestamp=None,
            description="Gross scale verification and post-harvest damage grading.",
        )
    else:
        actual_kg = t_dict.get("actual_received_kg") or t_dict.get("total_kg")
        t4 = TimelineEvent(
            step=4,
            title="Weighed & Inspected at Receiving Dock",
            status="completed",
            timestamp=received_at,
            description=f"Certified by {inspector}. Net scale: {actual_kg} kg ({grade}).",
        )

    # Step 5: Dual-Stream Mass Partitioning
    if status in ["Ready", "In Transit"]:
        t5 = TimelineEvent(
            step=5,
            title="Dual-Stream Partitioning: Fresh Retail & Bioeconomy Cull",
            status="pending",
            timestamp=None,
            description="Separating retail commercial produce from bioeconomy cull feedstock.",
        )
    else:
        t5 = TimelineEvent(
            step=5,
            title="Dual-Stream Recovery Completed",
            status="completed",
            timestamp=received_at,
            description=f"Fresh Retail: {fresh_kg or (t_dict['total_kg'] * 0.8):.1f} kg | Cull Stream: {cull_kg or (t_dict['total_kg'] * 0.2):.1f} kg -> {bio_action}.",
        )

    return [t1, t2, t3, t4, t5]


@router.get("/farmer/{farmer_id}/history", response_model=FarmerTransportHistoryResponse)
def get_farmer_transport_history(farmer_id: str) -> FarmerTransportHistoryResponse:
    """Returns the authenticated farmer's active shipments (Current Process) and past delivered history."""
    try:
        with get_db_connection() as conn:
            # Query all transports for farmer
            trans_rows = conn.execute(
                """
                SELECT * FROM transports
                WHERE farmer_id = ?
                ORDER BY created_at DESC
                """,
                (farmer_id,)
            ).fetchall()

            active_list: List[TransportTrackingDetailResponse] = []
            completed_list: List[TransportTrackingDetailResponse] = []

            total_produce_kg = 0.0
            total_fresh_kg = 0.0
            total_cull_kg = 0.0

            for t_row in trans_rows:
                t_dict = dict(t_row)
                t_id = t_dict["id"]

                # Fetch items for this transport
                item_rows = conn.execute(
                    "SELECT * FROM transport_items WHERE transport_id = ? ORDER BY created_at ASC",
                    (t_id,)
                ).fetchall()
                items = [_row_to_transport_item(dict(ir)) for ir in item_rows]

                timeline = _build_transport_timeline(t_dict, items)

                detail = TransportTrackingDetailResponse(
                    id=t_dict["id"],
                    farmer_id=t_dict["farmer_id"],
                    status=t_dict["status"],
                    destination_center=t_dict["destination_center"],
                    total_kg=float(t_dict["total_kg"]),
                    created_at=t_dict["created_at"],
                    updated_at=t_dict["updated_at"],
                    dispatched_at=t_dict.get("dispatched_at"),
                    received_at=t_dict.get("received_at"),
                    actual_received_kg=float(t_dict["actual_received_kg"]) if t_dict.get("actual_received_kg") is not None else None,
                    accepted_fresh_kg=float(t_dict["accepted_fresh_kg"]) if t_dict.get("accepted_fresh_kg") is not None else None,
                    cull_waste_kg=float(t_dict["cull_waste_kg"]) if t_dict.get("cull_waste_kg") is not None else None,
                    inspector_name=t_dict.get("inspector_name"),
                    receiving_notes=t_dict.get("receiving_notes"),
                    quality_grade=t_dict.get("quality_grade"),
                    bioeconomy_action=t_dict.get("bioeconomy_action"),
                    items=items,
                    timeline=timeline,
                )

                total_produce_kg += float(t_dict["total_kg"])
                if detail.status in ["Delivered", "Cancelled"]:
                    completed_list.append(detail)
                    if detail.accepted_fresh_kg is not None:
                        total_fresh_kg += detail.accepted_fresh_kg
                    if detail.cull_waste_kg is not None:
                        total_cull_kg += detail.cull_waste_kg
                else:
                    active_list.append(detail)

            return FarmerTransportHistoryResponse(
                farmer_id=farmer_id,
                total_shipments=len(trans_rows),
                active_shipments_count=len(active_list),
                delivered_shipments_count=len(completed_list),
                total_produce_kg=round(total_produce_kg, 2),
                total_fresh_delivered_kg=round(total_fresh_kg, 2),
                total_cull_recovered_kg=round(total_cull_kg, 2),
                active_transports=active_list,
                completed_transports=completed_list,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching farmer transport history: {exc!s}"
        ) from exc


@router.get("/{transport_id}", response_model=TransportTrackingDetailResponse)
def get_transport_tracking_detail(transport_id: str) -> TransportTrackingDetailResponse:
    """Returns complete real-time tracking details and 5-step milestone timeline for a transport batch."""
    try:
        with get_db_connection() as conn:
            t_row = conn.execute("SELECT * FROM transports WHERE id = ?", (transport_id,)).fetchone()
            if not t_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transport '{transport_id}' not found.")

            t_dict = dict(t_row)
            item_rows = conn.execute(
                "SELECT * FROM transport_items WHERE transport_id = ? ORDER BY created_at ASC",
                (transport_id,)
            ).fetchall()
            items = [_row_to_transport_item(dict(ir)) for ir in item_rows]
            timeline = _build_transport_timeline(t_dict, items)

            return TransportTrackingDetailResponse(
                id=t_dict["id"],
                farmer_id=t_dict["farmer_id"],
                status=t_dict["status"],
                destination_center=t_dict["destination_center"],
                total_kg=float(t_dict["total_kg"]),
                created_at=t_dict["created_at"],
                updated_at=t_dict["updated_at"],
                dispatched_at=t_dict.get("dispatched_at"),
                received_at=t_dict.get("received_at"),
                actual_received_kg=float(t_dict["actual_received_kg"]) if t_dict.get("actual_received_kg") is not None else None,
                accepted_fresh_kg=float(t_dict["accepted_fresh_kg"]) if t_dict.get("accepted_fresh_kg") is not None else None,
                cull_waste_kg=float(t_dict["cull_waste_kg"]) if t_dict.get("cull_waste_kg") is not None else None,
                inspector_name=t_dict.get("inspector_name"),
                receiving_notes=t_dict.get("receiving_notes"),
                quality_grade=t_dict.get("quality_grade"),
                bioeconomy_action=t_dict.get("bioeconomy_action"),
                items=items,
                timeline=timeline,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching transport detail: {exc!s}"
        ) from exc


@router.post("/{transport_id}/dispatch")
def dispatch_transport(transport_id: str, payload: DispatchTransportRequest = None) -> dict:
    """Farmer dispatches produce from farm gate: updates status to 'In Transit' and locks crate barcodes in transit."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT id, status FROM transports WHERE id = ?", (transport_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transport '{transport_id}' not found.")

            conn.execute(
                """
                UPDATE transports
                SET status = 'In Transit', dispatched_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now_iso, now_iso, transport_id)
            )

            conn.execute(
                """
                UPDATE barcode_stickers
                SET status = 'in_transit', updated_at = ?
                WHERE assigned_transport_id = ?
                """,
                (now_iso, transport_id)
            )

            conn.execute(
                """
                UPDATE transport_items
                SET item_status = 'In Transit'
                WHERE transport_id = ?
                """,
                (transport_id,)
            )

            conn.commit()

        return {
            "status": "success",
            "transport_id": transport_id,
            "new_status": "In Transit",
            "dispatched_at": now_iso,
            "message": "Produce successfully marked as Dispatched & In Transit to destination collection centre."
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error dispatching transport: {exc!s}"
        ) from exc


@router.post("/{transport_id}/receive")
def receive_transport_at_collection_center(transport_id: str, payload: ReceiveTransportRequest) -> dict:
    """Collection Centre Quality Control receives, weighs, and inspects the transport batch.
    Updates status to 'Delivered' and partitions fresh produce vs bioeconomy cull feedstock.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            t_row = conn.execute("SELECT * FROM transports WHERE id = ?", (transport_id,)).fetchone()
            if not t_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transport '{transport_id}' not found.")

            t_dict = dict(t_row)
            gross_kg = float(t_dict["total_kg"])
            actual_kg = float(payload.actual_received_kg) if payload.actual_received_kg is not None else gross_kg

            # If fresh kg not explicitly set, calculate based on average predicted waste
            item_rows = conn.execute(
                "SELECT predicted_waste_pct FROM transport_items WHERE transport_id = ?",
                (transport_id,)
            ).fetchall()
            avg_waste_pct = 20.0
            if item_rows:
                pcts = [r["predicted_waste_pct"] for r in item_rows if r["predicted_waste_pct"] is not None]
                if pcts:
                    avg_waste_pct = sum(pcts) / len(pcts)

            if payload.accepted_fresh_kg is not None:
                fresh_kg = float(payload.accepted_fresh_kg)
            else:
                fresh_kg = round(actual_kg * (1.0 - avg_waste_pct / 100.0), 2)

            if payload.cull_waste_kg is not None:
                cull_kg = float(payload.cull_waste_kg)
            else:
                cull_kg = round(actual_kg - fresh_kg, 2)

            bio_action = payload.bioeconomy_action or (
                "Anaerobic Biogas Diversion" if avg_waste_pct > 25.0 else "SLSI 1246:2003 Aerobic Composting"
            )

            conn.execute(
                """
                UPDATE transports
                SET status = 'Delivered', received_at = ?, actual_received_kg = ?,
                    accepted_fresh_kg = ?, cull_waste_kg = ?, inspector_name = ?,
                    receiving_notes = ?, quality_grade = ?, bioeconomy_action = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    now_iso, actual_kg, fresh_kg, cull_kg, payload.inspector_name,
                    payload.receiving_notes, payload.quality_grade, bio_action, now_iso, transport_id
                )
            )

            conn.execute(
                """
                UPDATE barcode_stickers
                SET status = 'delivered', updated_at = ?
                WHERE assigned_transport_id = ?
                """,
                (now_iso, transport_id)
            )

            conn.execute(
                """
                UPDATE transport_items
                SET item_status = 'Delivered', actual_received_kg = ?, accepted_fresh_kg = ?, cull_waste_kg = ?
                WHERE transport_id = ?
                """,
                (actual_kg, fresh_kg, cull_kg, transport_id)
            )

            conn.commit()

        return {
            "status": "success",
            "transport_id": transport_id,
            "new_status": "Delivered",
            "received_at": now_iso,
            "actual_received_kg": actual_kg,
            "accepted_fresh_kg": fresh_kg,
            "cull_waste_kg": cull_kg,
            "quality_grade": payload.quality_grade,
            "inspector_name": payload.inspector_name,
            "bioeconomy_action": bio_action,
            "message": f"Transport batch verified at collection centre. Fresh retail: {fresh_kg} kg | Cull diverted to {bio_action}: {cull_kg} kg."
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error receiving transport: {exc!s}"
        ) from exc


@router.get("/routing/distance")
def get_routing_distance(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float
):
    """Calculates road transit distance (km) and driving duration (hours) via OSRM map routing with Haversine fallback."""
    import math
    import urllib.request

    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
        req = urllib.request.Request(url, headers={"User-Agent": "AgroDecision/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            if data.get("routes") and len(data["routes"]) > 0:
                dist_m = data["routes"][0]["distance"]
                dur_s = data["routes"][0]["duration"]
                dist_km = round(dist_m / 1000.0, 1)
                dur_hrs = round(dur_s / 3600.0, 1)
                mins = int(round(dur_s / 60.0))
                return {
                    "status": "success",
                    "distance_km": dist_km,
                    "transit_hours": dur_hrs,
                    "duration_text": f"{mins} mins" if mins < 60 else f"{mins // 60}h {mins % 60}m",
                    "source": "osrm_live_map"
                }
    except Exception:
        pass

    # Mathematical curvature fallback for Sri Lankan road topography
    R = 6371.0
    dlat = math.radians(dest_lat - origin_lat)
    dlon = math.radians(dest_lon - origin_lon)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    direct_km = R * c
    road_km = round(max(5.0, direct_km * 1.35), 1)
    hours = round(max(0.3, road_km / 42.0), 1)
    mins = int(round(hours * 60))
    return {
        "status": "success",
        "distance_km": road_km,
        "transit_hours": hours,
        "duration_text": f"{mins} mins" if mins < 60 else f"{mins // 60}h {mins % 60}m",
        "source": "topographical_fallback"
    }


@router.get("/telemetry/weather")
def get_ambient_weather(lat: float, lon: float):
    """Fetches real-time ambient temperature (°C), relative humidity (%), and rainfall status via Open-Meteo API."""
    import urllib.request

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain,weather_code"
        req = urllib.request.Request(url, headers={"User-Agent": "AgroDecision/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            current = data.get("current", {})
            temp = current.get("temperature_2m", 30.5)
            hum = current.get("relative_humidity_2m", 76.0)
            rain = current.get("rain", 0.0)
            code = current.get("weather_code", 0)
            is_rain = rain > 0.1 or code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]
            return {
                "status": "success",
                "temperature_c": round(float(temp), 1),
                "relative_humidity_pct": round(float(hum), 1),
                "is_rainy": is_rain,
                "rain_mm": round(float(rain), 2),
                "weather_code": code,
                "source": "open_meteo_live"
            }
    except Exception:
        pass

    return {
        "status": "success",
        "temperature_c": 31.0,
        "relative_humidity_pct": 75.0,
        "is_rainy": False,
        "rain_mm": 0.0,
        "weather_code": 0,
        "source": "agro_climatic_default"
    }

