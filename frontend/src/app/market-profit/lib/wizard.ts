/**
 * Wizard state management and Step 1 validation for Component 1.
 * Supports session persistence and validation for Crop & Location selection.
 */

import {
  SUPPORTED_FRONTEND_CROPS,
  SRI_LANKA_DISTRICTS,
  STANDARD_MARKETS,
} from "./constants";

export interface Step1FormData {
  crop_id: string;
  cultivation_district_id: string;
}

export interface Step1ValidationResult {
  isValid: boolean;
  errors: {
    crop_id?: string;
    cultivation_district_id?: string;
  };
}

export const STEP1_STORAGE_KEY = "agrodecision_wizard_step1";

/**
 * Validates Step 1 selections.
 * Enforces single selection of a supported 6-crop candidate and a registered district.
 */
export function validateStep1(data: Partial<Step1FormData>): Step1ValidationResult {
  const errors: { crop_id?: string; cultivation_district_id?: string } = {};

  if (!data.crop_id || data.crop_id.trim() === "") {
    errors.crop_id = "Please select a crop to proceed with the analysis.";
  } else {
    const isSupported = SUPPORTED_FRONTEND_CROPS.some(
      (c) => c.crop_id === data.crop_id
    );
    if (!isSupported) {
      errors.crop_id =
        "The selected crop is not part of the active 6-crop pilot catalog.";
    }
  }

  if (!data.cultivation_district_id || data.cultivation_district_id.trim() === "") {
    errors.cultivation_district_id =
      "Please select a cultivation district in Sri Lanka.";
  } else {
    const isDistrictValid = SRI_LANKA_DISTRICTS.some(
      (d) => d.id === data.cultivation_district_id
    );
    if (!isDistrictValid) {
      errors.cultivation_district_id =
        "The selected district code is not recognized in Sri Lanka districts.";
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Safely reads Step 1 state from browser session storage.
 */
export function loadStep1FromStorage(): Step1FormData {
  if (typeof window === "undefined") {
    return { crop_id: "", cultivation_district_id: "" };
  }

  try {
    const stored = window.sessionStorage.getItem(STEP1_STORAGE_KEY);
    if (!stored) {
      return { crop_id: "", cultivation_district_id: "" };
    }
    const parsed = JSON.parse(stored);
    return {
      crop_id: typeof parsed.crop_id === "string" ? parsed.crop_id : "",
      cultivation_district_id:
        typeof parsed.cultivation_district_id === "string"
          ? parsed.cultivation_district_id
          : "",
    };
  } catch {
    return { crop_id: "", cultivation_district_id: "" };
  }
}

/**
 * Safely saves Step 1 state into browser session storage.
 */
export function saveStep1ToStorage(data: Step1FormData): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(STEP1_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage quota errors silently
  }
}

/**
 * Clears Step 1 state from session storage.
 */
export function clearStep1Storage(): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.removeItem(STEP1_STORAGE_KEY);
  } catch {
    // Ignore silently
  }
}

// ============================================================================
// Step 2: Harvest Details (Expected Harvest Date)
// ============================================================================

export interface Step2FormData {
  harvest_date: string; // Stored in YYYY-MM-DD local format
  land_extent_acres: string; // Numeric string preserving farmer's exact decimal input (e.g. "1.5")
  expected_yield_kg: string; // Numeric string preserving farmer's exact decimal input (e.g. "1500")
}

export interface Step2ValidationResult {
  isValid: boolean;
  errors: {
    harvest_date?: string;
    land_extent_acres?: string;
    expected_yield_kg?: string;
  };
}

export const STEP2_STORAGE_KEY = "agrodecision_wizard_step2";
export const MAX_LAND_EXTENT_ACRES = 1000;
export const MAX_EXPECTED_YIELD_KG = 1000000; // Application-level planning limit (1,000,000 kg)

/**
 * Checks if a given calendar year is a leap year.
 */
export function isLeapYear(year: number): boolean {
  if (year % 4 !== 0) return false;
  if (year % 100 !== 0) return true;
  return year % 400 === 0;
}

/**
 * Returns number of days in a given calendar month (1-12) and year.
 */
export function getDaysInMonth(year: number, month: number): number {
  if (month < 1 || month > 12) return 0;
  if (month === 2) {
    return isLeapYear(year) ? 29 : 28;
  }
  if ([4, 6, 9, 11].includes(month)) {
    return 30;
  }
  return 31;
}

/**
 * Checks if a given year, month (1-12), and day (1-31) form a valid calendar date.
 */
export function isValidCalendarDate(year: number, month: number, day: number): boolean {
  if (year < 1000 || year > 9999) return false;
  if (month < 1 || month > 12) return false;
  const maxDays = getDaysInMonth(year, month);
  return day >= 1 && day <= maxDays;
}

/**
 * Gets local today's date formatted as YYYY-MM-DD.
 * Strictly uses local calendar components to prevent UTC timezone date shifting.
 */
export function getTodayDateString(refDate: Date = new Date()): string {
  const y = refDate.getFullYear();
  const m = String(refDate.getMonth() + 1).padStart(2, "0");
  const d = String(refDate.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Validates the expected harvest date string.
 * Enforces YYYY-MM-DD format, calendar validity (including leap years), and rejects past dates.
 * Accepts today or any future calendar date.
 */
export function validateHarvestDate(
  dateStr: string | undefined | null,
  referenceDate?: Date
): { isValid: boolean; error?: string } {
  if (!dateStr || dateStr.trim() === "") {
    return {
      isValid: false,
      error: "Please select an expected harvest date.",
    };
  }

  const clean = dateStr.trim();
  const regex = /^(\d{4})-(\d{2})-(\d{2})$/;
  const match = clean.match(regex);

  if (!match) {
    return {
      isValid: false,
      error: "Please enter a valid date in YYYY-MM-DD format.",
    };
  }

  const year = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const day = parseInt(match[3], 10);

  if (!isValidCalendarDate(year, month, day)) {
    return {
      isValid: false,
      error: "Please select a valid calendar date.",
    };
  }

  const todayStr = getTodayDateString(referenceDate);
  if (clean < todayStr) {
    return {
      isValid: false,
      error: "Expected harvest date cannot be in the past.",
    };
  }

  return { isValid: true };
}

/**
 * Validates the cultivation land extent in acres.
 * Rejects missing input, non-numeric values, zero, negative numbers, NaN, and Infinity.
 * Rejects values exceeding the configurable max limit.
 * Preserves decimal precision.
 */
export function validateLandExtent(
  extentInput: string | number | undefined | null,
  maxLimit: number = MAX_LAND_EXTENT_ACRES
): { isValid: boolean; error?: string; parsedValue?: number } {
  if (extentInput === undefined || extentInput === null) {
    return {
      isValid: false,
      error: "Please enter your cultivation land extent in acres.",
    };
  }

  const str = String(extentInput).trim();
  if (str === "") {
    return {
      isValid: false,
      error: "Please enter your cultivation land extent in acres.",
    };
  }

  const num = Number(str);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return {
      isValid: false,
      error: "Cultivation land extent must be a valid numeric value.",
    };
  }

  if (num <= 0) {
    return {
      isValid: false,
      error: "Cultivation land extent must be greater than 0 acres.",
    };
  }

  if (num > maxLimit) {
    return {
      isValid: false,
      error: `Cultivation land extent exceeds the maximum planning limit of ${maxLimit} acres. Please enter a realistic land area.`,
    };
  }

  return {
    isValid: true,
    parsedValue: num,
  };
}

/**
 * Validates the expected harvest yield in kilograms.
 * Rejects missing input, non-numeric values, zero, negative numbers, NaN, and Infinity.
 * Rejects values exceeding the configurable application planning limit.
 * Preserves decimal precision.
 */
export function validateExpectedYield(
  yieldInput: string | number | undefined | null,
  maxLimit: number = MAX_EXPECTED_YIELD_KG
): { isValid: boolean; error?: string; parsedValue?: number } {
  if (yieldInput === undefined || yieldInput === null) {
    return {
      isValid: false,
      error: "Please enter your expected harvest yield in kilograms.",
    };
  }

  const str = String(yieldInput).trim();
  if (str === "") {
    return {
      isValid: false,
      error: "Please enter your expected harvest yield in kilograms.",
    };
  }

  const num = Number(str);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return {
      isValid: false,
      error: "Expected harvest yield must be a valid numeric value.",
    };
  }

  if (num <= 0) {
    return {
      isValid: false,
      error: "Expected harvest yield must be greater than 0 kg.",
    };
  }

  if (num > maxLimit) {
    return {
      isValid: false,
      error: `Expected harvest yield exceeds the maximum planning limit of ${maxLimit.toLocaleString()} kg. Please enter a realistic expected harvest amount.`,
    };
  }

  return {
    isValid: true,
    parsedValue: num,
  };
}

/**
 * Validates Step 2 form input (Expected Harvest Date, Cultivation Land Extent, and Expected Harvest Yield).
 */
export function validateStep2(
  data: Partial<Step2FormData>,
  referenceDate?: Date,
  maxLandLimit: number = MAX_LAND_EXTENT_ACRES,
  maxYieldLimit: number = MAX_EXPECTED_YIELD_KG
): Step2ValidationResult {
  const dateVal = validateHarvestDate(data.harvest_date, referenceDate);
  const extentVal = validateLandExtent(data.land_extent_acres, maxLandLimit);
  const yieldVal = validateExpectedYield(data.expected_yield_kg, maxYieldLimit);

  const errors: {
    harvest_date?: string;
    land_extent_acres?: string;
    expected_yield_kg?: string;
  } = {};

  if (!dateVal.isValid) errors.harvest_date = dateVal.error;
  if (!extentVal.isValid) errors.land_extent_acres = extentVal.error;
  if (!yieldVal.isValid) errors.expected_yield_kg = yieldVal.error;

  return {
    isValid: dateVal.isValid && extentVal.isValid && yieldVal.isValid,
    errors,
  };
}

/**
 * Safely reads Step 2 state from browser session storage.
 * Maintains full backward compatibility with older session storage records lacking expected_yield_kg.
 */
export function loadStep2FromStorage(): Step2FormData {
  if (typeof window === "undefined") {
    return { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" };
  }

  try {
    const stored = window.sessionStorage.getItem(STEP2_STORAGE_KEY);
    if (!stored) {
      return { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" };
    }
    const parsed = JSON.parse(stored);
    return {
      harvest_date: typeof parsed.harvest_date === "string" ? parsed.harvest_date : "",
      land_extent_acres:
        typeof parsed.land_extent_acres === "string"
          ? parsed.land_extent_acres
          : typeof parsed.land_extent_acres === "number"
          ? String(parsed.land_extent_acres)
          : "",
      expected_yield_kg:
        typeof parsed.expected_yield_kg === "string"
          ? parsed.expected_yield_kg
          : typeof parsed.expected_yield_kg === "number"
          ? String(parsed.expected_yield_kg)
          : "",
    };
  } catch {
    return { harvest_date: "", land_extent_acres: "", expected_yield_kg: "" };
  }
}

/**
 * Safely saves Step 2 state into browser session storage.
 */
export function saveStep2ToStorage(data: Step2FormData): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(STEP2_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage quota errors silently
  }
}

/**
 * Checks whether Step 2 has all required fields populated and valid.
 */
export function isStep2Complete(
  data: Partial<Step2FormData>,
  referenceDate?: Date
): boolean {
  return validateStep2(data, referenceDate).isValid;
}

/**
 * Safely saves Step 2 state into browser session storage ONLY if data is fully valid.
 * Protects existing valid session records from being overwritten with invalid values.
 */
export function saveValidatedStep2ToStorage(
  data: Partial<Step2FormData>,
  referenceDate?: Date
): boolean {
  const validation = validateStep2(data, referenceDate);
  if (!validation.isValid) {
    return false;
  }
  saveStep2ToStorage({
    harvest_date: data.harvest_date || "",
    land_extent_acres: data.land_extent_acres || "",
    expected_yield_kg: data.expected_yield_kg || "",
  });
  return true;
}

/**
 * Clears Step 2 state from session storage.
 */
export function clearStep2Storage(): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.removeItem(STEP2_STORAGE_KEY);
  } catch {
    // Ignore silently
  }
}

// ============================================================================
// Step 3: Selling Market & Price Type Selection
// ============================================================================

export type PriceType = "wholesale" | "retail";

export const VALID_PRICE_TYPES: readonly PriceType[] = ["wholesale", "retail"] as const;

export interface PriceTypeOption {
  value: PriceType;
  label: string;
  description: string;
  badge?: string;
}

export const PRICE_TYPE_OPTIONS: readonly PriceTypeOption[] = [
  {
    value: "wholesale",
    label: "Wholesale",
    description: "Use wholesale market prices for your analysis.",
    badge: "Bulk / Trade",
  },
  {
    value: "retail",
    label: "Retail",
    description: "Use retail market prices for your analysis.",
    badge: "Consumer",
  },
] as const;

export interface Step3FormData {
  target_market_id: string; // Primary market identifier (e.g. "DEC_EMBILIPITIYA")
  selling_market_id?: string; // Backward compatibility alias
  price_type: PriceType | ""; // "wholesale" | "retail" | ""
}

export interface Step3ValidationResult {
  isValid: boolean;
  errors: {
    target_market_id?: string;
    selling_market_id?: string;
    price_type?: string;
  };
}

export const STEP3_STORAGE_KEY = "agrodecision_wizard_step3";

/**
 * Validates the selected selling market ID against STANDARD_MARKETS.
 */
export function validateSellingMarket(
  marketId: string | undefined | null
): { isValid: boolean; error?: string } {
  if (!marketId || marketId.trim() === "") {
    return {
      isValid: false,
      error: "Please select a target selling market.",
    };
  }

  const clean = marketId.trim();
  const exists = STANDARD_MARKETS.some((m) => m.id === clean);

  if (!exists) {
    return {
      isValid: false,
      error: "The selected market is not recognized in verified Dedicated Economic Centres.",
    };
  }

  return { isValid: true };
}

/**
 * Validates the price type ("wholesale" or "retail").
 * Rejects empty, whitespace, null/undefined, and unrecognized strings.
 */
export function validatePriceType(
  priceType: string | undefined | null
): { isValid: boolean; error?: string } {
  if (!priceType || priceType.trim() === "") {
    return {
      isValid: false,
      error: "Please select a price type (Wholesale or Retail).",
    };
  }

  const clean = priceType.trim().toLowerCase();
  if (clean !== "wholesale" && clean !== "retail") {
    return {
      isValid: false,
      error: "Invalid price type. Please select either Wholesale or Retail.",
    };
  }

  return { isValid: true };
}

/**
 * Validates Step 3 form input (Selling Market Selection + Price Type Selection).
 * Requires both a valid recognized selling market and a valid price type.
 */
export function validateStep3(data: Partial<Step3FormData>): Step3ValidationResult {
  const marketId = data.target_market_id || data.selling_market_id;
  const marketVal = validateSellingMarket(marketId);
  const priceTypeVal = validatePriceType(data.price_type);

  const errors: {
    target_market_id?: string;
    selling_market_id?: string;
    price_type?: string;
  } = {};

  if (!marketVal.isValid) {
    errors.target_market_id = marketVal.error;
    errors.selling_market_id = marketVal.error;
  }

  if (!priceTypeVal.isValid) {
    errors.price_type = priceTypeVal.error;
  }

  return {
    isValid: marketVal.isValid && priceTypeVal.isValid,
    errors,
  };
}

/**
 * Checks whether Step 3 has all required fields populated and valid.
 */
export function isStep3Complete(data: Partial<Step3FormData>): boolean {
  return validateStep3(data).isValid;
}

/**
 * Result structure when checking previous wizard steps integrity.
 */
export interface PreviousStepsIntegrityResult {
  isValid: boolean;
  earliestIncompleteStep?: 1 | 2;
  redirectTarget?: string;
  errorMessage?: string;
}

/**
 * Evaluates earlier wizard steps integrity before allowing Step 3 completion.
 * Returns the earliest incomplete step and its redirection route.
 */
export function checkPreviousStepsForStep3(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  referenceDate?: Date
): PreviousStepsIntegrityResult {
  const v1 = validateStep1(step1);
  if (!v1.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 1,
      redirectTarget: "/market-profit/new-analysis",
      errorMessage:
        "Step 1 (Crop & Location) is incomplete. Please select your crop and cultivation district first.",
    };
  }

  const v2 = validateStep2(step2, referenceDate);
  if (!v2.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 2,
      redirectTarget: "/market-profit/new-analysis/harvest-details",
      errorMessage:
        "Step 2 (Harvest Details) is incomplete. Please provide your harvest timing, land extent, and expected yield first.",
    };
  }

  return {
    isValid: true,
  };
}

/**
 * Checks overall wizard readiness across all 3 steps before transitioning to Step 4 (Cultivation Costs).
 */
export function isWizardReadyForStep4(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  step3: Partial<Step3FormData>,
  referenceDate?: Date
): boolean {
  return checkPreviousStepsForStep4(step1, step2, step3, referenceDate).isValid;
}

/**
 * Result structure when checking previous wizard steps integrity before Step 4.
 */
export interface PreviousStepsForStep4Result {
  isValid: boolean;
  earliestIncompleteStep?: 1 | 2 | 3;
  redirectTarget?: string;
  errorMessage?: string;
}

/**
 * Evaluates earlier wizard steps integrity (Steps 1, 2, and 3) before allowing Step 4 progression.
 * Returns the earliest incomplete step and its redirection route.
 */
export function checkPreviousStepsForStep4(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  step3: Partial<Step3FormData>,
  referenceDate?: Date
): PreviousStepsForStep4Result {
  const v1 = validateStep1(step1);
  if (!v1.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 1,
      redirectTarget: "/market-profit/new-analysis",
      errorMessage:
        "Step 1 (Crop & Location) is incomplete. Please select your crop and cultivation district first.",
    };
  }

  const v2 = validateStep2(step2, referenceDate);
  if (!v2.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 2,
      redirectTarget: "/market-profit/new-analysis/harvest-details",
      errorMessage:
        "Step 2 (Harvest Details) is incomplete. Please provide your harvest timing, land extent, and expected yield first.",
    };
  }

  const v3 = validateStep3(step3);
  if (!v3.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 3,
      redirectTarget: "/market-profit/new-analysis/selling-market",
      errorMessage:
        "Step 3 (Selling Market) is incomplete. Please choose your target market and price type first.",
    };
  }

  return {
    isValid: true,
  };
}

/**
 * Safely reads Step 3 state from browser session storage.
 * Maintains backward compatibility for existing records containing only target_market_id or selling_market_id.
 */
export function loadStep3FromStorage(): Step3FormData {
  if (typeof window === "undefined") {
    return { target_market_id: "", selling_market_id: "", price_type: "" };
  }

  try {
    const stored = window.sessionStorage.getItem(STEP3_STORAGE_KEY);
    if (!stored) {
      return { target_market_id: "", selling_market_id: "", price_type: "" };
    }
    const parsed = JSON.parse(stored);

    // Support both target_market_id and legacy selling_market_id
    const marketId =
      typeof parsed.target_market_id === "string"
        ? parsed.target_market_id
        : typeof parsed.selling_market_id === "string"
        ? parsed.selling_market_id
        : "";

    // Normalize price_type if present and valid, otherwise empty string
    const rawPriceType =
      typeof parsed.price_type === "string" ? parsed.price_type.trim().toLowerCase() : "";
    const priceType: PriceType | "" =
      rawPriceType === "wholesale" || rawPriceType === "retail" ? rawPriceType : "";

    return {
      target_market_id: marketId,
      selling_market_id: marketId,
      price_type: priceType,
    };
  } catch {
    return { target_market_id: "", selling_market_id: "", price_type: "" };
  }
}

/**
 * Safely saves Step 3 state into browser session storage.
 * Ensures both target_market_id and selling_market_id are populated for backward compatibility.
 */
export function saveStep3ToStorage(data: Step3FormData): void {
  if (typeof window === "undefined") return;

  try {
    const marketId = data.target_market_id || data.selling_market_id || "";
    const cleanMarketId = typeof marketId === "string" ? marketId.trim() : "";
    const rawPriceType =
      typeof data.price_type === "string" ? data.price_type.trim().toLowerCase() : "";
    const normalizedPriceType: PriceType | "" =
      rawPriceType === "wholesale" || rawPriceType === "retail" ? rawPriceType : "";

    const payload = {
      target_market_id: cleanMarketId,
      selling_market_id: cleanMarketId,
      price_type: normalizedPriceType,
    };
    window.sessionStorage.setItem(STEP3_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage quota errors silently
  }
}

/**
 * Safely saves Step 3 state into browser session storage ONLY if data is fully valid.
 * Protects existing valid session records from being overwritten with invalid values.
 * Normalizes price_type to exact backend-compatible lowercase value before saving.
 */
export function saveValidatedStep3ToStorage(data: Partial<Step3FormData>): boolean {
  const validation = validateStep3(data);
  if (!validation.isValid) {
    return false;
  }
  const marketId = data.target_market_id || data.selling_market_id || "";
  const cleanMarketId = typeof marketId === "string" ? marketId.trim() : "";
  const rawPriceType =
    typeof data.price_type === "string" ? data.price_type.trim().toLowerCase() : "";
  const normalizedPriceType = rawPriceType as PriceType;

  saveStep3ToStorage({
    target_market_id: cleanMarketId,
    selling_market_id: cleanMarketId,
    price_type: normalizedPriceType,
  });
  return true;
}

/**
 * Clears Step 3 state from session storage.
 */
export function clearStep3Storage(): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.removeItem(STEP3_STORAGE_KEY);
  } catch {
    // Ignore silently
  }
}

// ============================================================================
// Step 4: Cultivation Costs (Quick & Detailed Cultivation Budget)
// ============================================================================

export type BudgetMode = "quick" | "detailed";

export interface DetailedExpensesData {
  seeds: string;
  fertilizer: string;
  pesticides: string;
  labour: string;
  irrigation: string;
  harvesting: string;
  packaging: string;
  transportation: string;
  market_commission: string;
  other_expenses: string;
}

export type DetailedExpenseKey = keyof DetailedExpensesData;

export interface DetailedExpenseCategoryItem {
  key: DetailedExpenseKey;
  label: string;
  helperText: string;
  placeholder: string;
}

export const DETAILED_EXPENSE_CATEGORIES: DetailedExpenseCategoryItem[] = [
  {
    key: "seeds",
    label: "Seeds / Planting Material",
    helperText: "Certified seeds, seedlings, or nursery preparation",
    placeholder: "15000",
  },
  {
    key: "fertilizer",
    label: "Fertilizer & Soil Nutrition",
    helperText: "Basal, top-dressing fertilizers, compost, or manure",
    placeholder: "25000",
  },
  {
    key: "pesticides",
    label: "Pesticides & Crop Protection",
    helperText: "Insecticides, fungicides, weedicides, or crop protectors",
    placeholder: "12000",
  },
  {
    key: "labour",
    label: "Labour & Field Operations",
    helperText: "Land preparation, ploughing, planting, weeding, and tending",
    placeholder: "45000",
  },
  {
    key: "irrigation",
    label: "Irrigation & Water Management",
    helperText: "Pumping fuel, electricity, water bowsers, or canal fees",
    placeholder: "10000",
  },
  {
    key: "harvesting",
    label: "Harvesting Labour & Machinery",
    helperText: "Labour or machinery specifically for crop picking and harvesting",
    placeholder: "20000",
  },
  {
    key: "packaging",
    label: "Packaging & Bagging",
    helperText: "Gunny sacks, plastic crates, netting, or cardboard boxes",
    placeholder: "8000",
  },
  {
    key: "transportation",
    label: "Transportation to Market",
    helperText: "Lorry, tractor, or three-wheeler hire to the economic centre",
    placeholder: "15000",
  },
  {
    key: "market_commission",
    label: "Market Commission & DEC Fees",
    helperText: "Dedicated Economic Centre floor fees, unloaders, or trade fees",
    placeholder: "5000",
  },
  {
    key: "other_expenses",
    label: "Other Miscellaneous Expenses",
    helperText: "Minor tools, equipment maintenance, and farming contingencies",
    placeholder: "5000",
  },
];

export function createDefaultDetailedExpenses(): DetailedExpensesData {
  return {
    seeds: "",
    fertilizer: "",
    pesticides: "",
    labour: "",
    irrigation: "",
    harvesting: "",
    packaging: "",
    transportation: "",
    market_commission: "",
    other_expenses: "",
  };
}

/**
 * Safely sums an array of decimal strings without floating-point rounding errors.
 * Preserves decimal accuracy by scaling numbers to exact integer units.
 */
export function safeSumDecimalStrings(strings: string[]): { sumNumber: number; sumString: string } {
  const validStrings = strings
    .map((s) => s.trim())
    .filter((s) => s !== "");

  if (validStrings.length === 0) {
    return { sumNumber: 0, sumString: "0" };
  }

  let maxDecimals = 0;
  for (const s of validStrings) {
    const dotIndex = s.indexOf(".");
    if (dotIndex !== -1) {
      const decLen = s.length - dotIndex - 1;
      if (decLen > maxDecimals) {
        maxDecimals = decLen;
      }
    }
  }

  let totalScaled = BigInt(0);
  for (const s of validStrings) {
    const num = Number(s);
    if (!Number.isFinite(num) || Number.isNaN(num)) {
      continue;
    }
    const [intPart, fracPart = ""] = s.split(".");
    const paddedFrac = fracPart.padEnd(maxDecimals, "0").slice(0, maxDecimals);
    const combined = `${intPart.replace(/^-/, "")}${paddedFrac}`;
    const val = BigInt(combined === "" ? "0" : combined);
    if (s.startsWith("-")) {
      totalScaled -= val;
    } else {
      totalScaled += val;
    }
  }

  if (maxDecimals === 0) {
    const str = totalScaled.toString();
    return { sumNumber: Number(str), sumString: str };
  }

  const isNeg = totalScaled < BigInt(0);
  const absVal = isNeg ? -totalScaled : totalScaled;
  const absStr = absVal.toString().padStart(maxDecimals + 1, "0");
  const intStr = absStr.slice(0, -maxDecimals) || "0";
  let fracStr = absStr.slice(-maxDecimals);

  fracStr = fracStr.replace(/0+$/, "");
  const resultStr = (isNeg ? "-" : "") + (fracStr ? `${intStr}.${fracStr}` : intStr);
  return { sumNumber: Number(resultStr), sumString: resultStr };
}

/**
 * Calculates the total cultivation cost across all detailed expense categories.
 * Treats empty optional expense fields as zero for total calculation.
 * Preserves decimal precision and prevents double counting.
 */
export function calculateDetailedCultivationTotal(
  expenses: Partial<DetailedExpensesData>
): {
  totalCultivationCost: number;
  totalString: string;
  isZeroCost: boolean;
  hasAnyEnteredValue: boolean;
  nonZeroCount: number;
} {
  const values: string[] = [];
  let nonZeroCount = 0;
  let hasAnyEnteredValue = false;

  for (const cat of DETAILED_EXPENSE_CATEGORIES) {
    const raw = expenses[cat.key];
    if (raw !== undefined && raw !== null && String(raw).trim() !== "") {
      hasAnyEnteredValue = true;
      const str = String(raw).trim();
      values.push(str);
      const num = Number(str);
      if (Number.isFinite(num) && num > 0) {
        nonZeroCount++;
      }
    }
  }

  const { sumNumber, sumString } = safeSumDecimalStrings(values);
  const isZero = sumNumber === 0;

  return {
    totalCultivationCost: sumNumber,
    totalString: sumString,
    isZeroCost: isZero,
    hasAnyEnteredValue,
    nonZeroCount,
  };
}

/**
 * Validates a single detailed expense category field.
 * Empty or whitespace is treated as valid (optional, treated as 0 in total).
 * Non-empty must be numeric and non-negative.
 */
export function validateDetailedExpenseField(
  categoryKey: DetailedExpenseKey,
  value: string | number | undefined | null
): {
  isValid: boolean;
  error?: string;
  parsedValue: number;
  isEmpty: boolean;
} {
  const catMeta = DETAILED_EXPENSE_CATEGORIES.find((c) => c.key === categoryKey);
  const label = catMeta ? catMeta.label : categoryKey;

  if (value === undefined || value === null) {
    return { isValid: true, parsedValue: 0, isEmpty: true };
  }

  const str = String(value).trim();
  if (str === "") {
    return { isValid: true, parsedValue: 0, isEmpty: true };
  }

  const num = Number(str);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return {
      isValid: false,
      error: `${label} must be a valid numeric amount in LKR.`,
      parsedValue: 0,
      isEmpty: false,
    };
  }

  if (num < 0) {
    return {
      isValid: false,
      error: `${label} cannot be negative. Please enter 0 or a positive amount.`,
      parsedValue: num,
      isEmpty: false,
    };
  }

  return {
    isValid: true,
    parsedValue: num,
    isEmpty: false,
  };
}

export interface DetailedExpensesValidationResult {
  isValid: boolean;
  errors: Partial<Record<DetailedExpenseKey, string>>;
  totalCultivationCost: number;
  totalString: string;
  isZeroCost: boolean;
  warning?: string;
}

/**
 * Validates all 10 detailed expense categories.
 * Collects field-specific errors without silently accepting malformed values.
 */
export function validateDetailedExpenses(
  expenses: Partial<DetailedExpensesData>
): DetailedExpensesValidationResult {
  const errors: Partial<Record<DetailedExpenseKey, string>> = {};

  for (const cat of DETAILED_EXPENSE_CATEGORIES) {
    const raw = expenses[cat.key];
    const fieldVal = validateDetailedExpenseField(cat.key, raw);
    if (!fieldVal.isValid && fieldVal.error) {
      errors[cat.key] = fieldVal.error;
    }
  }

  const calc = calculateDetailedCultivationTotal(expenses);
  const isValid = Object.keys(errors).length === 0;

  const warning =
    isValid && calc.isZeroCost
      ? "Cultivation cost is set to Rs. 0. Profit percentage and risk evaluation may be unavailable when cost is zero."
      : undefined;

  return {
    isValid,
    errors,
    totalCultivationCost: calc.totalCultivationCost,
    totalString: calc.totalString,
    isZeroCost: calc.isZeroCost,
    warning,
  };
}

export interface Step4FormData {
  budget_mode: BudgetMode;
  quick_total_cultivation_cost_lkr: string; // Numeric string preserving farmer's exact decimal input (e.g. "150000")
  detailed_expenses: DetailedExpensesData;
  effective_total_cultivation_cost_lkr: string;
  total_cultivation_cost_lkr: string; // Backward compatibility alias
  manual_selling_price_lkr_per_kg?: string; // Optional obsolete field for backward compatibility with older session records
}

export interface Step4ValidationResult {
  isValid: boolean;
  budget_mode: BudgetMode;
  errors: {
    total_cultivation_cost_lkr?: string;
    quick_total_cultivation_cost_lkr?: string;
    detailed_expenses?: Partial<Record<DetailedExpenseKey, string>>;
  };
  warnings?: {
    total_cultivation_cost_lkr?: string;
  };
  parsedCost?: number;
  effectiveTotalString: string;
  isZeroCost?: boolean;
}

export const STEP4_STORAGE_KEY = "agrodecision_wizard_step4";

/**
 * Validates the total expected cultivation cost in Sri Lankan Rupees (LKR).
 * Requirements:
 * 1. Numeric input supporting positive decimal values.
 * 2. Required field for Quick Budget mode.
 * 3. Rejects missing, negative, non-numeric, NaN, and Infinity values.
 * 4. Allows zero as a valid numeric input, but displays a clear warning that
 *    profit percentage and risk evaluation may be unavailable when cost is zero.
 * 5. Preserves the farmer's decimal precision without silent rounding.
 */
export function validateCultivationCost(
  costInput: string | number | undefined | null
): {
  isValid: boolean;
  error?: string;
  warning?: string;
  parsedValue?: number;
  isZeroCost?: boolean;
} {
  if (costInput === undefined || costInput === null) {
    return {
      isValid: false,
      error: "Please enter your total expected cultivation cost in LKR.",
    };
  }

  const str = String(costInput).trim();
  if (str === "") {
    return {
      isValid: false,
      error: "Please enter your total expected cultivation cost in LKR.",
    };
  }

  const num = Number(str);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return {
      isValid: false,
      error: "Cultivation cost must be a valid numeric amount.",
    };
  }

  if (num < 0) {
    return {
      isValid: false,
      error: "Cultivation cost cannot be negative. Please enter 0 or a positive amount in LKR.",
    };
  }

  if (num === 0) {
    return {
      isValid: true,
      parsedValue: 0,
      isZeroCost: true,
      warning:
        "Cultivation cost is set to Rs. 0. Profit percentage and risk evaluation may be unavailable when cost is zero.",
    };
  }

  return {
    isValid: true,
    parsedValue: num,
    isZeroCost: false,
  };
}

/**
 * Safely multiplies two decimal strings without floating-point rounding errors.
 * Uses integer scaling with BigInt.
 */
export function safeMultiplyDecimalStrings(
  a: string,
  b: string
): { productNumber: number; productString: string } {
  const strA = a.trim();
  const strB = b.trim();

  if (strA === "" || strB === "") {
    return { productNumber: 0, productString: "0" };
  }

  const numA = Number(strA);
  const numB = Number(strB);
  if (!Number.isFinite(numA) || Number.isNaN(numA) || !Number.isFinite(numB) || Number.isNaN(numB)) {
    return { productNumber: 0, productString: "0" };
  }

  const isNeg = (strA.startsWith("-") && !strB.startsWith("-")) || (!strA.startsWith("-") && strB.startsWith("-"));

  const cleanA = strA.replace(/^-/, "");
  const cleanB = strB.replace(/^-/, "");

  const [intA = "0", fracA = ""] = cleanA.split(".");
  const [intB = "0", fracB = ""] = cleanB.split(".");

  const decA = fracA.length;
  const decB = fracB.length;
  const totalDecimals = decA + decB;

  const combinedA = `${intA}${fracA}` || "0";
  const combinedB = `${intB}${fracB}` || "0";
  const bigA = BigInt(combinedA);
  const bigB = BigInt(combinedB);
  const bigProd = bigA * bigB;

  if (bigProd === BigInt(0)) {
    return { productNumber: 0, productString: "0" };
  }

  if (totalDecimals === 0) {
    const s = (isNeg ? "-" : "") + bigProd.toString();
    return { productNumber: Number(s), productString: s };
  }

  const rawStr = bigProd.toString().padStart(totalDecimals + 1, "0");
  const intPart = rawStr.slice(0, -totalDecimals) || "0";
  let fracPart = rawStr.slice(-totalDecimals).replace(/0+$/, "");

  const finalStr = (isNeg ? "-" : "") + (fracPart ? `${intPart}.${fracPart}` : intPart);
  return { productNumber: Number(finalStr), productString: finalStr };
}

/**
 * Calculates predicted revenue from future AI-predicted selling price (LKR/kg) and expected yield (kg).
 * Predicted Revenue = AI Predicted Price × Expected Yield
 * Only computed when real backend prediction data is available from the ML model.
 * Returns isAvailable: false when predictions are unavailable (no invented or mock values).
 */
export function calculatePredictedRevenue(
  predictedPriceLkrPerKg: number | string | undefined | null,
  expectedYieldKg: number | string | undefined | null
): {
  isAvailable: boolean;
  revenueNumber: number;
  revenueString: string;
} {
  if (
    predictedPriceLkrPerKg === undefined ||
    predictedPriceLkrPerKg === null ||
    expectedYieldKg === undefined ||
    expectedYieldKg === null
  ) {
    return { isAvailable: false, revenueNumber: 0, revenueString: "0" };
  }

  const pNum = Number(predictedPriceLkrPerKg);
  const yNum = Number(expectedYieldKg);

  if (!Number.isFinite(pNum) || Number.isNaN(pNum) || pNum <= 0 || !Number.isFinite(yNum) || Number.isNaN(yNum) || yNum <= 0) {
    return { isAvailable: false, revenueNumber: 0, revenueString: "0" };
  }

  const { productNumber, productString } = safeMultiplyDecimalStrings(String(pNum), String(yNum));
  return {
    isAvailable: true,
    revenueNumber: productNumber,
    revenueString: productString,
  };
}

/**
 * Calculates predicted profit from predicted revenue and total cultivation cost.
 * Predicted Profit = Predicted Revenue - Total Cultivation Cost
 * Only computed when real backend prediction data is available from the ML model.
 * Returns isAvailable: false when predictions are unavailable.
 */
export function calculatePredictedProfit(
  predictedRevenueLkr: number | undefined | null,
  totalCultivationCostLkr: number | undefined | null
): {
  isAvailable: boolean;
  profitNumber: number;
  profitString: string;
} {
  if (
    predictedRevenueLkr === undefined ||
    predictedRevenueLkr === null ||
    totalCultivationCostLkr === undefined ||
    totalCultivationCostLkr === null
  ) {
    return { isAvailable: false, profitNumber: 0, profitString: "0" };
  }

  if (!Number.isFinite(predictedRevenueLkr) || !Number.isFinite(totalCultivationCostLkr)) {
    return { isAvailable: false, profitNumber: 0, profitString: "0" };
  }

  const profit = predictedRevenueLkr - totalCultivationCostLkr;
  return {
    isAvailable: true,
    profitNumber: profit,
    profitString: String(profit),
  };
}

/**
 * Validates Step 4 form input based on the active budget mode.
 * - In Quick Budget mode: validates total_cultivation_cost_lkr / quick_total_cultivation_cost_lkr.
 * - In Detailed Budget mode: validates all 10 detailed expense categories and calculates total automatically.
 * Cultivation cost must be zero or positive. No manual selling price is required.
 */
export function validateStep4(data: Partial<Step4FormData>): Step4ValidationResult {
  const mode: BudgetMode = data.budget_mode === "detailed" ? "detailed" : "quick";

  if (mode === "detailed") {
    const detailed = data.detailed_expenses || createDefaultDetailedExpenses();
    const detailedVal = validateDetailedExpenses(detailed);

    const errors: Step4ValidationResult["errors"] = {};
    if (!detailedVal.isValid) {
      errors.detailed_expenses = detailedVal.errors;
      errors.total_cultivation_cost_lkr = "Please correct the invalid expense entries.";
    }

    const warnings: { total_cultivation_cost_lkr?: string } = {};
    if (detailedVal.warning) {
      warnings.total_cultivation_cost_lkr = detailedVal.warning;
    }

    return {
      isValid: detailedVal.isValid,
      budget_mode: "detailed",
      errors,
      warnings: Object.keys(warnings).length > 0 ? warnings : undefined,
      parsedCost: detailedVal.totalCultivationCost,
      effectiveTotalString: detailedVal.totalString,
      isZeroCost: detailedVal.isZeroCost,
    };
  } else {
    // Quick Budget mode (default)
    const costInput = data.quick_total_cultivation_cost_lkr ?? data.total_cultivation_cost_lkr;
    const costVal = validateCultivationCost(costInput);

    const errors: Step4ValidationResult["errors"] = {};
    const warnings: { total_cultivation_cost_lkr?: string } = {};

    if (!costVal.isValid) {
      errors.total_cultivation_cost_lkr = costVal.error;
      errors.quick_total_cultivation_cost_lkr = costVal.error;
    } else if (costVal.warning) {
      warnings.total_cultivation_cost_lkr = costVal.warning;
    }

    return {
      isValid: costVal.isValid,
      budget_mode: "quick",
      errors,
      warnings: Object.keys(warnings).length > 0 ? warnings : undefined,
      parsedCost: costVal.parsedValue,
      effectiveTotalString: costVal.isValid && costInput !== undefined && costInput !== null ? String(costInput).trim() : "0",
      isZeroCost: costVal.isZeroCost,
    };
  }
}

/**
 * Checks whether Step 4 has all required fields populated and valid.
 * Cultivation cost must be zero or positive. No manual selling price is required.
 */
export function isStep4Complete(data: Partial<Step4FormData>): boolean {
  return validateStep4(data).isValid;
}

/**
 * Safely reads Step 4 state from browser session storage.
 * Maintains backward compatibility with earlier Step 4 records.
 * Safely ignores obsolete manual selling price field.
 */
export function loadStep4FromStorage(): Step4FormData {
  if (typeof window === "undefined") {
    return {
      budget_mode: "quick",
      quick_total_cultivation_cost_lkr: "",
      detailed_expenses: createDefaultDetailedExpenses(),
      effective_total_cultivation_cost_lkr: "",
      total_cultivation_cost_lkr: "",
    };
  }

  try {
    const stored = window.sessionStorage.getItem(STEP4_STORAGE_KEY);
    if (!stored) {
      return {
        budget_mode: "quick",
        quick_total_cultivation_cost_lkr: "",
        detailed_expenses: createDefaultDetailedExpenses(),
        effective_total_cultivation_cost_lkr: "",
        total_cultivation_cost_lkr: "",
      };
    }
    const parsed = JSON.parse(stored);

    const budgetMode: BudgetMode =
      parsed.budget_mode === "detailed" ? "detailed" : "quick";

    const quickCost =
      typeof parsed.quick_total_cultivation_cost_lkr === "string"
        ? parsed.quick_total_cultivation_cost_lkr
        : typeof parsed.total_cultivation_cost_lkr === "string"
        ? parsed.total_cultivation_cost_lkr
        : typeof parsed.total_cultivation_cost_lkr === "number"
        ? String(parsed.total_cultivation_cost_lkr)
        : "";

    const storedDetailed =
      typeof parsed.detailed_expenses === "object" && parsed.detailed_expenses !== null
        ? parsed.detailed_expenses
        : {};

    const detailedExpenses: DetailedExpensesData = {
      seeds: typeof storedDetailed.seeds === "string" ? storedDetailed.seeds : "",
      fertilizer: typeof storedDetailed.fertilizer === "string" ? storedDetailed.fertilizer : "",
      pesticides: typeof storedDetailed.pesticides === "string" ? storedDetailed.pesticides : "",
      labour: typeof storedDetailed.labour === "string" ? storedDetailed.labour : "",
      irrigation: typeof storedDetailed.irrigation === "string" ? storedDetailed.irrigation : "",
      harvesting: typeof storedDetailed.harvesting === "string" ? storedDetailed.harvesting : "",
      packaging: typeof storedDetailed.packaging === "string" ? storedDetailed.packaging : "",
      transportation: typeof storedDetailed.transportation === "string" ? storedDetailed.transportation : "",
      market_commission: typeof storedDetailed.market_commission === "string" ? storedDetailed.market_commission : "",
      other_expenses: typeof storedDetailed.other_expenses === "string" ? storedDetailed.other_expenses : "",
    };

    const detailedSum = calculateDetailedCultivationTotal(detailedExpenses).totalString;
    const effectiveTotal = budgetMode === "detailed" ? detailedSum : quickCost;

    return {
      budget_mode: budgetMode,
      quick_total_cultivation_cost_lkr: quickCost,
      detailed_expenses: detailedExpenses,
      effective_total_cultivation_cost_lkr: effectiveTotal,
      total_cultivation_cost_lkr: effectiveTotal,
      manual_selling_price_lkr_per_kg:
        typeof parsed.manual_selling_price_lkr_per_kg === "string"
          ? parsed.manual_selling_price_lkr_per_kg
          : undefined,
    };
  } catch {
    return {
      budget_mode: "quick",
      quick_total_cultivation_cost_lkr: "",
      detailed_expenses: createDefaultDetailedExpenses(),
      effective_total_cultivation_cost_lkr: "",
      total_cultivation_cost_lkr: "",
    };
  }
}

/**
 * Safely saves Step 4 state into browser session storage.
 * Preserves Quick/Detailed Budget values independently.
 */
export function saveStep4ToStorage(data: Partial<Step4FormData>): void {
  if (typeof window === "undefined") return;

  try {
    const budgetMode: BudgetMode = data.budget_mode === "detailed" ? "detailed" : "quick";
    const quickCost = String(data.quick_total_cultivation_cost_lkr ?? data.total_cultivation_cost_lkr ?? "").trim();
    const detailed = data.detailed_expenses || createDefaultDetailedExpenses();

    const detailedExpenses: DetailedExpensesData = {
      seeds: String(detailed.seeds ?? "").trim(),
      fertilizer: String(detailed.fertilizer ?? "").trim(),
      pesticides: String(detailed.pesticides ?? "").trim(),
      labour: String(detailed.labour ?? "").trim(),
      irrigation: String(detailed.irrigation ?? "").trim(),
      harvesting: String(detailed.harvesting ?? "").trim(),
      packaging: String(detailed.packaging ?? "").trim(),
      transportation: String(detailed.transportation ?? "").trim(),
      market_commission: String(detailed.market_commission ?? "").trim(),
      other_expenses: String(detailed.other_expenses ?? "").trim(),
    };

    const detailedSum = calculateDetailedCultivationTotal(detailedExpenses).totalString;
    const effectiveTotal = budgetMode === "detailed" ? detailedSum : quickCost;

    const payload = {
      budget_mode: budgetMode,
      quick_total_cultivation_cost_lkr: quickCost,
      detailed_expenses: detailedExpenses,
      effective_total_cultivation_cost_lkr: effectiveTotal,
      total_cultivation_cost_lkr: effectiveTotal,
    };

    window.sessionStorage.setItem(STEP4_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage quota errors silently
  }
}

/**
 * Safely saves Step 4 state into browser session storage ONLY if data is fully valid.
 * Protects existing valid session records from being overwritten with invalid values.
 */
export function saveValidatedStep4ToStorage(data: Partial<Step4FormData>): boolean {
  const validation = validateStep4(data);
  if (!validation.isValid) {
    return false;
  }
  saveStep4ToStorage(data);
  return true;
}

/**
 * Clears Step 4 state from session storage.
 */
export function clearStep4Storage(): void {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.removeItem(STEP4_STORAGE_KEY);
  } catch {
    // Ignore silently
  }
}

// ============================================================================
// Wizard Completion & Analysis Results Handoff (Commit 25)
// ============================================================================

export interface ValidatedAnalysisSnapshot {
  crop_id: string;
  cultivation_district_id: string;
  harvest_date: string;
  forecast_target_date: string; // strictly aligns with backend forecast request contracts
  expected_yield_kg: number;
  expected_yield_kg_string: string;
  target_market_id: string;
  price_type: "wholesale" | "retail";
  total_cultivation_cost: number;
  total_cultivation_cost_string: string;
  metadata: {
    land_extent_acres: number;
    land_extent_acres_string: string;
    budget_mode: BudgetMode;
    detailed_expenses?: DetailedExpensesData;
    is_zero_cultivation_cost: boolean;
    zero_cost_warning?: string;
    created_at: string;
    version: string;
  };
}

export interface FullWizardValidationResult {
  isValid: boolean;
  earliestIncompleteStep?: 1 | 2 | 3 | 4;
  redirectTarget?: string;
  errorMessage?: string;
  step1Validation?: Step1ValidationResult;
  step2Validation?: Step2ValidationResult;
  step3Validation?: Step3ValidationResult;
  step4Validation?: Step4ValidationResult;
  snapshot?: ValidatedAnalysisSnapshot;
}

export const ANALYSIS_SNAPSHOT_STORAGE_KEY = "agrodecision_analysis_snapshot";

/**
 * Validates all four steps of the New Analysis wizard composite.
 * Enforces strict integrity across all farmer inputs:
 * - Step 1: Supported crop & registered district
 * - Step 2: Future harvest date, positive land extent, positive yield
 * - Step 3: Standard Dedicated Economic Centre & price type (wholesale/retail)
 * - Step 4: Cultivation budget >= 0 (zero cost accepted with advisory warning). No manual selling price required.
 *
 * If any step is invalid, identifies the earliest incomplete step and appropriate redirect target.
 * If all steps are valid, constructs the typed ValidatedAnalysisSnapshot ready for handoff.
 */
export function validateFullWizard(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  step3: Partial<Step3FormData>,
  step4: Partial<Step4FormData>,
  referenceDate?: Date
): FullWizardValidationResult {
  // 1. Step 1 Validation
  const s1Val = validateStep1(step1);
  if (!s1Val.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 1,
      redirectTarget: "/market-profit/new-analysis",
      errorMessage:
        s1Val.errors.crop_id ||
        s1Val.errors.cultivation_district_id ||
        "Step 1 (Crop & Location) is incomplete. Please select a supported crop and district.",
      step1Validation: s1Val,
    };
  }

  // 2. Step 2 Validation
  const s2Val = validateStep2(step2, referenceDate);
  if (!s2Val.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 2,
      redirectTarget: "/market-profit/new-analysis/harvest-details",
      errorMessage:
        s2Val.errors.harvest_date ||
        s2Val.errors.land_extent_acres ||
        s2Val.errors.expected_yield_kg ||
        "Step 2 (Harvest Details) is incomplete. Please provide a valid harvest date, land extent, and expected yield.",
      step1Validation: s1Val,
      step2Validation: s2Val,
    };
  }

  // 3. Step 3 Validation
  const s3Val = validateStep3(step3);
  if (!s3Val.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 3,
      redirectTarget: "/market-profit/new-analysis/selling-market",
      errorMessage:
        s3Val.errors.target_market_id ||
        s3Val.errors.price_type ||
        "Step 3 (Selling Market) is incomplete. Please select a target selling market and price type.",
      step1Validation: s1Val,
      step2Validation: s2Val,
      step3Validation: s3Val,
    };
  }

  // 4. Step 4 Validation
  const s4Val = validateStep4(step4);
  if (!s4Val.isValid) {
    return {
      isValid: false,
      earliestIncompleteStep: 4,
      redirectTarget: "/market-profit/new-analysis/cultivation-costs",
      errorMessage:
        s4Val.errors.total_cultivation_cost_lkr ||
        s4Val.errors.quick_total_cultivation_cost_lkr ||
        "Step 4 (Cultivation Costs) is incomplete. Please provide your planned cultivation budget.",
      step1Validation: s1Val,
      step2Validation: s2Val,
      step3Validation: s3Val,
      step4Validation: s4Val,
    };
  }

  // 5. Construct Validated Analysis Snapshot
  const cleanCropId = String(step1.crop_id).trim();
  const cleanDistrictId = String(step1.cultivation_district_id).trim();
  const cleanHarvestDate = String(step2.harvest_date).trim();
  const cleanYieldStr = String(step2.expected_yield_kg).trim();
  const parsedYield = Number(cleanYieldStr);
  const cleanMarketId = String(step3.target_market_id || step3.selling_market_id).trim();
  const rawPriceType = String(step3.price_type).trim().toLowerCase();
  const cleanPriceType: "wholesale" | "retail" = rawPriceType === "retail" ? "retail" : "wholesale";
  const parsedCost = s4Val.parsedCost ?? 0;
  const cleanCostStr = s4Val.effectiveTotalString || String(parsedCost);
  const cleanAcresStr = String(step2.land_extent_acres).trim();
  const parsedAcres = Number(cleanAcresStr);
  const budgetMode: BudgetMode = s4Val.budget_mode;

  const snapshot: ValidatedAnalysisSnapshot = {
    crop_id: cleanCropId,
    cultivation_district_id: cleanDistrictId,
    harvest_date: cleanHarvestDate,
    forecast_target_date: cleanHarvestDate,
    expected_yield_kg: parsedYield,
    expected_yield_kg_string: cleanYieldStr,
    target_market_id: cleanMarketId,
    price_type: cleanPriceType,
    total_cultivation_cost: parsedCost,
    total_cultivation_cost_string: cleanCostStr,
    metadata: {
      land_extent_acres: parsedAcres,
      land_extent_acres_string: cleanAcresStr,
      budget_mode: budgetMode,
      detailed_expenses: budgetMode === "detailed" ? step4.detailed_expenses : undefined,
      is_zero_cultivation_cost: Boolean(s4Val.isZeroCost),
      zero_cost_warning: s4Val.warnings?.total_cultivation_cost_lkr,
      created_at: new Date().toISOString(),
      version: "1.0",
    },
  };

  return {
    isValid: true,
    step1Validation: s1Val,
    step2Validation: s2Val,
    step3Validation: s3Val,
    step4Validation: s4Val,
    snapshot,
  };
}

/**
 * Checks whether all 4 wizard steps are fully completed and valid.
 */
export function isFullWizardComplete(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  step3: Partial<Step3FormData>,
  step4: Partial<Step4FormData>,
  referenceDate?: Date
): boolean {
  return validateFullWizard(step1, step2, step3, step4, referenceDate).isValid;
}

/**
 * Builds a reusable typed analysis payload mapping from wizard inputs.
 * Returns null if any wizard step is invalid or incomplete.
 */
export function buildValidatedAnalysisPayload(
  step1: Partial<Step1FormData>,
  step2: Partial<Step2FormData>,
  step3: Partial<Step3FormData>,
  step4: Partial<Step4FormData>,
  referenceDate?: Date
): ValidatedAnalysisSnapshot | null {
  const result = validateFullWizard(step1, step2, step3, step4, referenceDate);
  return result.isValid && result.snapshot ? result.snapshot : null;
}

/**
 * Loads and validates all 4 wizard steps from browser session storage.
 */
export function loadAndValidateWizardFromStorage(
  referenceDate?: Date
): FullWizardValidationResult {
  const s1 = loadStep1FromStorage();
  const s2 = loadStep2FromStorage();
  const s3 = loadStep3FromStorage();
  const s4 = loadStep4FromStorage();
  return validateFullWizard(s1, s2, s3, s4, referenceDate);
}

/**
 * Validates the schema and values of a stored analysis snapshot.
 */
export function isAnalysisSnapshotValid(
  snapshot: unknown,
  referenceDate?: Date
): snapshot is ValidatedAnalysisSnapshot {
  if (!snapshot || typeof snapshot !== "object") return false;

  const s = snapshot as Partial<ValidatedAnalysisSnapshot>;

  // 1. Core mapped fields
  if (typeof s.crop_id !== "string" || !SUPPORTED_FRONTEND_CROPS.some((c) => c.crop_id === s.crop_id)) {
    return false;
  }
  if (
    typeof s.cultivation_district_id !== "string" ||
    !SRI_LANKA_DISTRICTS.some((d) => d.id === s.cultivation_district_id)
  ) {
    return false;
  }
  if (typeof s.harvest_date !== "string" || !validateHarvestDate(s.harvest_date, referenceDate).isValid) {
    return false;
  }
  if (
    typeof s.expected_yield_kg !== "number" ||
    !Number.isFinite(s.expected_yield_kg) ||
    s.expected_yield_kg <= 0 ||
    s.expected_yield_kg > 1000000
  ) {
    return false;
  }
  if (
    typeof s.target_market_id !== "string" ||
    !STANDARD_MARKETS.some((m) => m.id === s.target_market_id)
  ) {
    return false;
  }
  if (s.price_type !== "wholesale" && s.price_type !== "retail") {
    return false;
  }
  if (
    typeof s.total_cultivation_cost !== "number" ||
    !Number.isFinite(s.total_cultivation_cost) ||
    s.total_cultivation_cost < 0
  ) {
    return false;
  }

  // 2. Metadata fields
  if (!s.metadata || typeof s.metadata !== "object") {
    return false;
  }
  if (
    typeof s.metadata.land_extent_acres !== "number" ||
    !Number.isFinite(s.metadata.land_extent_acres) ||
    s.metadata.land_extent_acres <= 0 ||
    s.metadata.land_extent_acres > 10000
  ) {
    return false;
  }
  if (s.metadata.budget_mode !== "quick" && s.metadata.budget_mode !== "detailed") {
    return false;
  }

  return true;
}

/**
 * Safely saves a validated analysis snapshot into browser session storage.
 */
export function saveAnalysisSnapshot(snapshot: ValidatedAnalysisSnapshot): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (!isAnalysisSnapshotValid(snapshot)) {
      return false;
    }
    window.sessionStorage.setItem(ANALYSIS_SNAPSHOT_STORAGE_KEY, JSON.stringify(snapshot));
    return true;
  } catch {
    return false;
  }
}

/**
 * Safely reads and validates the analysis snapshot from browser session storage.
 * Returns null if snapshot is missing, corrupted, or invalid.
 */
export function loadAnalysisSnapshot(referenceDate?: Date): ValidatedAnalysisSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(ANALYSIS_SNAPSHOT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!isAnalysisSnapshotValid(parsed, referenceDate)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Clears the stored analysis snapshot from browser session storage.
 */
export function clearAnalysisSnapshot(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(ANALYSIS_SNAPSHOT_STORAGE_KEY);
  } catch {
    // Ignore silently
  }
}






