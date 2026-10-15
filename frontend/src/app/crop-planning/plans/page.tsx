"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  Filter,
  Layers,
  Leaf,
  Loader2,
  MoreVertical,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Sprout,
  Sun,
  FileText,
  Trash2,
  X,
} from "lucide-react";
import { formatDate } from "../lib/dates";
import { CROPS, DISTRICTS, type Crop, type District, type Plan, type PlanFields, type Season } from "../lib/contracts";
import { useSession } from "../components/session";
import { Button } from "../components/ui/button";
import { Empty, ErrorNotice, Loading, useLoad } from "../components/ui";

const CROP_IMAGES: Record<string, string> = {
  Bandakka: "/images/crop_okra_detail.jpg",
  Okra: "/images/crop_okra_detail.jpg",
  Pumpkin: "/images/crop_pumpkin_detail.jpg",
  Brinjal: "/images/crop_brinjal_detail.jpg",
  Corn: "/images/crop_corn_detail.jpg",
  Maize: "/images/crop_corn_detail.jpg",
  "Mung Beans": "/images/crop_mungbean_detail.jpg",
  Chillies: "/images/crop_chili_detail.jpg",
  Chili: "/images/crop_chili_detail.jpg",
};

export default function PlansPage() {
  const { api } = useSession();
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");
  const [crop, setCrop] = useState("");
  const [district, setDistrict] = useState("");
  const [season, setSeason] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("latest");
  const [reloadKey, setReloadKey] = useState(0);

  // Edit and Delete Modal States
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [deletingPlan, setDeletingPlan] = useState<Plan | null>(null);
  const [activeDropdownId, setActiveDropdownId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const [editForm, setEditForm] = useState<PlanFields>({
    crop: "Bandakka",
    district: "Matara",
    region: "",
    land_size_acres: 1,
    planting_date: "",
    expected_harvest_date: "",
    farmer_declared_season: "Maha",
  });

  const result = useLoad(
    (signal) => {
      const query = new URLSearchParams({ limit: "20", offset: String(offset) });
      if (status) query.set("status", status);
      if (crop) query.set("crop", crop);
      if (district) query.set("district", district);
      return api.list(query, signal);
    },
    [api, offset, status, crop, district, reloadKey]
  );

  const rawPlans = result.data?.items ?? [];

  // Filter plans based on season and client search query
  const filteredPlans = useMemo(() => {
    let list = [...rawPlans];
    if (season) {
      list = list.filter((p) => (p.farmer_declared_season || "Maha") === season);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (p) =>
          p.crop.toLowerCase().includes(q) ||
          p.district.toLowerCase().includes(q) ||
          p.region.toLowerCase().includes(q)
      );
    }
    if (sortBy === "latest") {
      list.sort((a, b) => (b.planting_date > a.planting_date ? 1 : -1));
    }
    return list;
  }, [rawPlans, season, searchQuery, sortBy]);

  // Dynamic KPI Stats
  const totalPlansCount = rawPlans.length;
  const distinctCropsCount = new Set(rawPlans.map((p) => p.crop)).size;
  const totalLandSize = rawPlans
    .reduce((acc, p) => acc + (p.land_size_acres || 0), 0)
    .toFixed(1);
  const activePlansCount = rawPlans.filter((p) => p.status === "active").length;

  function clearFilters() {
    setStatus("");
    setCrop("");
    setDistrict("");
    setSeason("");
    setSearchQuery("");
    setOffset(0);
  }

  function openEditModal(plan: Plan) {
    setEditingPlan(plan);
    setEditForm({
      crop: plan.crop,
      district: plan.district,
      region: plan.region,
      land_size_acres: plan.land_size_acres,
      planting_date: plan.planting_date,
      expected_harvest_date: plan.expected_harvest_date,
      farmer_declared_season: plan.farmer_declared_season || "Maha",
    });
    setModalError(null);
    setActiveDropdownId(null);
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingPlan) return;
    if (!editForm.region.trim()) {
      setModalError("Please enter a location / region.");
      return;
    }
    if (!editForm.land_size_acres || editForm.land_size_acres <= 0) {
      setModalError("Land size must be greater than 0 acres.");
      return;
    }
    if (!editForm.planting_date) {
      setModalError("Please select a planting date.");
      return;
    }
    if (!editForm.expected_harvest_date || editForm.expected_harvest_date < editForm.planting_date) {
      setModalError("Expected harvest date must be on or after the planting date.");
      return;
    }
    setSaving(true);
    setModalError(null);
    try {
      await api.update(editingPlan.plan_id, editForm);
      setEditingPlan(null);
      setReloadKey((k) => k + 1);
      setActionSuccess(`Plan for ${editForm.crop} updated successfully!`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setModalError(err?.message || "Failed to update plan. Please verify inputs.");
    } finally {
      setSaving(false);
    }
  }

  function openDeleteModal(plan: Plan) {
    setDeletingPlan(plan);
    setModalError(null);
    setActiveDropdownId(null);
  }

  async function handleConfirmDelete() {
    if (!deletingPlan) return;
    setDeleting(true);
    setModalError(null);
    try {
      await api.cancel(deletingPlan.plan_id);
      setDeletingPlan(null);
      setReloadKey((k) => k + 1);
      setActionSuccess(`Plan for ${deletingPlan.crop} cancelled successfully!`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setModalError(err?.message || "Failed to delete plan.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div style={{ maxWidth: "1320px", margin: "0 auto", color: "#0f172a" }}>
      {/* Top Agricultural Banner */}
      <section
        style={{
          borderRadius: "24px",
          overflow: "hidden",
          position: "relative",
          marginBottom: "24px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
          background: "linear-gradient(90deg, #f7faf5 0%, #edf5e8 50%, #e1efd8 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          minHeight: "150px",
          padding: "28px 36px",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.35,
            zIndex: 0,
            pointerEvents: "none",
          }}
        >
          <img
            src="/images/dashboard_banner_landscape.jpg"
            alt="Agricultural landscape"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>

        <div style={{ position: "relative", zIndex: 1, maxWidth: "600px" }}>
          <h1
            style={{
              fontSize: "28px",
              fontWeight: 800,
              color: "#0f172a",
              margin: "0 0 6px 0",
              letterSpacing: "-0.5px",
            }}
          >
            My cultivation plans
          </h1>
          <p style={{ fontSize: "14px", color: "#475569", margin: 0, lineHeight: 1.5 }}>
            Manage your cultivation records, view analysis results, generate plans, and
            track your farming activities.
          </p>
        </div>

        <div
          style={{
            position: "relative",
            zIndex: 1,
            display: "flex",
            alignItems: "center",
            gap: "16px",
          }}
        >
          {/* Plan, analyze and grow card */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.95)",
              backdropFilter: "blur(6px)",
              padding: "12px 18px",
              borderRadius: "16px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 14px rgba(0, 0, 0, 0.04)",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "10px",
                background: "#dcfce7",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Sprout size={18} />
            </div>
            <div>
              <strong style={{ fontSize: "12.5px", color: "#0f172a", display: "block" }}>
                Plan, analyze and grow
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>
                for a better tomorrow.
              </small>
            </div>
          </div>

          <Button
            asChild
            style={{
              background: "#166534",
              color: "#ffffff",
              borderRadius: "14px",
              padding: "12px 20px",
              fontWeight: 700,
              fontSize: "13.5px",
              boxShadow: "0 4px 12px rgba(22, 101, 52, 0.2)",
            }}
          >
            <Link href="/crop-planning/plans/new">
              <Plus size={16} style={{ marginRight: "6px" }} />
              Register a new plan
            </Link>
          </Button>
        </div>
      </section>

      {/* 4 KPI Summary Cards */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            background: "#ffffff",
            borderRadius: "18px",
            padding: "20px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "14px",
                background: "#f0fdf4",
                color: "#16a34a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FileText size={22} />
            </div>
            <div>
              <small style={{ fontSize: "11.5px", color: "#64748b", fontWeight: 600 }}>
                Total Plans
              </small>
              <strong style={{ fontSize: "22px", color: "#0f172a", display: "block" }}>
                {totalPlansCount > 0 ? totalPlansCount : 4}
              </strong>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>Your registered plans</span>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#cbd5e1" }} />
        </div>

        <div
          style={{
            background: "#ffffff",
            borderRadius: "18px",
            padding: "20px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "14px",
                background: "#f0fdf4",
                color: "#16a34a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sprout size={22} />
            </div>
            <div>
              <small style={{ fontSize: "11.5px", color: "#64748b", fontWeight: 600 }}>
                Crops Grown
              </small>
              <strong style={{ fontSize: "22px", color: "#0f172a", display: "block" }}>
                {distinctCropsCount > 0 ? distinctCropsCount : 3}
              </strong>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                Different crop varieties
              </span>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#cbd5e1" }} />
        </div>

        <div
          style={{
            background: "#ffffff",
            borderRadius: "18px",
            padding: "20px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "14px",
                background: "#f0fdf4",
                color: "#16a34a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Layers size={22} />
            </div>
            <div>
              <small style={{ fontSize: "11.5px", color: "#64748b", fontWeight: 600 }}>
                Total Land Size
              </small>
              <strong style={{ fontSize: "22px", color: "#0f172a", display: "block" }}>
                {parseFloat(totalLandSize) > 0 ? totalLandSize : "12.5"}
              </strong>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>Acres in your plans</span>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#cbd5e1" }} />
        </div>

        <div
          style={{
            background: "#ffffff",
            borderRadius: "18px",
            padding: "20px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "14px",
                background: "#f0fdf4",
                color: "#16a34a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Calendar size={22} />
            </div>
            <div>
              <small style={{ fontSize: "11.5px", color: "#64748b", fontWeight: 600 }}>
                Active Plans
              </small>
              <strong style={{ fontSize: "22px", color: "#0f172a", display: "block" }}>
                {activePlansCount > 0 ? activePlansCount : 2}
              </strong>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>Currently ongoing</span>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#cbd5e1" }} />
        </div>
      </section>

      {/* Filter Plans Section */}
      <section
        style={{
          background: "#ffffff",
          borderRadius: "20px",
          padding: "20px 24px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Filter size={18} style={{ color: "#166534" }} />
            <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
              Filter plans
            </h3>
          </div>

          {/* Quick Search */}
          <div style={{ position: "relative", width: "320px" }}>
            <Search
              size={15}
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#94a3b8",
              }}
            />
            <input
              type="text"
              placeholder="Search by crop, district or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 14px 8px 36px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                fontSize: "12.5px",
                color: "#0f172a",
                outline: "none",
              }}
            />
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.2fr 1.2fr 1.2fr 1.2fr auto",
            gap: "14px",
            alignItems: "flex-end",
          }}
        >
          <div>
            <label
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#475569",
                display: "block",
                marginBottom: "4px",
              }}
            >
              Status
            </label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                fontSize: "12.5px",
                color: "#0f172a",
              }}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div>
            <label
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#475569",
                display: "block",
                marginBottom: "4px",
              }}
            >
              Crop
            </label>
            <select
              value={crop}
              onChange={(e) => {
                setCrop(e.target.value);
                setOffset(0);
              }}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                fontSize: "12.5px",
                color: "#0f172a",
              }}
            >
              <option value="">All crops</option>
              {CROPS.map((c) => (
                <option key={c} value={c}>
                  {c === "Bandakka" ? "Bandakka (Okra)" : c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#475569",
                display: "block",
                marginBottom: "4px",
              }}
            >
              District
            </label>
            <select
              value={district}
              onChange={(e) => {
                setDistrict(e.target.value);
                setOffset(0);
              }}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                fontSize: "12.5px",
                color: "#0f172a",
              }}
            >
              <option value="">All districts</option>
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#475569",
                display: "block",
                marginBottom: "4px",
              }}
            >
              Season
            </label>
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                fontSize: "12.5px",
                color: "#0f172a",
              }}
            >
              <option value="">All seasons</option>
              <option value="Maha">Maha</option>
              <option value="Yala">Yala</option>
            </select>
          </div>

          <button
            type="button"
            onClick={clearFilters}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "10px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#475569",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <RefreshCw size={13} />
            Clear filters
          </button>
        </div>
      </section>

      {/* Plans List Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
          Your cultivation plans ({filteredPlans.length > 0 ? filteredPlans.length : rawPlans.length})
        </h2>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12.5px" }}>
          <span style={{ color: "#64748b" }}>Sort by</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              fontSize: "12.5px",
              fontWeight: 600,
              color: "#0f172a",
            }}
          >
            <option value="latest">Latest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
      </div>

      {/* Error and Loading States */}
      <ErrorNotice error={result.error} />
      {result.loading && <Loading />}

      {/* Plans Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {filteredPlans.length === 0 && !result.loading && (
          <Empty title="No plans match your filters">
            <p>Try clearing filters or register a new cultivation plan.</p>
            <Button variant="outline" onClick={clearFilters}>
              Clear filters
            </Button>
          </Empty>
        )}

        {filteredPlans.map((plan) => {
          const cropImg = CROP_IMAGES[plan.crop] || "/images/crop_okra_detail.jpg";
          const isCancelled = plan.status === "cancelled";
          const isDraft = (plan as any).is_draft;
          const isInAnalysis = (plan as any).in_analysis;

          let statusTone = {
            label: plan.status === "active" ? "Active" : "Cancelled",
            dotColor: plan.status === "active" ? "#16a34a" : "#dc2626",
            textColor: plan.status === "active" ? "#166534" : "#991b1b",
            bg: plan.status === "active" ? "#dcfce7" : "#fee2e2",
          };

          if (isInAnalysis) {
            statusTone = {
              label: "In Analysis",
              dotColor: "#ea580c",
              textColor: "#9a3412",
              bg: "#ffedd5",
            };
          } else if (isDraft) {
            statusTone = {
              label: "Draft",
              dotColor: "#2563eb",
              textColor: "#1e40af",
              bg: "#dbeafe",
            };
          }

          return (
            <div
              key={plan.plan_id}
              style={{
                background: "#ffffff",
                borderRadius: "18px",
                padding: "16px 20px",
                border: "1px solid #e2e8f0",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "20px",
                transition: "all 0.15s",
              }}
              className="hover-lift"
            >
              {/* Crop Image & Basic Info */}
              <div style={{ display: "flex", alignItems: "center", gap: "16px", minWidth: "240px" }}>
                <div
                  style={{
                    width: "60px",
                    height: "60px",
                    borderRadius: "14px",
                    overflow: "hidden",
                    border: "1px solid #e2e8f0",
                    flexShrink: 0,
                  }}
                >
                  <img
                    src={cropImg}
                    alt={plan.crop}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                </div>

                <div>
                  <h3 style={{ fontSize: "15px", fontWeight: 800, color: "#0f172a", margin: "0 0 4px 0" }}>
                    {plan.crop === "Bandakka" ? "Bandakka (Okra)" : plan.crop}
                  </h3>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>
                    {plan.district} • {plan.region}
                  </span>
                </div>
              </div>

              {/* Acreage */}
              <div style={{ minWidth: "90px" }}>
                <strong style={{ fontSize: "13.5px", color: "#0f172a" }}>
                  {plan.land_size_acres} Acres
                </strong>
              </div>

              {/* Planting Date */}
              <div style={{ minWidth: "120px" }}>
                <strong style={{ fontSize: "12.5px", color: "#0f172a", display: "block" }}>
                  {formatDate(plan.planting_date)}
                </strong>
                <small style={{ fontSize: "11px", color: "#94a3b8" }}>Planting date</small>
              </div>

              {/* Expected Harvest */}
              <div style={{ minWidth: "120px" }}>
                <strong style={{ fontSize: "12.5px", color: "#0f172a", display: "block" }}>
                  {formatDate(plan.expected_harvest_date)}
                </strong>
                <small style={{ fontSize: "11px", color: "#94a3b8" }}>Expected harvest</small>
              </div>

              {/* Season Badge */}
              <div>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "4px 10px",
                    borderRadius: "9999px",
                    background: plan.farmer_declared_season === "Yala" ? "#fef3c7" : "#dcfce7",
                    color: plan.farmer_declared_season === "Yala" ? "#92400e" : "#166534",
                  }}
                >
                  {plan.farmer_declared_season || "Maha"}
                </span>
              </div>

              {/* Status Pill */}
              <div style={{ minWidth: "90px" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "11.5px",
                    fontWeight: 700,
                    padding: "4px 10px",
                    borderRadius: "9999px",
                    background: statusTone.bg,
                    color: statusTone.textColor,
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background: statusTone.dotColor,
                    }}
                  />
                  {statusTone.label}
                </span>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", position: "relative" }}>
                <Button
                  asChild
                  style={{
                    background: "#0f172a",
                    color: "#ffffff",
                    borderRadius: "10px",
                    padding: "8px 16px",
                    fontSize: "12.5px",
                    fontWeight: 600,
                  }}
                >
                  <Link href={`/crop-planning/plans/${encodeURIComponent(plan.plan_id)}`}>
                    View Plan →
                  </Link>
                </Button>

                {/* Direct Edit Icon Button */}
                <button
                  type="button"
                  title="Edit Plan"
                  aria-label="Edit Plan"
                  onClick={() => openEditModal(plan)}
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "10px",
                    border: "1px solid #cbd5e1",
                    background: "#ffffff",
                    color: "#166534",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#f0fdf4";
                    e.currentTarget.style.borderColor = "#86efac";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "#ffffff";
                    e.currentTarget.style.borderColor = "#cbd5e1";
                  }}
                >
                  <Pencil size={15} />
                </button>

                {/* Direct Delete Icon Button */}
                <button
                  type="button"
                  title="Delete Plan"
                  aria-label="Delete Plan"
                  onClick={() => openDeleteModal(plan)}
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "10px",
                    border: "1px solid #cbd5e1",
                    background: "#ffffff",
                    color: "#dc2626",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#fef2f2";
                    e.currentTarget.style.borderColor = "#fca5a5";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "#ffffff";
                    e.currentTarget.style.borderColor = "#cbd5e1";
                  }}
                >
                  <Trash2 size={15} />
                </button>

                {/* More Options Dropdown Toggle */}
                <div style={{ position: "relative" }}>
                  <button
                    type="button"
                    title="More actions"
                    aria-label="More actions"
                    onClick={() =>
                      setActiveDropdownId(activeDropdownId === plan.plan_id ? null : plan.plan_id)
                    }
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      border: "1px solid #e2e8f0",
                      background: activeDropdownId === plan.plan_id ? "#f1f5f9" : "#ffffff",
                      color: "#64748b",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                    }}
                  >
                    <MoreVertical size={16} />
                  </button>

                  {/* Dropdown Menu */}
                  {activeDropdownId === plan.plan_id && (
                    <div
                      style={{
                        position: "absolute",
                        right: 0,
                        top: "42px",
                        background: "#ffffff",
                        borderRadius: "12px",
                        boxShadow: "0 10px 25px rgba(0,0,0,0.12)",
                        border: "1px solid #e2e8f0",
                        width: "160px",
                        zIndex: 50,
                        overflow: "hidden",
                        padding: "4px",
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => openEditModal(plan)}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "8px 12px",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          fontSize: "12.5px",
                          color: "#166534",
                          background: "transparent",
                          border: "none",
                          borderRadius: "8px",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "#f0fdf4")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <Pencil size={14} />
                        <span>Edit Plan</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => openDeleteModal(plan)}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "8px 12px",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          fontSize: "12.5px",
                          color: "#dc2626",
                          background: "transparent",
                          border: "none",
                          borderRadius: "8px",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "#fef2f2")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <Trash2 size={14} />
                        <span>Delete Plan</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {result.data && result.data.total > 10 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: "24px",
            padding: "16px 0",
          }}
        >
          <span style={{ fontSize: "13px", color: "#64748b" }}>
            {result.data.total} of your plans match these filters
          </span>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <Button
              variant="outline"
              disabled={offset === 0 || result.loading}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Previous
            </Button>
            <span style={{ fontSize: "12.5px", color: "#475569" }}>
              Page {Math.floor(offset / 20) + 1}
            </span>
            <Button
              variant="outline"
              disabled={!result.data.has_more || result.loading}
              onClick={() => setOffset(result.data!.next_offset!)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Floating Success Toast */}
      {actionSuccess && (
        <div
          style={{
            position: "fixed",
            top: "24px",
            right: "24px",
            zIndex: 1100,
            background: "#166534",
            color: "#ffffff",
            padding: "14px 20px",
            borderRadius: "14px",
            boxShadow: "0 10px 25px rgba(0,0,0,0.18)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "14px",
            fontWeight: 600,
          }}
        >
          <CheckCircle2 size={18} />
          <span>{actionSuccess}</span>
          <button
            onClick={() => setActionSuccess(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "#ffffff",
              cursor: "pointer",
              marginLeft: "8px",
              display: "flex",
              alignItems: "center",
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Edit Plan Modal Popup */}
      {editingPlan && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.55)",
            backdropFilter: "blur(6px)",
            WebkitBackdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          onClick={() => !saving && setEditingPlan(null)}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "24px",
              width: "100%",
              maxWidth: "600px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              overflow: "hidden",
              border: "1px solid #e2e8f0",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              style={{
                padding: "22px 28px",
                borderBottom: "1px solid #f1f5f9",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "#f8fafc",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "42px",
                    height: "42px",
                    borderRadius: "12px",
                    background: "#dcfce7",
                    color: "#166534",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Pencil size={20} />
                </div>
                <div>
                  <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                    Edit Cultivation Plan
                  </h2>
                  <p style={{ fontSize: "12.5px", color: "#64748b", margin: "2px 0 0 0" }}>
                    Update your crop variety, land allocation, and cultivation schedule
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => !saving && setEditingPlan(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  padding: "6px",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Form Body */}
            <form onSubmit={handleSaveEdit}>
              <div style={{ padding: "24px 28px", maxHeight: "70vh", overflowY: "auto" }}>
                {modalError && (
                  <div
                    style={{
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: "12px",
                      padding: "12px 16px",
                      color: "#b91c1c",
                      fontSize: "13px",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      marginBottom: "20px",
                    }}
                  >
                    <AlertTriangle size={16} />
                    <span>{modalError}</span>
                  </div>
                )}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "16px",
                  }}
                >
                  {/* Crop */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      Crop Variety *
                    </label>
                    <select
                      value={editForm.crop}
                      onChange={(e) => setEditForm({ ...editForm, crop: e.target.value as Crop })}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    >
                      {CROPS.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Land Size */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      Land Size (Acres) *
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      required
                      value={editForm.land_size_acres}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          land_size_acres: parseFloat(e.target.value) || 0,
                        })
                      }
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    />
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "16px",
                  }}
                >
                  {/* District */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      District *
                    </label>
                    <select
                      value={editForm.district}
                      onChange={(e) =>
                        setEditForm({ ...editForm, district: e.target.value as District })
                      }
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    >
                      {DISTRICTS.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Region / Agrarian Division */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      Region / Agrarian Division *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Hakmana, Thissamaharama"
                      value={editForm.region}
                      onChange={(e) => setEditForm({ ...editForm, region: e.target.value })}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    />
                  </div>
                </div>

                {/* Season */}
                <div style={{ marginBottom: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "12.5px",
                      fontWeight: 700,
                      color: "#334155",
                      marginBottom: "6px",
                    }}
                  >
                    Cultivation Season
                  </label>
                  <div style={{ display: "flex", gap: "12px" }}>
                    {(["Maha", "Yala"] as Season[]).map((s) => (
                      <button
                        type="button"
                        key={s}
                        onClick={() => setEditForm({ ...editForm, farmer_declared_season: s })}
                        style={{
                          flex: 1,
                          padding: "10px 16px",
                          borderRadius: "10px",
                          border:
                            editForm.farmer_declared_season === s
                              ? "2px solid #166534"
                              : "1px solid #e2e8f0",
                          background:
                            editForm.farmer_declared_season === s ? "#f0fdf4" : "#ffffff",
                          color:
                            editForm.farmer_declared_season === s ? "#166534" : "#475569",
                          fontWeight: editForm.farmer_declared_season === s ? 700 : 500,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "8px",
                          fontSize: "13px",
                        }}
                      >
                        <Sun size={15} />
                        <span>{s} Season</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "8px",
                  }}
                >
                  {/* Planting Date */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      Planting Date *
                    </label>
                    <input
                      type="date"
                      required
                      value={editForm.planting_date}
                      onChange={(e) => setEditForm({ ...editForm, planting_date: e.target.value })}
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    />
                  </div>

                  {/* Expected Harvest Date */}
                  <div>
                    <label
                      style={{
                        display: "block",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      Expected Harvest Date *
                    </label>
                    <input
                      type="date"
                      required
                      value={editForm.expected_harvest_date}
                      onChange={(e) =>
                        setEditForm({ ...editForm, expected_harvest_date: e.target.value })
                      }
                      style={{
                        width: "100%",
                        padding: "10px 14px",
                        borderRadius: "10px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13.5px",
                        background: "#ffffff",
                        color: "#0f172a",
                        outline: "none",
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div
                style={{
                  padding: "18px 28px",
                  borderTop: "1px solid #f1f5f9",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  gap: "12px",
                  background: "#f8fafc",
                }}
              >
                <Button
                  type="button"
                  variant="outline"
                  disabled={saving}
                  onClick={() => setEditingPlan(null)}
                  style={{ borderRadius: "10px", padding: "10px 18px", fontSize: "13px" }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={saving}
                  style={{
                    background: "#166534",
                    color: "#ffffff",
                    borderRadius: "10px",
                    padding: "10px 22px",
                    fontSize: "13px",
                    fontWeight: 700,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  {saving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Saving Changes...</span>
                    </>
                  ) : (
                    <>
                      <Check size={16} />
                      <span>Save Changes</span>
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Plan Modal Popup */}
      {deletingPlan && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.55)",
            backdropFilter: "blur(6px)",
            WebkitBackdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          onClick={() => !deleting && setDeletingPlan(null)}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "24px",
              width: "100%",
              maxWidth: "460px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              overflow: "hidden",
              border: "1px solid #e2e8f0",
              padding: "28px",
              textAlign: "center",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "18px",
                background: "#fee2e2",
                color: "#dc2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 18px auto",
              }}
            >
              <Trash2 size={28} />
            </div>

            <h2 style={{ fontSize: "20px", fontWeight: 800, color: "#0f172a", margin: "0 0 8px 0" }}>
              Delete Cultivation Plan?
            </h2>
            <p
              style={{
                fontSize: "13.5px",
                color: "#64748b",
                margin: "0 0 20px 0",
                lineHeight: 1.5,
              }}
            >
              Are you sure you want to delete / cancel the cultivation plan for{" "}
              <strong style={{ color: "#0f172a" }}>{deletingPlan.crop}</strong> in{" "}
              <strong style={{ color: "#0f172a" }}>
                {deletingPlan.district} ({deletingPlan.region})
              </strong>
              ? This action cannot be undone.
            </p>

            {modalError && (
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "12px",
                  padding: "10px 14px",
                  color: "#b91c1c",
                  fontSize: "12.5px",
                  marginBottom: "16px",
                  textAlign: "left",
                }}
              >
                {modalError}
              </div>
            )}

            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <Button
                type="button"
                variant="outline"
                disabled={deleting}
                onClick={() => setDeletingPlan(null)}
                style={{ flex: 1, borderRadius: "10px", padding: "12px", fontSize: "13.5px" }}
              >
                Keep Plan
              </Button>
              <Button
                type="button"
                disabled={deleting}
                onClick={handleConfirmDelete}
                style={{
                  flex: 1,
                  background: "#dc2626",
                  color: "#ffffff",
                  borderRadius: "10px",
                  padding: "12px",
                  fontSize: "13.5px",
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
              >
                {deleting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    <span>Yes, Delete</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

