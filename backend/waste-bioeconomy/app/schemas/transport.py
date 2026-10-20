"""Pydantic schemas for Farmer Transport Tracking & Spoilage Risk Prediction.
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks.
"""
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class BarcodeValidationRequest(BaseModel):
    barcode_no: str = Field(..., examples=["BC-000001"], description="Pre-issued barcode sticker number")


class BarcodeValidationResponse(BaseModel):
    valid: bool
    barcode_no: str
    status: str
    assigned_farmer_id: Optional[str] = None
    issued_at: Optional[str] = None
    message: Optional[str] = None


class AvailableBarcodesResponse(BaseModel):
    total: int
    barcodes: List[str]


class TransportLotItem(BaseModel):
    id: Optional[str] = None
    barcode_no: str = Field(..., description="Sticker ID e.g. BC-000001")
    crop_category: str = Field(..., description="Vegetable or Fruit")
    food_name: str = Field(..., description="Specific produce name e.g. Tomato")
    kg: float = Field(..., gt=0, description="Gross quantity in kilograms")
    destination_center: str = Field(..., description="Destination Economic Centre")
    origin_district: str = Field(..., description="Origin farming district")
    distance_km: float = Field(..., gt=0, description="Transit corridor distance in km")
    transit_hours: float = Field(..., gt=0, description="Transit duration in hours")
    harvest_datetime: str = Field(..., description="ISO datetime of crop harvest")
    transport_date: str = Field(..., description="Departure date YYYY-MM-DD")
    transport_time: str = Field(..., description="Departure time HH:MM")
    transport_type: str = Field(..., description="OPEN_TRUCK, COVERED_TRUCK, REFRIGERATED_VAN, etc.")
    vehicle_no: str = Field(..., description="Vehicle registration plate")
    packing_type: str = Field(..., description="PLASTIC_CRATE, VENTILATED_BOX, CARDBOARD_BOX, POLYSACK_MESH, etc.")
    maturity: str = Field(..., description="Under-ripe, Ripe, Over-ripe")
    is_covered: bool = False
    has_cooling: bool = False
    is_washed: bool = False
    is_graded: bool = True
    ambient_temp_c: Optional[float] = 31.0
    ambient_humidity_pct: Optional[float] = 75.0
    is_rainy: Optional[bool] = False
    predicted_waste_pct: Optional[float] = None
    predicted_waste_kg: Optional[float] = None
    risk_level: Optional[str] = None
    stream_1_fresh_kg: Optional[float] = None
    stream_2_waste_kg: Optional[float] = None
    bioeconomy_destination: Optional[str] = None
    actual_received_kg: Optional[float] = None
    accepted_fresh_kg: Optional[float] = None
    cull_waste_kg: Optional[float] = None
    item_status: Optional[str] = "Ready"
    advice: Optional[List[str]] = None
    created_at: Optional[str] = None


class BatchPredictRequest(BaseModel):
    items: List[TransportLotItem]


class BatchPredictResponse(BaseModel):
    total_lots: int
    total_kg: float
    total_predicted_waste_kg: float
    overall_waste_pct: float
    overall_risk_level: str
    items: List[TransportLotItem]


class ConfirmTransportRequest(BaseModel):
    farmer_id: str = Field(..., description="Authenticated farmer identifier")
    destination_center: str = Field(..., description="Primary Economic Centre destination")
    items: List[TransportLotItem]


class ConfirmTransportResponse(BaseModel):
    transport_id: str
    farmer_id: str
    status: str
    destination_center: str
    total_kg: float
    total_lots: int
    total_predicted_waste_kg: float
    overall_risk_level: str
    confirmed_at: str
    message: str


class DispatchTransportRequest(BaseModel):
    driver_name: Optional[str] = None
    vehicle_no: Optional[str] = None
    notes: Optional[str] = None


class ReceiveTransportRequest(BaseModel):
    inspector_name: str = Field(..., description="Receiving Quality Inspector Name")
    receiving_notes: Optional[str] = "Inspected and accepted at receiving dock."
    quality_grade: Optional[str] = "Grade A - Good Condition"
    actual_received_kg: Optional[float] = None
    accepted_fresh_kg: Optional[float] = None
    cull_waste_kg: Optional[float] = None
    bioeconomy_action: Optional[str] = "Diverted to Dambulla Bio-Hub for SLSI 1246:2003 Aerobic Composting"


class TimelineEvent(BaseModel):
    step: int
    title: str
    status: str  # 'completed', 'current', 'pending'
    timestamp: Optional[str] = None
    description: str


class TransportTrackingDetailResponse(BaseModel):
    id: str
    farmer_id: str
    status: str
    destination_center: str
    total_kg: float
    created_at: str
    updated_at: str
    dispatched_at: Optional[str] = None
    received_at: Optional[str] = None
    actual_received_kg: Optional[float] = None
    accepted_fresh_kg: Optional[float] = None
    cull_waste_kg: Optional[float] = None
    inspector_name: Optional[str] = None
    receiving_notes: Optional[str] = None
    quality_grade: Optional[str] = None
    bioeconomy_action: Optional[str] = None
    items: List[TransportLotItem] = []
    timeline: List[TimelineEvent] = []


class FarmerTransportHistoryResponse(BaseModel):
    farmer_id: str
    total_shipments: int
    active_shipments_count: int
    delivered_shipments_count: int
    total_produce_kg: float
    total_fresh_delivered_kg: float
    total_cull_recovered_kg: float
    active_transports: List[TransportTrackingDetailResponse]
    completed_transports: List[TransportTrackingDetailResponse]

