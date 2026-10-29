/**
 * Master catalog constants and validation lists for Component 1 (Market Demand & Profit Risk).
 * Strictly mirrors shared project schemas and verified Dedicated Economic Centres (DECs).
 */

export interface CropMetadata {
  crop_id: string;
  name_en: string;
  name_si: string;
  category: string;
  growth_duration_days: number;
  primary_zones: string[];
  default_unit: string;
  typical_yield_kg_per_acre: number;
}

export interface DistrictMetadata {
  id: string;
  name: string;
  zone: string;
  is_pilot: boolean;
}

export interface MarketMetadata {
  id: string;
  name: string;
  short_name: string;
  region: string;
  is_pilot_recommended: boolean;
}

// 7 Master Candidate Crops from shared/constants/crop_catalog.json
export const MASTER_CROPS: CropMetadata[] = [
  {
    crop_id: "CR_MAIZE",
    name_en: "Maize",
    name_si: "ඉරිඟු (Bada Iringu)",
    category: "Grain",
    growth_duration_days: 110,
    primary_zones: ["Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 2000,
  },
  {
    crop_id: "CR_CHILLI",
    name_en: "Chilli",
    name_si: "මිරිස් (Miris)",
    category: "Condiment",
    growth_duration_days: 120,
    primary_zones: ["Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 1500,
  },
  {
    crop_id: "CR_MUNG_BEAN",
    name_en: "Green Gram / Mung Bean",
    name_si: "මුං ඇට (Mung Ata)",
    category: "Legume",
    growth_duration_days: 75,
    primary_zones: ["Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 600,
  },
  {
    crop_id: "CR_TOMATO",
    name_en: "Tomato",
    name_si: "තක්කාලි (Thakkali)",
    category: "Vegetable",
    growth_duration_days: 90,
    primary_zones: ["Upcountry", "Intermediate Zone", "Low Country"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 4500,
  },
  {
    crop_id: "CR_BRINJAL",
    name_en: "Brinjal (Eggplant)",
    name_si: "වම්බටු (Wambatu)",
    category: "Vegetable",
    growth_duration_days: 130,
    primary_zones: ["Low Country Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 5000,
  },
  {
    crop_id: "CR_OKRA",
    name_en: "Okra (Lady's Finger)",
    name_si: "බණ්ඩක්කා (Bandakka)",
    category: "Vegetable",
    growth_duration_days: 85,
    primary_zones: ["Low Country Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 3500,
  },
  {
    crop_id: "CR_PUMPKIN",
    name_en: "Pumpkin",
    name_si: "වට්ටක්කා (Wattakka)",
    category: "Vegetable",
    growth_duration_days: 110,
    primary_zones: ["Dry Zone", "Intermediate Zone"],
    default_unit: "kg",
    typical_yield_kg_per_acre: 6000,
  },
];

// 5 Farmer-Facing Supported Crops for Component 1 (Excludes Tomato and Pumpkin per model scope)
// Displayed exactly: Okra, Brinjal (Eggplant), Maize (Corn), Mung Bean (Green Gram), Chilli
export interface FrontendCropMetadata {
  crop_id: string;
  name_en: string;
  name_si: string;
  category: string;
  image_name: string;
  alt_text: string;
}

export const SUPPORTED_FRONTEND_CROPS: FrontendCropMetadata[] = [
  {
    crop_id: "CR_OKRA",
    name_en: "Okra",
    name_si: "බණ්ඩක්කා (Bandakka)",
    category: "Vegetable",
    image_name: "okra.jpg",
    alt_text: "Fresh green okra pods",
  },
  {
    crop_id: "CR_BRINJAL",
    name_en: "Brinjal (Eggplant)",
    name_si: "වම්බටු (Wambatu)",
    category: "Vegetable",
    image_name: "brinjal.jpg",
    alt_text: "Fresh glossy purple brinjals",
  },
  {
    crop_id: "CR_MAIZE",
    name_en: "Maize (Corn)",
    name_si: "ඉරිඟු (Bada Iringu)",
    category: "Grain",
    image_name: "maize.jpg",
    alt_text: "Fresh golden yellow maize corn cobs",
  },
  {
    crop_id: "CR_MUNG_BEAN",
    name_en: "Mung Bean (Green Gram)",
    name_si: "මුං ඇට (Mung Ata)",
    category: "Legume",
    image_name: "mung-bean.jpg",
    alt_text: "Raw green gram mung bean seeds",
  },
  {
    crop_id: "CR_CHILLI",
    name_en: "Chilli",
    name_si: "මිරිස් (Miris)",
    category: "Condiment",
    image_name: "chilli.jpg",
    alt_text: "Fresh bright red and green chillies",
  },
];


// Valid Sri Lankan Districts from shared/constants/srilanka_districts.json
export const SRI_LANKA_DISTRICTS: DistrictMetadata[] = [
  // Pilot Districts
  { id: "LK-32", name: "Matara", zone: "Wet / Intermediate Zone", is_pilot: true },
  { id: "LK-33", name: "Hambantota", zone: "Dry Zone", is_pilot: true },
  // Southern Province
  { id: "LK-31", name: "Galle", zone: "Wet Zone", is_pilot: false },
  // Western Province
  { id: "LK-11", name: "Colombo", zone: "Wet Zone", is_pilot: false },
  { id: "LK-12", name: "Gampaha", zone: "Wet Zone", is_pilot: false },
  { id: "LK-13", name: "Kalutara", zone: "Wet Zone", is_pilot: false },
  // Central Province
  { id: "LK-21", name: "Kandy", zone: "Upcountry Wet Zone", is_pilot: false },
  { id: "LK-22", name: "Matale", zone: "Intermediate Zone", is_pilot: false },
  { id: "LK-23", name: "Nuwara Eliya", zone: "Upcountry Wet Zone", is_pilot: false },
  // North Central Province
  { id: "LK-71", name: "Anuradhapura", zone: "Dry Zone", is_pilot: false },
  { id: "LK-72", name: "Polonnaruwa", zone: "Dry Zone", is_pilot: false },
  // North Western Province
  { id: "LK-61", name: "Kurunegala", zone: "Intermediate / Dry Zone", is_pilot: false },
  { id: "LK-62", name: "Puttalam", zone: "Dry Zone", is_pilot: false },
  // Sabaragamuwa Province
  { id: "LK-91", name: "Ratnapura", zone: "Wet Zone", is_pilot: false },
  { id: "LK-92", name: "Kegalle", zone: "Wet Zone", is_pilot: false },
  // Uva Province
  { id: "LK-81", name: "Badulla", zone: "Intermediate / Upcountry", is_pilot: false },
  { id: "LK-82", name: "Monaragala", zone: "Dry Zone", is_pilot: false },
  // Northern Province
  { id: "LK-41", name: "Jaffna", zone: "Dry Zone", is_pilot: false },
  { id: "LK-42", name: "Kilinochchi", zone: "Dry Zone", is_pilot: false },
  { id: "LK-43", name: "Mannar", zone: "Dry Zone", is_pilot: false },
  { id: "LK-44", name: "Vavuniya", zone: "Dry Zone", is_pilot: false },
  { id: "LK-45", name: "Mullaitivu", zone: "Dry Zone", is_pilot: false },
  // Eastern Province
  { id: "LK-51", name: "Batticaloa", zone: "Dry Zone", is_pilot: false },
  { id: "LK-52", name: "Ampara", zone: "Dry Zone", is_pilot: false },
  { id: "LK-53", name: "Trincomalee", zone: "Dry Zone", is_pilot: false },
];

// Component 1 Research Pilot Districts (Matara LK-32 & Hambantota LK-33)
export const SUPPORTED_PILOT_DISTRICT_IDS: readonly string[] = [
  "LK-32",
  "LK-33",
] as const;

export const SUPPORTED_PILOT_DISTRICTS: DistrictMetadata[] = SRI_LANKA_DISTRICTS.filter(
  (d) => d.is_pilot
);

// 10 Verified Dedicated Economic Centres (DECs) from backend STANDARD_MARKETS
export const STANDARD_MARKETS: MarketMetadata[] = [
  {
    id: "DEC_EMBILIPITIYA",
    name: "Embilipitiya Dedicated Economic Centre",
    short_name: "Embilipitiya DEC",
    region: "Southern / Sabaragamuwa Border (Primary Pilot Hub)",
    is_pilot_recommended: true,
  },
  {
    id: "DEC_DAMBULLA",
    name: "Dambulla Dedicated Economic Centre",
    short_name: "Dambulla DEC",
    region: "Central / Island Distribution Hub",
    is_pilot_recommended: true,
  },
  {
    id: "DEC_PETTAH",
    name: "Pettah Manning Market",
    short_name: "Pettah Manning Market",
    region: "Western Province Terminal Market",
    is_pilot_recommended: true,
  },
  {
    id: "DEC_MEEGODA",
    name: "Meegoda Dedicated Economic Centre",
    short_name: "Meegoda DEC",
    region: "Western Province Special Economic Centre",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_KEPPETIPOLA",
    name: "Keppetipola Dedicated Economic Centre",
    short_name: "Keppetipola DEC",
    region: "Central / Uva Province Vegetable Hub",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_THAMBUTHTHEGAMA",
    name: "Thambuththegama Dedicated Economic Centre",
    short_name: "Thambuththegama DEC",
    region: "North Central Province Economic Centre",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_KURUNEGALA",
    name: "Kurunegala Central Market",
    short_name: "Kurunegala Market",
    region: "North Western Province Central Market",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_KANDY",
    name: "Kandy Central Market",
    short_name: "Kandy Market",
    region: "Central Province Central Market",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_NUWARA_ELIYA",
    name: "Nuwara Eliya Economic Centre",
    short_name: "Nuwara Eliya DEC",
    region: "Upcountry High-Elevation Hub",
    is_pilot_recommended: false,
  },
  {
    id: "DEC_VEYANGODA",
    name: "Veyangoda Dedicated Economic Centre",
    short_name: "Veyangoda DEC",
    region: "Western / Gampaha Distribution Hub",
    is_pilot_recommended: false,
  },
];

// Component 1 Active Farmer-Facing Selling Market (Restricted to Embilipitiya DEC)
export const SUPPORTED_FRONTEND_MARKETS: MarketMetadata[] = STANDARD_MARKETS.filter(
  (m) => m.id === "DEC_EMBILIPITIYA"
);
export const DEFAULT_PILOT_MARKET_ID = "DEC_EMBILIPITIYA";

// Price Tier Options
export const PRICE_TYPES = [
  {
    id: "wholesale",
    label: "Wholesale (DEC Auction Price)",
    description: "Farmer bulk selling price at Dedicated Economic Centre auctions",
  },
  {
    id: "retail",
    label: "Retail (Consumer Market Price)",
    description: "Direct consumer selling price in local retail produce markets",
  },
] as const;

// Default Rule-Based Risk Thresholds
export const DEFAULT_RISK_THRESHOLDS = {
  min_roi_low_risk: 25.0,
  min_margin_safety_low_risk: 20.0,
};

// Default API Base URL
export const DEFAULT_API_BASE_URL = "http://localhost:8001";
