"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, FlaskConical, Loader2, MapPin, Sprout } from "lucide-react";
import { NativeSelect } from "./ui/native-select";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { ErrorNotice, Field, inputProps, Notice } from "./ui";
import { useSession } from "./session";
import type { Plan, PlanFields, Season, Submission } from "../lib/contracts";
import { CROPS, DISTRICTS } from "../lib/contracts";
import { formatDate, nextUtcDate, utcToday } from "../lib/dates";
import { validatePlan } from "../lib/validation";
import { ApiError } from "../lib/api";

export default function PlanForm({
  plan,
  onSaved,
  submitLabel,
}: {
  plan?: Plan;
  onSaved: (result: Submission | { plan: Plan }) => void;
  submitLabel?: string;
}) {
  const { api } = useSession();
  const [fields, setFields] = useState<PlanFields>(
    plan
      ? {
          crop: plan.crop,
          district: plan.district,
          region: plan.region,
          land_size_acres: plan.land_size_acres,
          planting_date: plan.planting_date,
          expected_harvest_date: plan.expected_harvest_date,
          farmer_declared_season: plan.farmer_declared_season,
        }
      : {
          district: "Matara",
          crop: "Corn",
          region: "",
          land_size_acres: 0,
          planting_date: "",
          expected_harvest_date: "",
          farmer_declared_season: null,
        }
  );

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const validation = validatePlan(fields, !plan);
  const fieldError = (name: string) => errors[name] || (touched[name] ? validation[name] : undefined);

  function update<K extends keyof PlanFields>(key: K, value: PlanFields[K]) {
    setFields((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: "", ...(key === "farmer_declared_season" ? { season: "" } : {}) }));
    setTouched((previous) => ({ ...previous, [key]: true }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    setErrors(validation);
    if (Object.keys(validation).length) {
      if (typeof document !== "undefined") document.getElementById(Object.keys(validation)[0])?.focus();
      return;
    }
    setBusy(true);
    try {
      onSaved(plan ? await api.update(plan.plan_id, fields) : await api.create(fields));
    } catch (reason) {
      setError(reason);
      if (reason instanceof ApiError) setErrors(reason.fields);
    } finally {
      setBusy(false);
    }
  }

  const isPastDate = Boolean(!plan && fields.planting_date && fields.planting_date <= utcToday());
  const dateHint = fields.planting_date ? `Selected: ${formatDate(fields.planting_date)}` : "Please choose a future planting date.";
  const researchLabUrl = `/crop-planning/research-demo/history?crop=${encodeURIComponent(fields.crop)}&district=${encodeURIComponent(fields.district)}&planting_date=${encodeURIComponent(fields.planting_date)}&harvest_date=${encodeURIComponent(fields.expected_harvest_date)}&land_size=${fields.land_size_acres || 2}${fields.farmer_declared_season ? `&season=${encodeURIComponent(fields.farmer_declared_season)}` : ""}`;

  return (
    <form onSubmit={submit} noValidate className="cp-plan-form">
      <ErrorNotice error={error} />
      <fieldset disabled={busy}>
        <legend className="cp-sr-only">Cultivation details</legend>

        <section className="cp-form-section">
          <div className="cp-form-section-title">
            <span>
              <MapPin size={18} aria-hidden="true" />
            </span>
            <div>
              <h3>Where you’re growing</h3>
              <p>Your district and the locality used in your records.</p>
            </div>
          </div>
          <div className="cp-grid two">
            <Field label="District" name="district" error={fieldError("district")}>
              <NativeSelect
                {...inputProps("district", fieldError("district"))}
                value={fields.district}
                onChange={(event) => update("district", event.target.value as PlanFields["district"])}
              >
                {DISTRICTS.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </NativeSelect>
            </Field>
            <Field label="Region / locality" name="region" error={fieldError("region")}>
              <Input
                {...inputProps("region", fieldError("region"))}
                placeholder="Enter your locality"
                value={fields.region}
                onChange={(event) => update("region", event.target.value)}
                onBlur={() => setTouched((previous) => ({ ...previous, region: true }))}
                maxLength={100}
                required
              />
            </Field>
          </div>
        </section>

        <section className="cp-form-section">
          <div className="cp-form-section-title">
            <span>
              <Sprout size={18} aria-hidden="true" />
            </span>
            <div>
              <h3>What you’re cultivating</h3>
              <p>The crop and land size for your individual plan.</p>
            </div>
          </div>
          <div className="cp-grid two">
            <Field label="Crop" name="crop" error={fieldError("crop")}>
              <NativeSelect
                {...inputProps("crop", fieldError("crop"))}
                value={fields.crop}
                onChange={(event) => update("crop", event.target.value as PlanFields["crop"])}
              >
                {CROPS.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </NativeSelect>
            </Field>
            <Field label="Your land size (acres)" name="land_size_acres" error={fieldError("land_size_acres")}>
              <div className="cp-unit-input">
                <Input
                  {...inputProps("land_size_acres", fieldError("land_size_acres"))}
                  type="number"
                  min="0"
                  step="any"
                  placeholder="e.g. 2.5"
                  className="pr-16"
                  value={fields.land_size_acres || ""}
                  onChange={(event) => update("land_size_acres", Number(event.target.value))}
                  onBlur={() => setTouched((previous) => ({ ...previous, land_size_acres: true }))}
                  required
                />
                <span>acres</span>
              </div>
            </Field>
          </div>
        </section>

        {!plan && <p className="cp-small-note">Testing a 2025 or early-2026 scenario? <a href="http://127.0.0.1:8011" target="_blank" rel="noopener noreferrer">Use private historical model testing</a> to run saved models against the historical dataset without creating live farmer records.</p>}

        <section className="cp-form-section">
          <div className="cp-form-section-title">
            <span>
              <CalendarDays size={18} aria-hidden="true" />
            </span>
            <div>
              <h3>Your season at a glance</h3>
              <p>Dates follow your browser’s date format. The readable selection appears below.</p>
            </div>
          </div>
          <div className="cp-grid two">
            <Field
              label="Planting date"
              name="planting_date"
              error={fieldError("planting_date")}
              hint={!plan ? dateHint : fields.planting_date ? `Selected: ${formatDate(fields.planting_date)}` : "Choose a planting date."}
            >
              <Input
                {...inputProps("planting_date", fieldError("planting_date"), true)}
                type="date"
                min={!plan ? nextUtcDate() : undefined}
                value={fields.planting_date}
                onChange={(event) => update("planting_date", event.target.value)}
                required
              />
            </Field>
            <Field
              label="Expected harvest date"
              name="expected_harvest_date"
              error={fieldError("expected_harvest_date")}
              hint={fields.expected_harvest_date ? `Selected: ${formatDate(fields.expected_harvest_date)}` : "On or after your planting date."}
            >
              <Input
                {...inputProps("expected_harvest_date", fieldError("expected_harvest_date"), true)}
                type="date"
                min={fields.planting_date || undefined}
                value={fields.expected_harvest_date}
                onChange={(event) => update("expected_harvest_date", event.target.value)}
                required
              />
            </Field>
            <Field
              label="Farmer-declared season"
              name="farmer_declared_season"
              error={fieldError("farmer_declared_season") || errors.season}
              hint="Your declaration provides context; it does not verify a statistical season."
            >
              <NativeSelect
                {...inputProps("farmer_declared_season", fieldError("farmer_declared_season") || errors.season, true)}
                value={fields.farmer_declared_season ?? ""}
                onChange={(event) => update("farmer_declared_season", (event.target.value || null) as Season | null)}
              >
                <option value="">Not declared</option>
                <option>Maha</option>
                <option>Yala</option>
              </NativeSelect>
            </Field>
          </div>

          {isPastDate && (
            <div
              style={{
                marginTop: "16px",
                padding: "16px 18px",
                borderRadius: "14px",
                background: "#f0fdf4",
                border: "1px solid #86efac",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", flex: 1, minWidth: "260px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "10px",
                    background: "#dcfce7",
                    color: "#16a34a",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <FlaskConical size={20} />
                </div>
                <div>
                  <strong style={{ fontSize: "14px", color: "#14532d", display: "block" }}>
                    Testing historical 2025–2026 dates?
                  </strong>
                  <p style={{ margin: "2px 0 0 0", fontSize: "12.5px", color: "#166534", lineHeight: 1.45 }}>
                    Operational farmer registration strictly requires future planting dates to protect live farmer records. To review historical scenario inputs for dates like <strong>{fields.planting_date}</strong>, use the isolated <strong>Research Lab</strong>.
                  </p>
                </div>
              </div>
              <Link
                href={researchLabUrl}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 16px",
                  borderRadius: "10px",
                  background: "#16a34a",
                  color: "#ffffff",
                  fontWeight: 600,
                  fontSize: "13px",
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                }}
              >
                <FlaskConical size={16} />
                Simulate in Research Lab
                <ArrowRight size={14} />
              </Link>
            </div>
          )}
        </section>
      </fieldset>

      {errors.planting_date && (
        <Notice kind="error">
          <div>{errors.planting_date}</div>
          {isPastDate && (
            <div style={{ marginTop: "6px", fontSize: "12.5px" }}>
              Looking to test models on historical 2025–2026 dates? Switch to the{" "}
              <Link href={researchLabUrl} style={{ fontWeight: 700, textDecoration: "underline" }}>
                Research Lab (2025–2026)
              </Link>{" "}
              which reviews scenario inputs while keeping private historical outputs withheld.
            </div>
          )}
        </Notice>
      )}

      <div className="cp-form-footer">
        <span>{plan ? "Updates preserve your record history." : "Your plan is saved before analysis runs."}</span>
        <Button type="submit" disabled={busy}>
          {busy ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <ArrowRight size={17} aria-hidden="true" />}
          {busy ? "Saving your plan…" : plan ? "Save changes" : submitLabel ?? "Save plan & analyze"}
        </Button>
      </div>
    </form>
  );
}
