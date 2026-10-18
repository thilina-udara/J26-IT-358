import type { Credentials, PlanFields } from "./contracts";
import { CROPS, DISTRICTS } from "./contracts";
export function validateCredentials(input: Credentials, registration: boolean) {
  const errors: Record<string, string> = {};
  if (!/^[a-z0-9._@+\-]{3,100}$/i.test(input.login_identifier.trim())) errors.login_identifier = "Use 3–100 letters, numbers, or . _ @ + -";
  if (!input.login_identifier.trim()) errors.login_identifier = "Enter your username.";
  const length = Array.from(input.password).length;
  if (length < (registration ? 8 : 1) || length > 128) errors.password = registration ? "Use a password of 8–128 characters." : "Enter your password (up to 128 characters).";
  if (!length) errors.password = "Enter your password.";
  return errors;
}
export function validatePlan(input: PlanFields, creating: boolean, today = new Date().toISOString().slice(0, 10)) {
  const errors: Record<string, string> = {};
  if (!DISTRICTS.includes(input.district)) errors.district = "Choose Matara or Hambantota.";
  if (!CROPS.includes(input.crop)) errors.crop = "Choose one of the available crops.";
  if (input.farmer_declared_season !== null && !["Maha", "Yala"].includes(input.farmer_declared_season)) errors.farmer_declared_season = "Choose Maha, Yala, or leave the season undeclared.";
  if (!input.region.trim() || input.region.trim().length > 100) errors.region = "Enter a region of 1–100 characters.";
  if (!Number.isFinite(input.land_size_acres) || input.land_size_acres <= 0) errors.land_size_acres = "Enter a land size greater than zero.";
  if (!input.planting_date) errors.planting_date = "Choose a planting date.";
  else if (creating && input.planting_date <= today) errors.planting_date = "Please choose a future planting date.";
  if (!input.expected_harvest_date || input.expected_harvest_date < input.planting_date) errors.expected_harvest_date = "Choose a harvest date on or after planting.";
  return errors;
}
