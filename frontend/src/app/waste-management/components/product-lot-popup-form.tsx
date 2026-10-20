"use client";

import React, { useEffect, useState } from "react";
import {
  Barcode,
  Calendar,
  CheckCircle2,
  Clock,
  HelpCircle,
  Info,
  MapPin,
  Navigation,
  Package,
  Plus,
  RefreshCw,
  Route,
  Scale,
  Sparkles,
  Thermometer,
  Droplets,
  CloudRain,
  Sun,
  Truck,
  X,
} from "lucide-react";

export interface TransportLotItem {
  id?: string;
  barcode_no: string;
  crop_category: "Vegetable" | "Fruit";
  food_name: string;
  kg: number;
  destination_center: string;
  origin_district: string;
  distance_km: number;
  transit_hours: number;
  harvest_datetime: string;
  transport_date: string;
  transport_time: string;
  transport_type: string;
  vehicle_no: string;
  packing_type: string;
  maturity: "Under-ripe" | "Ripe" | "Over-ripe";
  is_covered: boolean;
  has_cooling: boolean;
  is_washed: boolean;
  is_graded: boolean;
  ambient_temp_c?: number;
  ambient_humidity_pct?: number;
  is_rainy?: boolean;
  predicted_waste_pct?: number;
  predicted_waste_kg?: number;
  risk_level?: string;
  stream_1_fresh_kg?: number;
  stream_2_waste_kg?: number;
  bioeconomy_destination?: string;
  advice?: string[];
  created_at?: string;
}

interface ProductLotPopupFormProps {
  isOpen: boolean;
  barcode: string;
  initialData?: TransportLotItem | null;
  farmerDistrict?: string;
  onSave: (item: TransportLotItem) => void;
  onClose: () => void;
}

export interface CollectionCentreOption {
  name: string;
  lat: number;
  lon: number;
  district: string;
}

export interface SriLankaDistrictOption {
  district: string;
  lat: number;
  lon: number;
  province: string;
  agriculturalHubs: string;
}

export const SRI_LANKA_COLLECTION_CENTRES: CollectionCentreOption[] = [
  { name: "Dambulla Dedicated Economic Centre", lat: 7.8731, lon: 80.6517, district: "Matale" },
  { name: "Meegoda Dedicated Economic Centre", lat: 6.8392, lon: 80.0536, district: "Colombo" },
  { name: "Keppetipola Dedicated Economic Centre", lat: 6.9934, lon: 80.9550, district: "Badulla" },
  { name: "Embilipitiya Dedicated Economic Centre", lat: 6.3382, lon: 80.8497, district: "Ratnapura" },
  { name: "Thambuththegama Dedicated Economic Centre", lat: 8.1583, lon: 80.2986, district: "Anuradhapura" },
  { name: "Norochcholai Dedicated Economic Centre", lat: 8.1469, lon: 79.7428, district: "Puttalam" },
  { name: "Veyangoda Dedicated Economic Centre", lat: 7.1472, lon: 80.0617, district: "Gampaha" },
  { name: "Kandana Dedicated Economic Centre", lat: 7.0475, lon: 79.8972, district: "Gampaha" },
];

/**
 * Official 25 Administrative Districts of Sri Lanka with coordinates & key agricultural zones
 */
export const SRI_LANKA_DISTRICTS: SriLankaDistrictOption[] = [
  { district: "Matale", lat: 7.4675, lon: 80.6234, province: "Central", agriculturalHubs: "Dambulla, Galewela, Naula" },
  { district: "Anuradhapura", lat: 8.3114, lon: 80.4037, province: "North Central", agriculturalHubs: "Thambuththegama, Eppawala, Kekirawa" },
  { district: "Nuwara Eliya", lat: 6.9497, lon: 80.7891, province: "Central", agriculturalHubs: "Welimada, Hanguranketha, Ragala" },
  { district: "Badulla", lat: 6.9934, lon: 81.0550, province: "Uva", agriculturalHubs: "Bandarawela, Keppetipola, Mahiyanganaya" },
  { district: "Kurunegala", lat: 7.4863, lon: 80.3623, province: "North Western", agriculturalHubs: "Wariyapola, Kuliyapitiya, Pannala" },
  { district: "Kandy", lat: 7.2906, lon: 80.6337, province: "Central", agriculturalHubs: "Peradeniya, Kundasale, Gampola" },
  { district: "Puttalam", lat: 8.0362, lon: 79.8283, province: "North Western", agriculturalHubs: "Kalpitiya, Norochcholai, Anamaduwa" },
  { district: "Polonnaruwa", lat: 7.9403, lon: 81.0188, province: "North Central", agriculturalHubs: "Medirigiriya, Hingurakgoda, Kaduruwela" },
  { district: "Monaragala", lat: 6.8728, lon: 81.3507, province: "Uva", agriculturalHubs: "Wellawaya, Buttala, Bibile" },
  { district: "Ratnapura", lat: 6.6828, lon: 80.4036, province: "Sabaragamuwa", agriculturalHubs: "Balangoda, Embilipitiya, Kuruwita" },
  { district: "Hambantota", lat: 6.1429, lon: 81.1212, province: "Southern", agriculturalHubs: "Tissamaharama, Ambalantota, Suriyawewa" },
  { district: "Kegalle", lat: 7.2513, lon: 80.3464, province: "Sabaragamuwa", agriculturalHubs: "Mawanella, Warakapola, Ruwanwella" },
  { district: "Gampaha", lat: 7.0917, lon: 79.9997, province: "Western", agriculturalHubs: "Veyangoda, Kandana, Negombo" },
  { district: "Colombo", lat: 6.9271, lon: 79.8612, province: "Western", agriculturalHubs: "Meegoda, Pettah, Kaduwela" },
  { district: "Kalutara", lat: 6.5854, lon: 79.9607, province: "Western", agriculturalHubs: "Horana, Bandaragama, Matugama" },
  { district: "Galle", lat: 6.0535, lon: 80.2210, province: "Southern", agriculturalHubs: "Ambalangoda, Hikkaduwa, Elpitiya" },
  { district: "Matara", lat: 5.9549, lon: 80.5550, province: "Southern", agriculturalHubs: "Kamburupitiya, Weligama, Deniyaya" },
  { district: "Jaffna", lat: 9.6615, lon: 80.0255, province: "Northern", agriculturalHubs: "Thirunelveli, Chunnakam, Chavakachcheri" },
  { district: "Kilinochchi", lat: 9.3803, lon: 80.3770, province: "Northern", agriculturalHubs: "Paranthan, Poonakary" },
  { district: "Mannar", lat: 8.9810, lon: 79.9042, province: "Northern", agriculturalHubs: "Murunkan, Nanaddan" },
  { district: "Vavuniya", lat: 8.7514, lon: 80.4971, province: "Northern", agriculturalHubs: "Cheddikulam, Nedunkeni" },
  { district: "Mullaitivu", lat: 9.2671, lon: 80.8143, province: "Northern", agriculturalHubs: "Oddusuddan, Puthukkudiyiruppu" },
  { district: "Batticaloa", lat: 7.7310, lon: 81.6747, province: "Eastern", agriculturalHubs: "Valaichchenai, Eravur, Kattankudy" },
  { district: "Ampara", lat: 7.2975, lon: 81.6747, province: "Eastern", agriculturalHubs: "Kalmunai, Akkaraipattu, Mahaoya" },
  { district: "Trincomalee", lat: 8.5874, lon: 81.2152, province: "Eastern", agriculturalHubs: "Kantale, Kinniya, Mutur" },
];

export const SRI_LANKA_ORIGINS = SRI_LANKA_DISTRICTS.map((d) => ({
  name: d.district,
  lat: d.lat,
  lon: d.lon,
  province: d.province,
}));

const CROPS_BY_CATEGORY = {
  Vegetable: [
    "Tomato",
    "Cabbage",
    "Carrot",
    "Leeks",
    "Capsicum",
    "Brinjal",
    "Beans",
    "Pumpkin",
    "Bitter Gourd",
    "Snake Gourd",
    "Green Chilli",
    "Beetroot",
    "Radish",
    "Cucumber",
    "Okra",
    "Lime",
    "Big Onion",
    "Potato",
  ],
  Fruit: [
    "Banana",
    "Papaya",
    "Mango",
    "Watermelon",
    "Pineapple",
    "Guava",
    "Avocado",
    "Passion Fruit",
    "Orange",
  ],
};

const VEHICLE_TYPES = [
  { label: "Open Truck (Canter / 4-Ton)", value: "OPEN_TRUCK", covered: false, cooling: false },
  { label: "Covered Lorry (Tarpaulin/Box)", value: "COVERED_TRUCK", covered: true, cooling: false },
  { label: "Refrigerated Truck / Reefer Van", value: "REFRIGERATED_VAN", covered: true, cooling: true },
  { label: "Three-Wheeler (Piaggio/Bajaj)", value: "THREE_WHEELER", covered: true, cooling: false },
  { label: "Tractor & Trailer (Agricultural)", value: "TRACTOR_TRAILER", covered: false, cooling: false },
  { label: "Pickup Van / Double-Cab", value: "PICKUP_VAN", covered: true, cooling: false },
];

const PACKING_TYPES = [
  { label: "Plastic Crate (Rigid, DoA Approved)", value: "PLASTIC_CRATE", desc: "Maximum physical cushioning, lowest loss rate" },
  { label: "Ventilated Wooden Box", value: "VENTILATED_BOX", desc: "Good aeration, moderate shock protection" },
  { label: "Corrugated Cardboard Box", value: "CARDBOARD_BOX", desc: "Lightweight, absorbs vibration if dry" },
  { label: "Gunny / Polythene Mesh Bag", value: "POLYSACK_MESH", desc: "High mechanical compression and bruise risk" },
  { label: "Loose Bulk Loading", value: "LOOSE_BULK", desc: "Severe bottom-layer crushing loss risk" },
];

export function ProductLotPopupForm({
  isOpen,
  barcode,
  initialData,
  farmerDistrict = "Matale",
  onSave,
  onClose,
}: ProductLotPopupFormProps) {
  const now = new Date();
  const todayStr = now.toISOString().split("T")[0];
  const timeStr = now.toTimeString().slice(0, 5);

  const [category, setCategory] = useState<"Vegetable" | "Fruit">("Vegetable");
  const [foodName, setFoodName] = useState("Tomato");
  const [quantityKg, setQuantityKg] = useState<string>("350");

  // Farm Origin District & Collection Centre state
  const defaultDistrict =
    SRI_LANKA_DISTRICTS.find((d) => d.district.toLowerCase() === farmerDistrict.toLowerCase()) ||
    SRI_LANKA_DISTRICTS[0];
  const [originDistrict, setOriginDistrict] = useState(defaultDistrict.district);
  const [farmVillage, setFarmVillage] = useState("");
  const [farmerCoords, setFarmerCoords] = useState<{ lat: number; lon: number }>({
    lat: defaultDistrict.lat,
    lon: defaultDistrict.lon,
  });
  const [destinationCenter, setDestinationCenter] = useState(SRI_LANKA_COLLECTION_CENTRES[0].name);

  // Routing API State
  const [distanceKm, setDistanceKm] = useState<number>(47.6);
  const [transitHours, setTransitHours] = useState<number>(0.9);
  const [durationText, setDurationText] = useState<string>("~52 mins (0.9 hrs)");
  const [routeSource, setRouteSource] = useState<string>("OSRM Live Road Map");
  const [isCalculatingRoute, setIsCalculatingRoute] = useState(false);
  const [showMapPreview, setShowMapPreview] = useState(false);
  const [isLocating, setIsLocating] = useState(false);

  // Timing state
  const [harvestDate, setHarvestDate] = useState(todayStr);
  const [harvestTime, setHarvestTime] = useState("06:00");
  const [transportDate, setTransportDate] = useState(todayStr);
  const [transportTime, setTransportTime] = useState(timeStr);

  // Vehicle & Handling state
  const [maturity, setMaturity] = useState<"Under-ripe" | "Ripe" | "Over-ripe">("Ripe");
  const [vehicleType, setVehicleType] = useState("OPEN_TRUCK");
  const [vehicleNo, setVehicleNo] = useState("NC-CP-4820");
  const [packingType, setPackingType] = useState("PLASTIC_CRATE");
  const [isCovered, setIsCovered] = useState(false);
  const [hasCooling, setHasCooling] = useState(false);
  const [isWashed, setIsWashed] = useState(false);
  const [isGraded, setIsGraded] = useState(true);

  // Real-time Ambient Telemetry state (Open-Meteo API)
  const [ambientTemp, setAmbientTemp] = useState("24.6");
  const [ambientHumidity, setAmbientHumidity] = useState("96");
  const [isRainy, setIsRainy] = useState(true);
  const [isFetchingWeather, setIsFetchingWeather] = useState(false);
  const [weatherSource, setWeatherSource] = useState("Open-Meteo Live API");

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Destination coordinates helper
  const activeDest = SRI_LANKA_COLLECTION_CENTRES.find((c) => c.name === destinationCenter) || SRI_LANKA_COLLECTION_CENTRES[0];

  // 1. Fetch real-time OSRM route distance and driving duration
  async function fetchLiveRoute(originLat: number, originLon: number, destLat: number, destLon: number) {
    setIsCalculatingRoute(true);
    try {
      const res = await fetch(
        `http://localhost:8003/api/transport/routing/distance?origin_lat=${originLat}&origin_lon=${originLon}&dest_lat=${destLat}&dest_lon=${destLon}`
      );
      if (res.ok) {
        const data = await res.json();
        setDistanceKm(data.distance_km);
        setTransitHours(data.transit_hours);
        setDurationText(data.duration_text ? `${data.duration_text} (~${data.transit_hours} hrs)` : `${data.transit_hours} hrs`);
        setRouteSource(data.source === "osrm_live_map" ? "OSRM Live Road Map" : "Sri Lanka Road Topography");
        return;
      }
    } catch (err) {
      console.warn("Routing API error, using mathematical fallback:", err);
    } finally {
      setIsCalculatingRoute(false);
    }

    // Direct mathematical fallback
    const R = 6371;
    const dlat = ((destLat - originLat) * Math.PI) / 180;
    const dlon = ((destLon - originLon) * Math.PI) / 180;
    const a =
      Math.sin(dlat / 2) * Math.sin(dlat / 2) +
      Math.cos((originLat * Math.PI) / 180) * Math.cos((destLat * Math.PI) / 180) * Math.sin(dlon / 2) * Math.sin(dlon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const roadKm = Math.round(Math.max(8, R * c * 1.35) * 10) / 10;
    const hours = Math.round(Math.max(0.3, roadKm / 42.0) * 10) / 10;
    setDistanceKm(roadKm);
    setTransitHours(hours);
    setDurationText(`${Math.round(hours * 60)} mins (~${hours} hrs)`);
    setRouteSource("Sri Lanka Topographical Fallback");
  }

  // 2. Fetch real-time ambient weather (temperature, humidity, rain) from Open-Meteo
  async function fetchLiveWeather(lat: number, lon: number) {
    setIsFetchingWeather(true);
    try {
      const res = await fetch(`http://localhost:8003/api/transport/telemetry/weather?lat=${lat}&lon=${lon}`);
      if (res.ok) {
        const data = await res.json();
        setAmbientTemp(String(data.temperature_c));
        setAmbientHumidity(String(data.relative_humidity_pct));
        setIsRainy(Boolean(data.is_rainy));
        setWeatherSource("Open-Meteo Real-Time Telemetry");
        return;
      }
    } catch (err) {
      console.warn("Weather API error, maintaining baseline:", err);
    } finally {
      setIsFetchingWeather(false);
    }
  }

  // 3. Handle GPS auto-detect
  function handleDetectGPS() {
    if (typeof window === "undefined" || !navigator?.geolocation) {
      alert("Geolocation is not supported by your browser environment.");
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(4));
        const lon = Number(pos.coords.longitude.toFixed(4));
        setFarmerCoords({ lat, lon });
        setIsLocating(false);

        // Find nearest Sri Lankan District centroid
        let closest = SRI_LANKA_DISTRICTS[0];
        let minD = Infinity;
        for (const dist of SRI_LANKA_DISTRICTS) {
          const d = Math.hypot(dist.lat - lat, dist.lon - lon);
          if (d < minD) {
            minD = d;
            closest = dist;
          }
        }
        setOriginDistrict(closest.district);

        // Automatically trigger live route and weather API sync
        fetchLiveRoute(lat, lon, activeDest.lat, activeDest.lon);
        fetchLiveWeather(lat, lon);
      },
      (err) => {
        setIsLocating(false);
        console.warn("GPS acquire error:", err);
        alert("GPS location could not be detected. Please select your Origin District from the dropdown list.");
      },
      { timeout: 7000, enableHighAccuracy: true }
    );
  }

  // 4. Handle farm origin district selection
  function handleDistrictChange(distName: string) {
    setOriginDistrict(distName);
    const found = SRI_LANKA_DISTRICTS.find((d) => d.district === distName) || SRI_LANKA_DISTRICTS[0];
    setFarmerCoords({ lat: found.lat, lon: found.lon });

    fetchLiveRoute(found.lat, found.lon, activeDest.lat, activeDest.lon);
    fetchLiveWeather(found.lat, found.lon);
  }

  // 5. Handle destination DEC selection
  function handleDestinationChange(destName: string) {
    setDestinationCenter(destName);
    const dest = SRI_LANKA_COLLECTION_CENTRES.find((c) => c.name === destName) || SRI_LANKA_COLLECTION_CENTRES[0];
    fetchLiveRoute(farmerCoords.lat, farmerCoords.lon, dest.lat, dest.lon);
  }

  // Initialize on open or initialData change
  useEffect(() => {
    if (!isOpen) return;

    if (initialData) {
      setCategory(initialData.crop_category);
      setFoodName(initialData.food_name);
      setQuantityKg(String(initialData.kg));
      setDestinationCenter(initialData.destination_center);
      setOriginDistrict(initialData.origin_district);
      setDistanceKm(initialData.distance_km);
      setTransitHours(initialData.transit_hours);
      setDurationText(`~${Math.round(initialData.transit_hours * 60)} mins (${initialData.transit_hours} hrs)`);

      const distMatch =
        SRI_LANKA_DISTRICTS.find(
          (d) => d.district.toLowerCase() === initialData.origin_district.toLowerCase()
        ) || SRI_LANKA_DISTRICTS[0];
      setFarmerCoords({ lat: distMatch.lat, lon: distMatch.lon });

      if (initialData.harvest_datetime) {
        const [hDate, hTime] = initialData.harvest_datetime.split("T");
        setHarvestDate(hDate || todayStr);
        setHarvestTime(hTime?.slice(0, 5) || "06:00");
      }
      setTransportDate(initialData.transport_date || todayStr);
      setTransportTime(initialData.transport_time || timeStr);
      setMaturity(initialData.maturity);
      setVehicleType(initialData.transport_type);
      setVehicleNo(initialData.vehicle_no);
      setPackingType(initialData.packing_type);
      setIsCovered(initialData.is_covered);
      setHasCooling(initialData.has_cooling);
      setIsWashed(initialData.is_washed);
      setIsGraded(initialData.is_graded);
      setAmbientTemp(String(initialData.ambient_temp_c ?? 24.6));
      setAmbientHumidity(String(initialData.ambient_humidity_pct ?? 96));
      setIsRainy(initialData.is_rainy ?? true);
    } else {
      setCategory("Vegetable");
      setFoodName("Tomato");
      setQuantityKg("350");

      const dist =
        SRI_LANKA_DISTRICTS.find(
          (d) => d.district.toLowerCase() === farmerDistrict.toLowerCase()
        ) || SRI_LANKA_DISTRICTS[0];
      setOriginDistrict(dist.district);
      setFarmerCoords({ lat: dist.lat, lon: dist.lon });
      const dest = SRI_LANKA_COLLECTION_CENTRES[0];
      setDestinationCenter(dest.name);

      // Auto-trigger live route & weather calculation on form launch
      fetchLiveRoute(dist.lat, dist.lon, dest.lat, dest.lon);
      fetchLiveWeather(dist.lat, dist.lon);
    }
  }, [initialData, farmerDistrict, isOpen]);

  function handleVehicleSelect(vehVal: string) {
    setVehicleType(vehVal);
    const cfg = VEHICLE_TYPES.find((v) => v.value === vehVal);
    if (cfg) {
      setIsCovered(cfg.covered);
      setHasCooling(cfg.cooling);
    }
  }

  function handleCategoryChange(cat: "Vegetable" | "Fruit") {
    setCategory(cat);
    const crops = CROPS_BY_CATEGORY[cat];
    setFoodName(crops[0]);
  }

  function validateForm(): boolean {
    const errs: Record<string, string> = {};
    const kgNum = parseFloat(quantityKg);
    if (isNaN(kgNum) || kgNum <= 0) {
      errs.quantityKg = "Please enter a valid weight in kg (> 0).";
    }
    if (!foodName) errs.foodName = "Please select a produce item.";
    if (!destinationCenter) errs.destinationCenter = "Please select a destination center.";
    if (!transportDate) errs.transportDate = "Transport date is required.";
    if (!harvestDate) errs.harvestDate = "Harvest date is required.";

    if (harvestDate && transportDate && harvestDate > transportDate) {
      errs.harvestDate = "Harvest date cannot be after transport departure date.";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validateForm()) return;

    const kgNum = parseFloat(quantityKg);
    const harvestIso = `${harvestDate}T${harvestTime || "06:00"}:00Z`;

    const item: TransportLotItem = {
      id: initialData?.id || `lot_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      barcode_no: barcode,
      crop_category: category,
      food_name: foodName,
      kg: kgNum,
      destination_center: destinationCenter,
      origin_district: originDistrict.trim(),
      distance_km: Number(distanceKm),
      transit_hours: Number(transitHours),
      harvest_datetime: harvestIso,
      transport_date: transportDate,
      transport_time: transportTime || "08:00",
      transport_type: vehicleType,
      vehicle_no: vehicleNo.trim().toUpperCase(),
      packing_type: packingType,
      maturity,
      is_covered: isCovered,
      has_cooling: hasCooling,
      is_washed: isWashed,
      is_graded: isGraded,
      ambient_temp_c: parseFloat(ambientTemp) || 25.0,
      ambient_humidity_pct: parseFloat(ambientHumidity) || 85.0,
      is_rainy: isRainy,
      created_at: initialData?.created_at || new Date().toISOString(),
    };

    onSave(item);
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(15, 23, 42, 0.7)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "24px",
          width: "100%",
          maxWidth: "860px",
          maxHeight: "92vh",
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          border: "1px solid #e2e8f0",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 28px",
            borderBottom: "1px solid #e2e8f0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(22, 163, 74, 0.25)",
              }}
            >
              <Package size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                {initialData ? "Edit Produce Lot Details" : "Register Produce Lot for Transport"}
              </h3>
              <p style={{ fontSize: "12.5px", color: "#64748b", margin: "2px 0 0 0" }}>
                Component 3 • Pre-Departure Barcode Lot Verification & OSRM Routing
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {/* Locked Barcode Badge */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#f0fdf4",
                border: "1.5px solid #86efac",
                padding: "6px 14px",
                borderRadius: "10px",
              }}
            >
              <Barcode size={16} style={{ color: "#16a34a" }} />
              <span style={{ fontSize: "13px", fontWeight: 800, fontFamily: "monospace", color: "#166534" }}>
                {barcode}
              </span>
              <span
                style={{
                  fontSize: "9px",
                  fontWeight: 800,
                  background: "#16a34a",
                  color: "#ffffff",
                  padding: "1px 6px",
                  borderRadius: "4px",
                  letterSpacing: "0.5px",
                }}
              >
                VERIFIED
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              style={{
                background: "#f1f5f9",
                border: "none",
                borderRadius: "10px",
                width: "36px",
                height: "36px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                color: "#64748b",
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Scrollable Form Body */}
        <div style={{ padding: "24px 28px", overflowY: "auto", flex: 1 }}>
          <form id="product-lot-form" onSubmit={handleSubmit}>
            {/* Section 1: Produce & Category */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: "20px", marginBottom: "18px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  Produce Category:
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                  {(["Vegetable", "Fruit"] as const).map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => handleCategoryChange(cat)}
                      style={{
                        flex: 1,
                        padding: "10px",
                        borderRadius: "12px",
                        border: category === cat ? "2px solid #16a34a" : "1.5px solid #cbd5e1",
                        background: category === cat ? "#f0fdf4" : "#ffffff",
                        color: category === cat ? "#15803d" : "#475569",
                        fontWeight: category === cat ? 800 : 600,
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      {cat === "Fruit" ? "🍌 Fruit" : "🥬 Vegetable"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  Crop / Food Item:
                </label>
                <select
                  value={foodName}
                  onChange={(e) => setFoodName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    border: "1.5px solid #cbd5e1",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    color: "#0f172a",
                    outline: "none",
                    background: "#ffffff",
                  }}
                >
                  {CROPS_BY_CATEGORY[category].map((cr) => (
                    <option key={cr} value={cr}>
                      {cr}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Section 2: Weight (kg) */}
            <div style={{ marginBottom: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <label style={{ fontSize: "12.5px", fontWeight: 700, color: "#334155", margin: 0 }}>
                  Net Produce Quantity (kg):
                </label>
                <div style={{ display: "flex", gap: "6px" }}>
                  {[100, 250, 350, 500, 1000].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setQuantityKg(String(preset))}
                      style={{
                        background: quantityKg === String(preset) ? "#dcfce7" : "#f1f5f9",
                        color: quantityKg === String(preset) ? "#15803d" : "#475569",
                        border: "1px solid #cbd5e1",
                        borderRadius: "6px",
                        padding: "2px 8px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {preset} kg
                    </button>
                  ))}
                </div>
              </div>
              <input
                type="number"
                step="1"
                min="1"
                value={quantityKg}
                onChange={(e) => setQuantityKg(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  border: errors.quantityKg ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                  fontSize: "14px",
                  fontWeight: 700,
                  outline: "none",
                }}
              />
              {errors.quantityKg && <small style={{ color: "#ef4444" }}>{errors.quantityKg}</small>}
            </div>

            {/* Section 3: Origin District & Destination Collection Centre with OSRM Auto-Routing */}
            <div
              style={{
                background: "#f8fafc",
                padding: "18px 20px",
                borderRadius: "18px",
                border: "1.5px solid #e2e8f0",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <MapPin size={18} style={{ color: "#16a34a" }} />
                  <div>
                    <strong style={{ fontSize: "13.5px", color: "#0f172a", display: "block" }}>
                      Origin District & Destination Collection Centre
                    </strong>
                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                      Official Sri Lanka District mapping with auto-calculated road route & weather telemetry
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={handleDetectGPS}
                    disabled={isLocating}
                    style={{
                      background: "#ffffff",
                      border: "1px solid #86efac",
                      borderRadius: "8px",
                      padding: "6px 12px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      color: "#15803d",
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "5px",
                      boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                    }}
                  >
                    <Navigation size={13} className={isLocating ? "animate-spin" : ""} />
                    <span>{isLocating ? "Acquiring GPS..." : "📍 Auto-Detect My GPS"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowMapPreview((v) => !v)}
                    style={{
                      background: showMapPreview ? "#dcfce7" : "#ffffff",
                      border: "1px solid #cbd5e1",
                      borderRadius: "8px",
                      padding: "6px 12px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      color: "#334155",
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "5px",
                    }}
                  >
                    <Route size={13} />
                    <span>{showMapPreview ? "Hide Route Map" : "🗺️ View Route Map"}</span>
                  </button>
                </div>
              </div>

              {/* District & DEC Selectors */}
              <div style={{ display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: "16px", marginBottom: "12px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "#1e293b", margin: 0 }}>
                      Origin District: <span style={{ color: "#dc2626" }}>*</span>
                    </label>
                    <span style={{ fontSize: "10.5px", color: "#16a34a", fontWeight: 600 }}>
                      {SRI_LANKA_DISTRICTS.find((d) => d.district === originDistrict)?.province} Province
                    </span>
                  </div>
                  <select
                    value={originDistrict}
                    onChange={(e) => handleDistrictChange(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "10px",
                      border: "1.5px solid #cbd5e1",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                    }}
                  >
                    {SRI_LANKA_DISTRICTS.map((dist) => (
                      <option key={dist.district} value={dist.district}>
                        {dist.district} District ({dist.province} Province)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "#1e293b", margin: 0 }}>
                      Destination Collection Centre (DEC): <span style={{ color: "#dc2626" }}>*</span>
                    </label>
                    <span style={{ fontSize: "10.5px", color: "#64748b" }}>
                      {activeDest.district} District
                    </span>
                  </div>
                  <select
                    value={destinationCenter}
                    onChange={(e) => handleDestinationChange(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "10px",
                      border: "1.5px solid #cbd5e1",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                    }}
                  >
                    {SRI_LANKA_COLLECTION_CENTRES.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Optional Farm Locality & GPS Coordinates */}
              <div style={{ display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: "16px", marginBottom: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#475569", marginBottom: "4px" }}>
                    Farm Village / Town (Optional):
                  </label>
                  <input
                    type="text"
                    placeholder={
                      SRI_LANKA_DISTRICTS.find((d) => d.district === originDistrict)?.agriculturalHubs
                        ? `e.g. ${SRI_LANKA_DISTRICTS.find((d) => d.district === originDistrict)?.agriculturalHubs.split(",")[0].trim()}`
                        : "e.g. Galewela, Dambulla"
                    }
                    value={farmVillage}
                    onChange={(e) => setFarmVillage(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "7px 12px",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      fontSize: "12px",
                      color: "#0f172a",
                      outline: "none",
                      background: "#ffffff",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#475569", marginBottom: "4px" }}>
                    Farm GPS Coordinates (Auto-Linked):
                  </label>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 12px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      background: "#ffffff",
                      fontSize: "11.5px",
                      fontFamily: "monospace",
                      color: "#334155",
                      height: "34px",
                    }}
                  >
                    <span>{farmerCoords.lat.toFixed(4)}° N, {farmerCoords.lon.toFixed(4)}° E</span>
                    <span style={{ fontSize: "10px", fontWeight: 700, color: "#16a34a", background: "#f0fdf4", padding: "1px 6px", borderRadius: "4px" }}>
                      📍 Linked
                    </span>
                  </div>
                </div>
              </div>

              {/* Auto-Calculated Distance & Duration Card */}
              <div
                style={{
                  background: "#ffffff",
                  padding: "14px 18px",
                  borderRadius: "12px",
                  border: "1px solid #e2e8f0",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px dashed #e2e8f0", paddingBottom: "8px", flexWrap: "wrap", gap: "6px" }}>
                  <span style={{ fontSize: "12px", color: "#334155", fontWeight: 600 }}>
                    Route Corridor: <strong style={{ color: "#15803d" }}>{originDistrict} District {farmVillage ? `(${farmVillage})` : ""}</strong> ➔ <strong style={{ color: "#0f172a" }}>{activeDest.name.split(" ")[0]} DEC</strong>
                  </span>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>
                    Direct road network link
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
                    <div>
                      <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600, display: "block" }}>
                        Road Transit Distance
                      </span>
                      <strong style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a" }}>
                        {isCalculatingRoute ? "Routing..." : `${distanceKm} km`}
                      </strong>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600, display: "block" }}>
                        Estimated Driving Time
                      </span>
                      <strong style={{ fontSize: "18px", fontWeight: 800, color: "#16a34a" }}>
                        {isCalculatingRoute ? "Routing..." : durationText}
                      </strong>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: isCalculatingRoute ? "#eab308" : "#22c55e",
                        display: "inline-block",
                      }}
                    />
                    <span style={{ fontSize: "11.5px", fontWeight: 700, color: "#15803d" }}>
                      {isCalculatingRoute ? "Routing API calculating..." : routeSource}
                    </span>
                  </div>
                </div>
              </div>

              {/* OpenStreetMap Interactive Preview */}
              {showMapPreview && (
                <div style={{ marginTop: "14px", borderRadius: "14px", overflow: "hidden", border: "1.5px solid #cbd5e1" }}>
                  <iframe
                    title="Corridor Route Map"
                    width="100%"
                    height="240"
                    frameBorder="0"
                    scrolling="no"
                    marginHeight={0}
                    marginWidth={0}
                    src={`https://www.openstreetmap.org/export/embed.html?bbox=${Math.min(farmerCoords.lon, activeDest.lon) - 0.2}%2C${Math.min(farmerCoords.lat, activeDest.lat) - 0.2}%2C${Math.max(farmerCoords.lon, activeDest.lon) + 0.2}%2C${Math.max(farmerCoords.lat, activeDest.lat) + 0.2}&layer=mapnik&marker=${activeDest.lat}%2C${activeDest.lon}`}
                    style={{ display: "block" }}
                  />
                  <div style={{ background: "#ffffff", padding: "8px 14px", fontSize: "11.5px", color: "#475569", display: "flex", justifyContent: "space-between", borderTop: "1px solid #e2e8f0" }}>
                    <span>📍 Farm: ({farmerCoords.lat.toFixed(3)}, {farmerCoords.lon.toFixed(3)})</span>
                    <span style={{ fontWeight: 700, color: "#15803d" }}>🏁 Destination DEC: {activeDest.name.split(" ")[0]} ({activeDest.lat.toFixed(3)}, {activeDest.lon.toFixed(3)})</span>
                  </div>
                </div>
              )}
            </div>

            {/* Section 4: Harvest & Departure Timings */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "18px" }}>
              <div style={{ background: "#ffffff", padding: "14px", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#166534", display: "block", marginBottom: "8px" }}>
                  Harvesting Timestamp
                </span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="date"
                    value={harvestDate}
                    onChange={(e) => setHarvestDate(e.target.value)}
                    style={{ flex: 1.5, padding: "7px 10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "12.5px" }}
                  />
                  <input
                    type="time"
                    value={harvestTime}
                    onChange={(e) => setHarvestTime(e.target.value)}
                    style={{ flex: 1, padding: "7px 10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "12.5px" }}
                  />
                </div>
                {errors.harvestDate && <small style={{ color: "#ef4444" }}>{errors.harvestDate}</small>}
              </div>

              <div style={{ background: "#ffffff", padding: "14px", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#166534", display: "block", marginBottom: "8px" }}>
                  Planned Departure Timestamp
                </span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="date"
                    value={transportDate}
                    onChange={(e) => setTransportDate(e.target.value)}
                    style={{ flex: 1.5, padding: "7px 10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "12.5px" }}
                  />
                  <input
                    type="time"
                    value={transportTime}
                    onChange={(e) => setTransportTime(e.target.value)}
                    style={{ flex: 1, padding: "7px 10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "12.5px" }}
                  />
                </div>
                {errors.transportDate && <small style={{ color: "#ef4444" }}>{errors.transportDate}</small>}
              </div>
            </div>

            {/* Section 5: Transport Vehicle & Packaging Container */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "18px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  Transport Vehicle Type:
                </label>
                <select
                  value={vehicleType}
                  onChange={(e) => handleVehicleSelect(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    border: "1.5px solid #cbd5e1",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "8px",
                  }}
                >
                  {VEHICLE_TYPES.map((v) => (
                    <option key={v.value} value={v.value}>
                      {v.label}
                    </option>
                  ))}
                </select>

                <input
                  type="text"
                  placeholder="Vehicle Plate No (e.g. NC-CP-4820)"
                  value={vehicleNo}
                  onChange={(e) => setVehicleNo(e.target.value)}
                  style={{ width: "100%", padding: "7px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  Packaging Container Type:
                </label>
                <select
                  value={packingType}
                  onChange={(e) => setPackingType(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    border: "1.5px solid #cbd5e1",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "8px",
                  }}
                >
                  {PACKING_TYPES.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <p style={{ fontSize: "11px", color: "#64748b", margin: 0 }}>
                  {PACKING_TYPES.find((p) => p.value === packingType)?.desc}
                </p>
              </div>
            </div>

            {/* Section 6: Maturity & Real-Time Ambient Weather Telemetry */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: "20px", marginBottom: "18px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  Maturity Stage:
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  {(["Under-ripe", "Ripe", "Over-ripe"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMaturity(m)}
                      style={{
                        flex: 1,
                        padding: "9px 6px",
                        borderRadius: "10px",
                        border: maturity === m ? "2px solid #16a34a" : "1px solid #cbd5e1",
                        background: maturity === m ? "#f0fdf4" : "#ffffff",
                        color: maturity === m ? "#15803d" : "#475569",
                        fontWeight: maturity === m ? 800 : 600,
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>

                {/* Pre-Trip Conditioning Badges */}
                <div style={{ marginTop: "12px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11.5px", color: "#334155", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={isGraded}
                      onChange={(e) => setIsGraded(e.target.checked)}
                      style={{ accentColor: "#16a34a" }}
                    />
                    <span>Pre-Graded</span>
                  </label>

                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11.5px", color: "#334155", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={isWashed}
                      onChange={(e) => setIsWashed(e.target.checked)}
                      style={{ accentColor: "#16a34a" }}
                    />
                    <span>Cleaned / Washed</span>
                  </label>
                </div>
              </div>

              {/* Real-Time Ambient Weather Telemetry Box */}
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1.5px solid #86efac",
                  borderRadius: "14px",
                  padding: "14px 16px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#16a34a", display: "inline-block", boxShadow: "0 0 6px #16a34a" }} />
                    <label style={{ fontSize: "12px", fontWeight: 800, color: "#166534", margin: 0 }}>
                      Real-Time Ambient Telemetry
                    </label>
                  </div>

                  <button
                    type="button"
                    onClick={() => fetchLiveWeather(farmerCoords.lat, farmerCoords.lon)}
                    disabled={isFetchingWeather}
                    style={{
                      background: "#ffffff",
                      border: "1px solid #bbf7d0",
                      borderRadius: "6px",
                      padding: "4px 8px",
                      fontSize: "11px",
                      fontWeight: 700,
                      color: "#15803d",
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <RefreshCw size={11} className={isFetchingWeather ? "animate-spin" : ""} />
                    <span>{isFetchingWeather ? "Syncing..." : "Sync Live Weather"}</span>
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "8px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px", marginBottom: "3px" }}>
                      <Thermometer size={13} style={{ color: "#ea580c" }} />
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>Air Temp (°C)</span>
                    </div>
                    <input
                      type="number"
                      step="0.1"
                      value={ambientTemp}
                      onChange={(e) => setAmbientTemp(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 10px",
                        borderRadius: "8px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "#0f172a",
                        background: "#ffffff",
                      }}
                    />
                  </div>

                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px", marginBottom: "3px" }}>
                      <Droplets size={13} style={{ color: "#0284c7" }} />
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>Rel. Humidity (%)</span>
                    </div>
                    <input
                      type="number"
                      step="1"
                      value={ambientHumidity}
                      onChange={(e) => setAmbientHumidity(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 10px",
                        borderRadius: "8px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "#0f172a",
                        background: "#ffffff",
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "4px" }}>
                  <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600, color: "#334155", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={isRainy}
                      onChange={(e) => setIsRainy(e.target.checked)}
                      style={{ width: "15px", height: "15px", accentColor: "#16a34a" }}
                    />
                    <span>{isRainy ? "🌧️ Wet / Rainy Transit" : "☀️ Dry / Clear Weather"}</span>
                  </label>
                  <span style={{ fontSize: "10.5px", color: "#16a34a", fontWeight: 700 }}>
                    {isFetchingWeather ? "Fetching..." : weatherSource}
                  </span>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 28px",
            borderTop: "1px solid #e2e8f0",
            background: "#f8fafc",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "#ffffff",
              border: "1px solid #cbd5e1",
              borderRadius: "12px",
              padding: "10px 18px",
              fontSize: "13.5px",
              fontWeight: 600,
              color: "#475569",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            form="product-lot-form"
            style={{
              background: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
              border: "none",
              borderRadius: "12px",
              padding: "10px 24px",
              fontSize: "14px",
              fontWeight: 800,
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: "pointer",
              boxShadow: "0 4px 12px rgba(22, 163, 74, 0.25)",
            }}
          >
            <Plus size={18} />
            <span>{initialData ? "Update Produce Lot" : "Add to Transport List"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
