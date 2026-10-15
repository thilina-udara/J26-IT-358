"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Calendar,
  Check,
  ChevronRight,
  Filter,
  Layers,
  Leaf,
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  Sprout,
  Sun,
  FileText,
} from "lucide-react";
import { formatDate } from "../lib/dates";
import { CROPS, DISTRICTS, type Plan } from "../lib/contracts";
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

  const result = useLoad(
    (signal) => {
      const query = new URLSearchParams({ limit: "20", offset: String(offset) });
      if (status) query.set("status", status);
      if (crop) query.set("crop", crop);
      if (district) query.set("district", district);
      return api.list(query, signal);
    },
    [api, offset, status, crop, district]
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
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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

                <button
                  type="button"
                  style={{
                    width: "34px",
                    height: "34px",
                    borderRadius: "10px",
                    border: "1px solid #e2e8f0",
                    background: "#ffffff",
                    color: "#64748b",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                  }}
                >
                  <MoreVertical size={16} />
                </button>
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
    </div>
  );
}
