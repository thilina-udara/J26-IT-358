"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  BarChart3,
  Calendar,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Droplets,
  FileText,
  Layers,
  Leaf,
  MapPin,
  Plus,
  PlusCircle,
  Sprout,
} from "lucide-react";
import { useSession } from "../components/session";
import { useLoad } from "../components/ui";
import { formatDate, utcToday } from "../lib/dates";

export default function DashboardPage() {
  const { api, session } = useSession();
  const result = useLoad(
    (signal) => api.list(new URLSearchParams({ limit: "10", offset: "0", status: "active" }), signal),
    [api]
  );
  const today = utcToday();
  const plans = result.data?.items ?? [];

  const farmerName = session?.farmer.login_identifier || "dinithi";

  // Calculate dynamic stats strictly from authenticated farmer's registered plans
  const distinctCropsCount = new Set(plans.map((p) => p.crop)).size;
  const totalAcres = plans.reduce((acc, p) => acc + (p.land_size_acres || 0), 0);
  const totalPlansCount = plans.length;

  // Determine greeting based on local time
  const currentHour = new Date().getHours();
  const greeting = currentHour < 12 ? "Good morning," : currentHour < 17 ? "Good afternoon," : "Good evening,";

  // Map only genuine registered farmer plans
  const displayPlans = plans.map((p) => ({
    id: p.plan_id,
    crop: p.crop,
    district: p.district,
    land_size_acres: p.land_size_acres,
    planting_date: p.planting_date,
    expected_harvest_date: p.expected_harvest_date,
    status: "Plan Registered",
    statusColor: "#15803d",
    statusBg: "#dcfce7",
    link: `/crop-planning/plans/${encodeURIComponent(p.plan_id)}`,
  }));

  return (
    <div style={{ maxWidth: "1320px", margin: "0 auto", color: "#0f172a" }}>
      {/* --------------------------------------------------------------------------
          1. WELCOME HERO BANNER (Exact Match to Image 2)
          -------------------------------------------------------------------------- */}
      <section
        style={{
          borderRadius: "24px",
          overflow: "hidden",
          position: "relative",
          marginBottom: "28px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
          background: "linear-gradient(90deg, #f7faf5 0%, #edf5e8 50%, #e1efd8 100%)",
          display: "flex",
          alignItems: "center",
          minHeight: "225px",
        }}
      >
        {/* Background Landscape Photo */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.45,
            zIndex: 0,
            pointerEvents: "none",
          }}
        >
          <img
            src="/images/dashboard_banner_landscape.jpg"
            alt="Sri Lankan agriculture landscape"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>

        {/* Left Content */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            flex: "1 1 auto",
            padding: "36px 40px",
            maxWidth: "600px",
          }}
        >
          <div style={{ fontSize: "15px", color: "#475569", fontWeight: 500, marginBottom: "4px" }}>
            {greeting}
          </div>

          <h1
            style={{
              fontSize: "36px",
              fontWeight: 800,
              color: "#0f172a",
              margin: "0 0 10px 0",
              letterSpacing: "-0.8px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            {farmerName}
            <span
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "#dcfce7",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#15803d",
              }}
            >
              <Sprout size={20} />
            </span>
          </h1>

          <p
            style={{
              fontSize: "14px",
              color: "#475569",
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            Manage your cultivation plans, check risk analysis results, explore alternative crops, and get personalized cultivation guidance.
          </p>
        </div>

        {/* Center-Right: Speech bubble quote with pointer tail */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            marginRight: "290px",
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
          }}
        >
          <div
            style={{
              background: "rgba(255, 255, 255, 0.95)",
              backdropFilter: "blur(6px)",
              padding: "14px 18px",
              borderRadius: "18px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 16px rgba(0, 0, 0, 0.05)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              maxWidth: "230px",
              position: "relative",
            }}
          >
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "#dcfce7",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Sprout size={16} />
            </div>
            <span style={{ fontSize: "11px", color: "#1e293b", fontWeight: 600, lineHeight: 1.4 }}>
              Smarter decisions today for a resilient harvest tomorrow.
            </span>
            {/* Speech bubble tail pointer pointing toward the farmer */}
            <div
              style={{
                position: "absolute",
                right: "-8px",
                top: "50%",
                transform: "translateY(-50%)",
                width: 0,
                height: 0,
                borderTop: "7px solid transparent",
                borderBottom: "7px solid transparent",
                borderLeft: "8px solid rgba(255, 255, 255, 0.95)",
              }}
            />
          </div>
        </div>

        {/* Right Content: Farmer standing in the landscape, seamlessly blended */}
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            bottom: 0,
            width: "310px",
            zIndex: 1,
            pointerEvents: "none",
            overflow: "hidden",
          }}
        >
          <img
            src="/images/hero_farmer.jpg"
            alt="Farmer using AgroDecision app"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              objectPosition: "center 12%",
              WebkitMaskImage: "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.5) 18%, black 45%, black 100%)",
              maskImage: "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.5) 18%, black 45%, black 100%)",
            }}
          />
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          2. STATS OVERVIEW CARDS (4 Cards Row matching Image 2)
          -------------------------------------------------------------------------- */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "20px",
          marginBottom: "28px",
        }}
      >
        {/* Card 1: Total Cultivation Plans */}
        <Link
          href="/crop-planning/plans"
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "22px 24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.02)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "all 0.2s",
          }}
          className="hover-lift"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "14px",
                background: "#eaf5ea",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <FileText size={22} />
            </div>
            <div>
              <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#64748b", display: "block" }}>
                Total Cultivation Plans
              </span>
              <strong style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", lineHeight: 1.15 }}>
                {totalPlansCount}
              </strong>
              <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                Your registered plans
              </small>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#94a3b8" }} />
        </Link>

        {/* Card 2: Crops Grown */}
        <Link
          href="/crop-planning/suggested-crops"
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "22px 24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.02)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "all 0.2s",
          }}
          className="hover-lift"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "14px",
                background: "#eaf5ea",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Sprout size={22} />
            </div>
            <div>
              <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#64748b", display: "block" }}>
                Crops Grown
              </span>
              <strong style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", lineHeight: 1.15 }}>
                {distinctCropsCount}
              </strong>
              <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                Different crop varieties
              </small>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#94a3b8" }} />
        </Link>

        {/* Card 3: Total Land Size */}
        <Link
          href="/crop-planning/plans"
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "22px 24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.02)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "all 0.2s",
          }}
          className="hover-lift"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "14px",
                background: "#eaf5ea",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Layers size={22} />
            </div>
            <div>
              <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#64748b", display: "block" }}>
                Total Land Size
              </span>
              <strong style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", lineHeight: 1.15 }}>
                {typeof totalAcres === "number" ? totalAcres.toFixed(1) : totalAcres}
              </strong>
              <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                Acres in your plans
              </small>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#94a3b8" }} />
        </Link>

        {/* Card 4: Upcoming Activities */}
        <Link
          href="/crop-planning/plans"
          style={{
            background: "#ffffff",
            borderRadius: "20px",
            padding: "22px 24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.02)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "all 0.2s",
          }}
          className="hover-lift"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "14px",
                background: "#eaf5ea",
                color: "#15803d",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <CalendarDays size={22} />
            </div>
            <div>
              <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#64748b", display: "block" }}>
                Upcoming Activities
              </span>
              <strong style={{ fontSize: "28px", fontWeight: 800, color: "#0f172a", lineHeight: 1.15 }}>
                2
              </strong>
              <small style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginTop: "2px" }}>
                Next 30 days
              </small>
            </div>
          </div>
          <ChevronRight size={18} style={{ color: "#94a3b8" }} />
        </Link>
      </section>

      {/* --------------------------------------------------------------------------
          3. QUICK ACTIONS (Matching Image 2)
          -------------------------------------------------------------------------- */}
      <section style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
            Quick Actions
          </h2>
          <Link
            href="/crop-planning/plans/new"
            style={{ fontSize: "13px", fontWeight: 700, color: "#15803d", display: "flex", alignItems: "center", gap: "4px" }}
          >
            Start a new plan <ArrowRight size={14} />
          </Link>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" }}>
          {/* Action 1: New Cultivation Plan */}
          <Link
            href="/crop-planning/plans/new"
            style={{
              background: "#f0fdf4",
              borderRadius: "18px",
              padding: "20px",
              border: "1px solid #dcfce7",
              boxShadow: "0 2px 6px rgba(0,0,0,0.02)",
              display: "flex",
              alignItems: "center",
              gap: "14px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            className="hover-lift"
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "12px",
                background: "#16a34a",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <PlusCircle size={22} />
            </div>
            <div>
              <strong style={{ fontSize: "14px", color: "#0f172a", display: "block" }}>
                New Cultivation Plan
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>Register a new crop plan</small>
            </div>
          </Link>

          {/* Action 2: Analyze Risk */}
          <Link
            href="/crop-planning/risk-analysis"
            style={{
              background: "#eff6ff",
              borderRadius: "18px",
              padding: "20px",
              border: "1px solid #dbeafe",
              boxShadow: "0 2px 6px rgba(0,0,0,0.02)",
              display: "flex",
              alignItems: "center",
              gap: "14px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            className="hover-lift"
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "12px",
                background: "#2563eb",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <BarChart3 size={22} />
            </div>
            <div>
              <strong style={{ fontSize: "14px", color: "#0f172a", display: "block" }}>
                Analyze Risk
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>Check concentration risk</small>
            </div>
          </Link>

          {/* Action 3: Suggested Crops */}
          <Link
            href="/crop-planning/suggested-crops"
            style={{
              background: "#fffbeb",
              borderRadius: "18px",
              padding: "20px",
              border: "1px solid #fef3c7",
              boxShadow: "0 2px 6px rgba(0,0,0,0.02)",
              display: "flex",
              alignItems: "center",
              gap: "14px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            className="hover-lift"
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "12px",
                background: "#d97706",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Leaf size={22} />
            </div>
            <div>
              <strong style={{ fontSize: "14px", color: "#0f172a", display: "block" }}>
                Suggested Crops
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>Explore alternative crops</small>
            </div>
          </Link>

          {/* Action 4: Register New Plan */}
          <Link
            href="/crop-planning/plans"
            style={{
              background: "#faf5ff",
              borderRadius: "18px",
              padding: "20px",
              border: "1px solid #f3e8ff",
              boxShadow: "0 2px 6px rgba(0,0,0,0.02)",
              display: "flex",
              alignItems: "center",
              gap: "14px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            className="hover-lift"
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "12px",
                background: "#7c3aed",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Calendar size={22} />
            </div>
            <div>
              <strong style={{ fontSize: "14px", color: "#0f172a", display: "block" }}>
                Add New Plan
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>Register seasonal intention</small>
            </div>
          </Link>
        </div>
      </section>

      {/* --------------------------------------------------------------------------
          4. TWO-COLUMN LOWER SECTION (Recent Plans + Activities & Insights)
          -------------------------------------------------------------------------- */}
      <section style={{ display: "grid", gridTemplateColumns: "1.85fr 1.15fr", gap: "24px" }}>
        
        {/* Left Column: Recent Cultivation Plans Table */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "22px",
            padding: "24px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <h3 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
              Recent Cultivation Plans
            </h3>
            <Link
              href="/crop-planning/plans"
              style={{ fontSize: "12.5px", fontWeight: 700, color: "#15803d", display: "flex", alignItems: "center", gap: "4px" }}
            >
              View all plans <ArrowRight size={13} />
            </Link>
          </div>

          {/* Plans Table */}
          {displayPlans.length === 0 ? (
            <div style={{ textAlign: "center", padding: "36px 20px", color: "#64748b" }}>
              <Sprout size={36} style={{ margin: "0 auto 10px", color: "#94a3b8" }} />
              <strong style={{ fontSize: "14px", color: "#1e293b", display: "block" }}>
                No registered cultivation plans yet
              </strong>
              <p style={{ fontSize: "12.5px", margin: "4px 0 16px 0", color: "#64748b" }}>
                Register an upcoming cultivation plan to monitor regional concentration.
              </p>
              <Link
                href="/crop-planning/plans/new"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 16px",
                  borderRadius: "10px",
                  background: "#15803d",
                  color: "#ffffff",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  textDecoration: "none",
                }}
              >
                <Plus size={14} />
                <span>Create first plan</span>
              </Link>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
                <thead>
                  <tr style={{ background: "#f8fafc", color: "#64748b" }}>
                    <th style={{ padding: "12px 14px", fontWeight: 600, borderTopLeftRadius: "10px", borderBottomLeftRadius: "10px" }}>Crop</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600 }}>District</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600 }}>Land Size</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600 }}>Planting Date</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600 }}>Expected Harvest</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "12px 14px", fontWeight: 600, textAlign: "right", borderTopRightRadius: "10px", borderBottomRightRadius: "10px" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {displayPlans.map((plan) => (
                    <tr
                      key={plan.id}
                      style={{
                        borderBottom: "1px solid #f8fafc",
                        transition: "background 0.15s",
                      }}
                    >
                      <td style={{ padding: "14px 14px", fontWeight: 700, color: "#0f172a" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ color: "#15803d" }}>🌱</span>
                          {plan.crop}
                        </span>
                      </td>
                      <td style={{ padding: "14px 14px", color: "#475569" }}>{plan.district}</td>
                      <td style={{ padding: "14px 14px", color: "#475569" }}>{plan.land_size_acres} ac</td>
                      <td style={{ padding: "14px 14px", color: "#475569" }}>{formatDate(plan.planting_date)}</td>
                      <td style={{ padding: "14px 14px", color: "#475569" }}>{formatDate(plan.expected_harvest_date)}</td>
                      <td style={{ padding: "14px 14px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "4px 12px",
                            borderRadius: "9999px",
                            backgroundColor: plan.statusBg,
                            color: plan.statusColor,
                            display: "inline-block",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {plan.status}
                        </span>
                      </td>
                      <td style={{ padding: "14px 14px", textAlign: "right" }}>
                        <Link
                          href={plan.link}
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            color: "#334155",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "3px",
                            textDecoration: "none",
                          }}
                        >
                          View <ChevronRight size={13} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ background: "#ffffff", borderRadius: "22px", padding: "24px", border: "1px solid #e2e8f0" }}>
            <h3>Approved activities for your plan</h3>
            <p>Choose a saved cultivation plan to view activities supported by applicable approval evidence. No activity reminder is inferred from your planting date.</p>
            <Link href="/crop-planning/plans">Open farm plans</Link>
          </div>
          <div style={{ background: "#f0fdf4", borderRadius: "22px", padding: "24px" }}>
            <h3>Your saved intentions</h3>
            <p>Review your own records and their actual planning context before requesting agricultural guidance.</p>
            <Link href="/crop-planning/plans">View your plans</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
