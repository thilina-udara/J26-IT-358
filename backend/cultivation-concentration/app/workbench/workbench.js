"use strict";
(() => {
  let credential = "";
  let busy = false;
  const element = id => document.getElementById(id);
  const form = element("scenario-form");
  function error(message) { element("error").textContent = message; element("error").hidden = !message; }
  function clearResult() { element("result").hidden = true; element("empty").hidden = false; }
  function lock() {
    credential = ""; element("credential").value = ""; element("credential-file").value = "";
    element("workbench").hidden = true; element("unlock").hidden = false;
    element("metadata").replaceChildren(); element("probabilities").replaceChildren(); element("classification").textContent = "";
    element("classification-panel").className = "";
    clearResult();
  }
  async function request(path, payload) {
    const result = await fetch(path, { method: payload ? "POST" : "GET", cache: "no-store", credentials: "omit",
      headers: { Authorization: `Bearer ${credential}`, ...(payload ? { "Content-Type": "application/json" } : {}) },
      body: payload ? JSON.stringify(payload) : undefined });
    const data = await result.json();
    if (!result.ok) {
      if (result.status === 401) lock();
      const detail = typeof data.detail === "string" ? data.detail : "Check your historical scenario fields.";
      throw new Error(detail);
    }
    return data;
  }
  element("credential-file").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 1024) { error("Choose the small local researcher credential text file."); return; }
    element("credential").value = (await file.text()).trim();
  });
  element("unlock-form").addEventListener("submit", async event => {
    event.preventDefault(); credential = element("credential").value.trim(); error("");
    try {
      await request("/api/private-research/status");
      element("credential").value = ""; element("credential-file").value = "";
      element("unlock").hidden = true; element("workbench").hidden = false;
      element("planting_date").focus();
    } catch (reason) { credential = ""; error(reason.message || "Could not unlock the local workbench."); }
  });
  element("lock").addEventListener("click", () => { lock(); error(""); });
  form.addEventListener("input", () => {
    clearResult(); error("");
    element("decision_cutoff").max = element("planting_date").value;
    element("expected_harvest_date").min = element("planting_date").value;
  });
  function metadata(label, value) {
    const title = document.createElement("dt"), detail = document.createElement("dd");
    title.textContent = label; detail.textContent = value; element("metadata").append(title, detail);
  }
  form.addEventListener("submit", async event => {
    event.preventDefault(); if (busy) return;
    busy = true; error(""); clearResult();
    const payload = Object.fromEntries(new FormData(form));
    payload.land_size_acres = Number(payload.land_size_acres);
    if (!payload.decision_cutoff) delete payload.decision_cutoff;
    const submitted = JSON.stringify(payload);
    element("run").disabled = true; element("run").textContent = "Running saved model…";
    try {
      const result = await request("/api/private-research/evaluate", payload);
      const current = Object.fromEntries(new FormData(form)); current.land_size_acres = Number(current.land_size_acres);
      if (!current.decision_cutoff) delete current.decision_cutoff;
      if (!credential || JSON.stringify(current) !== submitted) return; // Ignore changed inputs or a locked session.
      const label = ["Low", "Medium", "High"].includes(result.classification) ? result.classification : null;
      element("classification-panel").className = label ? label.toLowerCase() : "";
      element("classification").textContent = label ? `${label} · historical model class` : "Insufficient historical replay coverage";
      element("classification-description").textContent = label ? "Computed using the selected frozen pipeline and historical replay features. This is a model test, not validated current risk." : "The historical dataset does not provide enough prior replay features for this scenario. No class is inferred when the model has no historical input window.";
      element("probabilities").replaceChildren();
      if (label && result.class_probabilities) {
        for (const name of ["Low", "Medium", "High"]) {
          const value = result.class_probabilities[name];
          if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) continue;
          const row = document.createElement("div"), title = document.createElement("span"), percent = document.createElement("strong");
          title.textContent = name; percent.textContent = `${(value * 100).toFixed(1)}%`; row.append(title, percent); element("probabilities").append(row);
        }
      } else if (label) {
        const note = document.createElement("p"); note.className = "small";
        note.textContent = "This saved model does not provide class probabilities.";
        element("probabilities").append(note);
      }
      element("metadata").replaceChildren();
      metadata("Model", result.model_name);
      metadata("Model crop category", result.model_crop_category);
      metadata("Saved model training", `Through recorded Year ${result.trained_through}; not source publication time`);
      metadata("Scenario", `${result.scenario.district} · ${result.scenario.crop} · ${result.scenario.season}`);
      metadata("Your dates", `Planting ${result.scenario.planting_date} · Expected harvest ${result.scenario.expected_harvest_date}`);
      metadata("Decision cutoff", result.scenario.decision_cutoff || result.scenario.planting_date);
      metadata("Saved input contract", `${result.feature_names.length} features`);
      metadata("Observation availability", result.observation_availability);
      metadata("Probability meaning", "Historical class probabilities only; calibration and loss-risk interpretation are unverified.");
      element("empty").hidden = true; element("result").hidden = false;
      element("result").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (reason) { error(reason.message || "Could not reach the local research workbench."); }
    finally { busy = false; element("run").disabled = false; element("run").textContent = "Run historical model prediction →"; }
  });
})();
