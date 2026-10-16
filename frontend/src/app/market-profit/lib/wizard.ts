/**
 * Wizard state management and Step 1 validation for Component 1.
 * Supports session persistence and validation for Crop & Location selection.
 */

import { SUPPORTED_FRONTEND_CROPS, SRI_LANKA_DISTRICTS } from "./constants";

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
}

export interface Step2ValidationResult {
  isValid: boolean;
  errors: {
    harvest_date?: string;
    land_extent_acres?: string;
  };
}

export const STEP2_STORAGE_KEY = "agrodecision_wizard_step2";
export const MAX_LAND_EXTENT_ACRES = 1000;

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
 * Validates Step 2 form input (Expected Harvest Date and Cultivation Land Extent).
 */
export function validateStep2(
  data: Partial<Step2FormData>,
  referenceDate?: Date,
  maxLandLimit: number = MAX_LAND_EXTENT_ACRES
): Step2ValidationResult {
  const dateVal = validateHarvestDate(data.harvest_date, referenceDate);
  const extentVal = validateLandExtent(data.land_extent_acres, maxLandLimit);

  const errors: { harvest_date?: string; land_extent_acres?: string } = {};
  if (!dateVal.isValid) errors.harvest_date = dateVal.error;
  if (!extentVal.isValid) errors.land_extent_acres = extentVal.error;

  return {
    isValid: dateVal.isValid && extentVal.isValid,
    errors,
  };
}

/**
 * Safely reads Step 2 state from browser session storage.
 */
export function loadStep2FromStorage(): Step2FormData {
  if (typeof window === "undefined") {
    return { harvest_date: "", land_extent_acres: "" };
  }

  try {
    const stored = window.sessionStorage.getItem(STEP2_STORAGE_KEY);
    if (!stored) {
      return { harvest_date: "", land_extent_acres: "" };
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
    };
  } catch {
    return { harvest_date: "", land_extent_acres: "" };
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

