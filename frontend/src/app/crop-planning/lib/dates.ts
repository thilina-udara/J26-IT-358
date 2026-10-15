export function formatDate(value: string | null | undefined, locale = "en-GB") {
  if (!value) return "Not recorded";
  // Calendar dates must not shift when a browser timezone is behind UTC.
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}
export function utcToday(now = new Date()) { return now.toISOString().slice(0, 10); }
export function nextUtcDate(now = new Date()) { return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1)).toISOString().slice(0, 10); }
