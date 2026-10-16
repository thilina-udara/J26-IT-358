/**
 * Agricultural data formatting helpers for Sri Lankan currency (LKR),
 * metric weights (kg), percentages, and dates.
 */

/**
 * Format a number or numeric string as Sri Lankan Rupees (LKR).
 * Examples: 170000 -> "LKR 170,000.00", "350000.5" -> "LKR 350,000.50"
 */
export function formatLKR(
  value: number | string | null | undefined,
  options: { showCents?: boolean; fallback?: string } = {}
): string {
  const { showCents = true, fallback = "—" } = options;
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (isNaN(num)) {
    return fallback;
  }

  const formattedNumber = num.toLocaleString("en-LK", {
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
  });

  return `LKR ${formattedNumber}`;
}

/**
 * Format a harvest weight or volume in kilograms (kg).
 * Examples: 2500 -> "2,500 kg", 1250.5 -> "1,250.5 kg"
 */
export function formatKg(
  value: number | string | null | undefined,
  options: { fallback?: string; includeUnit?: boolean } = {}
): string {
  const { fallback = "—", includeUnit = true } = options;
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (isNaN(num)) {
    return fallback;
  }

  const formattedNumber = num.toLocaleString("en-LK", {
    maximumFractionDigits: 2,
  });

  return includeUnit ? `${formattedNumber} kg` : formattedNumber;
}

/**
 * Format a unit commodity price in LKR per kg.
 * Examples: 140 -> "LKR 140.00 / kg"
 */
export function formatLKRPerKg(
  value: number | string | null | undefined,
  options: { fallback?: string } = {}
): string {
  const { fallback = "—" } = options;
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (isNaN(num)) {
    return fallback;
  }

  const formatted = num.toLocaleString("en-LK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return `LKR ${formatted} / kg`;
}

/**
 * Format a percentage value. Returns "Undefined" when value is null (e.g., 0 cost ROI).
 * Examples: 94.44 -> "94.44%", null -> "Undefined", -30 -> "-30.00%"
 */
export function formatPercent(
  value: number | string | null | undefined,
  options: { fallback?: string } = {}
): string {
  const { fallback = "Undefined" } = options;
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (isNaN(num)) {
    return fallback;
  }

  const formatted = num.toLocaleString("en-LK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return `${formatted}%`;
}

/**
 * Format an ISO date string (YYYY-MM-DD) into readable format.
 * Examples: "2026-12-15" -> "Dec 15, 2026"
 */
export function formatDateDisplay(
  dateStr: string | null | undefined,
  fallback = "—"
): string {
  if (!dateStr) return fallback;
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
      }
    }
    const parsed = new Date(dateStr);
    return isNaN(parsed.getTime()) ? fallback : parsed.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return fallback;
  }
}

/**
 * Safely parse user input into a non-negative number.
 */
export function parsePositiveNumber(value: string | number): number {
  if (typeof value === "number") return isNaN(value) ? 0 : Math.max(0, value);
  const parsed = parseFloat(String(value).replace(/[^0-9.-]+/g, ""));
  return isNaN(parsed) ? 0 : Math.max(0, parsed);
}
