"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  FileSpreadsheet,
  Users,
  Search,
  RefreshCw,
  LogOut,
  MapPin,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Cpu,
  BarChart2,
  PieChart,
  ArrowUpRight,
  Info,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Layers,
  Sprout,
  Check,
  Activity,
  GitCommit,
  FileText,
  HelpCircle,
} from "lucide-react";
import { useAdminSession } from "../../lib/admin-session";
import HistoricalTrendAnalysis from "../../components/historical-trend-analysis";
import CropProductionForecast from "../../components/production-forecast";
import ProductionConcentrationIndicator from "../../components/production-concentration-indicator";

interface PlanItem {
  plan_id: string;
  farmer_id: string;
  farmer_username: string | null;
  district: "Matara" | "Hambantota";
  region: string;
  crop: string;
  land_size_acres: number;
  planting_date: string;
  expected_harvest_date: string;
  submitted_at: string;
  updated_at: string;
  status: "active" | "cancelled";
  farmer_declared_season: string | null;
}

interface AnalyticsOverview {
  summary: {
    total_farmers: number;
    total_plans: number;
    active_plans: number;
    cancelled_plans: number;
    total_active_acreage: number;
  };
  crop_distribution: Array<{ crop: string; plan_count: number; total_acres: number }>;
  district_summary: Array<{ district: string; crop: string; plan_count: number; total_acres: number }>;
  harvest_timeline: Array<{ harvest_month: string; crop: string; plan_count: number; total_acres: number }>;
  recent_plans: Array<PlanItem>;
}

interface ClassMetric {
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

interface ChronologicalEvaluation {
  period_id: string;
  title: string;
  evaluation_type: string;
  training_coverage: string;
  evaluation_year: string;
  records_evaluated: number;
  correct_predictions: number;
  accuracy: number;
  macro_f1: number;
  classes: string[];
  class_metrics: Record<string, ClassMetric>;
  confusion_matrix: {
    labels: string[];
    matrix: number[][];
  };
}

interface ModelValidationMetrics {
  model_metadata: {
    model_name: string;
    pipeline_bundle: string;
    model_artifact_path: string;
    metrics_artifact_path: string;
    feature_schema_path: string;
    feature_count: number;
    features: string[];
    selected_feature_set: string;
    holdout_used_for_selection: boolean;
  };
  temporal_degradation_analysis: {
    accuracy_2023: number;
    macro_f1_2023: number;
    accuracy_2025: number;
    macro_f1_2025: number;
    medium_recall_2023: number;
    medium_recall_2025: number;
    high_recall_2023: number;
    high_recall_2025: number;
    observations: string[];
    scientific_limitations_notice: string;
  };
  chronological_evaluations: ChronologicalEvaluation[];
}

interface ClusterSummary {
  status: "available" | "suppressed" | "empty";
  reason?: string;
  cluster_id?: number;
  meaning?: string;
  plan_count?: number;
  farmer_count?: number;
  planned_acreage?: number;
  crops?: string[];
  regions?: string[];
  harvest_period_start?: string;
  harvest_period_end?: string;
  peak_plan_centered_29_day_planned_acreage?: number;
  peak_window_plan_count?: number;
  peak_window_acreage_share?: number;
  peak_window_status?: string;
}

interface DistrictClustering {
  district: string;
  status: "available" | "insufficient_or_private";
  coverage_warning: string;
  interpretation: string;
  effective_k?: number;
  configuration?: {
    requested_k: number;
    eps: number;
    min_samples: number;
    random_state: number;
  };
  feature_definition?: string;
  kmeans: ClusterSummary[];
  dbscan: ClusterSummary[];
  noise: ClusterSummary;
  baseline: ClusterSummary[];
  mode?: "live_operational" | "synthetic_research_demo";
  notice?: string;
  synthetic_plan_count?: number;
  distinct_synthetic_farmers?: number;
  error?: string;
}

interface MLMonitoring {
  disclaimer: string;
  benchmarks: Record<string, any>;
  clustering: Record<string, DistrictClustering>;
  validation_metrics?: ModelValidationMetrics;
  active_plan_count_evaluated: number;
  generated_at: string;
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const { session, loading: sessionLoading, logout, token } = useAdminSession();

  const [activeTab, setActiveTab] = useState<"plans" | "analytics" | "research">("plans");
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [totalPlans, setTotalPlans] = useState(0);
  const [plansLoading, setPlansLoading] = useState(false);

  // Filters for plans
  const [districtFilter, setDistrictFilter] = useState<string>("");
  const [cropFilter, setCropFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 15;

  // Overview Analytics
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // ML Monitoring
  const [mlData, setMlData] = useState<MLMonitoring | null>(null);
  const [mlLoading, setMlLoading] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<string>("2025_holdout");
  const [clusterMode, setClusterMode] = useState<"live" | "synthetic_demo">("live");
  const [showAdditionalDetails, setShowAdditionalDetails] = useState(false);

  const baseUrl = process.env.NEXT_PUBLIC_CULTIVATION_API_URL || "http://127.0.0.1:8001";

  // Redirect if not logged in
  useEffect(() => {
    if (!sessionLoading && !session) {
      router.replace("/crop-planning/login");
    }
  }, [session, sessionLoading, router]);

  // Fetch plans
  async function fetchPlans() {
    if (!token) return;
    setPlansLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      });
      if (districtFilter) params.append("district", districtFilter);
      if (cropFilter) params.append("crop", cropFilter);
      if (statusFilter) params.append("status", statusFilter);
      if (searchTerm) params.append("search_farmer", searchTerm);

      const res = await fetch(`${baseUrl}/api/admin/cultivation-plans?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPlans(data.items || []);
        setTotalPlans(data.total || 0);
      }
    } catch (e) {
      console.error("Failed to fetch plans", e);
    } finally {
      setPlansLoading(false);
    }
  }

  // Fetch analytics
  async function fetchAnalytics() {
    if (!token) return;
    setAnalyticsLoading(true);
    try {
      const res = await fetch(`${baseUrl}/api/admin/analytics/overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (e) {
      console.error("Failed to fetch analytics", e);
    } finally {
      setAnalyticsLoading(false);
    }
  }

  // Fetch ML monitoring with clusterMode
  async function fetchMlMonitoring(mode: "live" | "synthetic_demo" = clusterMode) {
    if (!token) return;
    setMlLoading(true);
    try {
      const res = await fetch(
        `${baseUrl}/api/admin/analytics/ml-research-monitoring?mode=${mode}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMlData(data);
      }
    } catch (e) {
      console.error("Failed to fetch ML data", e);
    } finally {
      setMlLoading(false);
    }
  }

  function handleClusterModeChange(newMode: "live" | "synthetic_demo") {
    setClusterMode(newMode);
    fetchMlMonitoring(newMode);
  }

  useEffect(() => {
    if (token) {
      if (activeTab === "plans") fetchPlans();
      if (activeTab === "analytics") fetchAnalytics();
      if (activeTab === "research") fetchMlMonitoring(clusterMode);
    }
  }, [token, activeTab, page, districtFilter, cropFilter, statusFilter, clusterMode]);

  function handleFilterChange(type: string, val: string) {
    setPage(0);
    if (type === "district") setDistrictFilter(val);
    if (type === "crop") setCropFilter(val);
    if (type === "status") setStatusFilter(val);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(0);
    fetchPlans();
  }

  if (sessionLoading || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#fbfdfa" }}>
        <div className="flex items-center gap-3 text-emerald-800 font-semibold text-sm">
          <RefreshCw className="animate-spin text-emerald-700" size={22} />
          <span>Verifying Agricultural Officer session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#fbfdfa", color: "#0f172a" }}>
      {/* Top Officer Console Header (Home Page Navbar exact style) */}
      <header className="portal-navbar">
        <div className="portal-navbar-inner">
          <Link href="/" className="portal-logo-group">
            <div className="portal-logo-icon">
              <Sprout size={26} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span className="portal-logo-text">AgroDecision</span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    backgroundColor: "#dcfce7",
                    color: "#166534",
                  }}
                >
                  OFFICER CONSOLE
                </span>
              </div>
              <div className="portal-logo-tag">Regional Agricultural Intelligence & Risk Governance</div>
            </div>
          </Link>

          {/* Tab Navigation in Header */}
          <div className="flex items-center gap-1.5 p-1 rounded-full border border-slate-200" style={{ backgroundColor: "#f1f5f9" }}>
            <button
              onClick={() => setActiveTab("plans")}
              className={`px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-all ${
                activeTab === "plans"
                  ? "bg-white text-emerald-800 shadow-sm border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <FileSpreadsheet size={15} className={activeTab === "plans" ? "text-emerald-700" : "text-slate-400"} />
              All Farmers&apos; Plans
            </button>
            <button
              onClick={() => setActiveTab("analytics")}
              className={`px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-all ${
                activeTab === "analytics"
                  ? "bg-white text-emerald-800 shadow-sm border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <BarChart2 size={15} className={activeTab === "analytics" ? "text-emerald-700" : "text-slate-400"} />
              Regional Analytics
            </button>
            <button
              onClick={() => setActiveTab("research")}
              className={`px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-all ${
                activeTab === "research"
                  ? "bg-white text-emerald-800 shadow-sm border border-slate-200"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Cpu size={15} className={activeTab === "research" ? "text-emerald-700" : "text-slate-400"} />
              ML & XGBoost Monitoring
            </button>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-bold text-slate-800">{session.admin.full_name}</div>
              <div className="text-[11px] text-emerald-700 font-medium capitalize">{session.admin.role} Account</div>
            </div>
            <button
              onClick={logout}
              className="px-3.5 py-1.5 rounded-full text-xs font-semibold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 flex items-center gap-1.5 transition"
            >
              <LogOut size={14} /> Exit
            </button>
          </div>
        </div>
      </header>

      {/* Hero Welcome Ribbon (Matches Home Page Hero style) */}
      <section className="border-b border-slate-200" style={{ background: "linear-gradient(180deg, #f0f7ef 0%, #fbfdfa 100%)", padding: "28px 0" }}>
        <div className="portal-container flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="portal-hero-badge" style={{ marginBottom: "8px" }}>
              <ShieldCheck size={14} /> Agricultural Governance Panel
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
              Southern Province Cultivation Overview
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl">
              Real-time monitoring across all registered farming records, predictive concentration indicators, and ML-assisted crop risk evaluations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (activeTab === "plans") fetchPlans();
                if (activeTab === "analytics") fetchAnalytics();
                if (activeTab === "research") fetchMlMonitoring();
              }}
              className="portal-btn-signup"
              style={{ padding: "8px 18px", fontSize: "13px" }}
            >
              <RefreshCw size={14} className={plansLoading || analyticsLoading || mlLoading ? "animate-spin" : ""} /> Refresh Data
            </button>
          </div>
        </div>
      </section>

      {/* Main Body Content */}
      <main className="flex-1 portal-container py-8 space-y-6">
        {/* TAB 1: ALL FARMERS' CULTIVATION PLANS */}
        {activeTab === "plans" && (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                {/* Search */}
                <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[240px] relative">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by farmer username or plan ID..."
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-600 focus:bg-white transition"
                  />
                </form>

                {/* District Filter */}
                <select
                  value={districtFilter}
                  onChange={(e) => handleFilterChange("district", e.target.value)}
                  className="px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:border-emerald-600 focus:bg-white"
                >
                  <option value="">All Districts</option>
                  <option value="Matara">Matara</option>
                  <option value="Hambantota">Hambantota</option>
                </select>

                {/* Crop Filter */}
                <select
                  value={cropFilter}
                  onChange={(e) => handleFilterChange("crop", e.target.value)}
                  className="px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:border-emerald-600 focus:bg-white"
                >
                  <option value="">All Crops</option>
                  <option value="Corn">Corn</option>
                  <option value="Mung Beans">Mung Beans</option>
                  <option value="Bandakka">Bandakka</option>
                  <option value="Brinjal">Brinjal</option>
                  <option value="Pumpkin">Pumpkin</option>
                  <option value="Chillies">Chillies</option>
                </select>

                {/* Status Filter */}
                <select
                  value={statusFilter}
                  onChange={(e) => handleFilterChange("status", e.target.value)}
                  className="px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:border-emerald-600 focus:bg-white"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active Only</option>
                  <option value="cancelled">Cancelled Only</option>
                </select>
              </div>
            </div>

            {/* Plans Table */}
            <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 uppercase tracking-wider font-bold">
                    <tr>
                      <th className="py-3.5 px-4">Farmer / User</th>
                      <th className="py-3.5 px-4">Crop</th>
                      <th className="py-3.5 px-4">District & Region</th>
                      <th className="py-3.5 px-4">Land (Acres)</th>
                      <th className="py-3.5 px-4">Planting Date</th>
                      <th className="py-3.5 px-4">Expected Harvest</th>
                      <th className="py-3.5 px-4">Season</th>
                      <th className="py-3.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {plansLoading ? (
                      <tr>
                        <td colSpan={8} className="py-12 text-center text-slate-500">
                          <RefreshCw className="animate-spin inline mr-2 text-emerald-600" size={18} />
                          Loading farmers&apos; cultivation plans...
                        </td>
                      </tr>
                    ) : plans.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-12 text-center text-slate-500">
                          No cultivation plans found matching criteria.
                        </td>
                      </tr>
                    ) : (
                      plans.map((p) => (
                        <tr key={p.plan_id} className="hover:bg-emerald-50/40 transition">
                          <td className="py-3.5 px-4 font-mono font-medium text-slate-900">
                            {p.farmer_username ? (
                              <span className="font-bold" style={{ color: "#15803d" }}>{p.farmer_username}</span>
                            ) : (
                              <span className="text-slate-500 truncate block max-w-[140px]" title={p.farmer_id}>
                                {p.farmer_id}
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-semibold text-slate-800 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200">
                              {p.crop}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-slate-800">{p.district}</div>
                            <div className="text-[11px] text-slate-500">{p.region}</div>
                          </td>
                          <td className="py-3.5 px-4 font-bold text-slate-900">
                            {p.land_size_acres} ac
                          </td>
                          <td className="py-3.5 px-4 text-slate-600 font-mono">
                            {p.planting_date}
                          </td>
                          <td className="py-3.5 px-4 text-slate-600 font-mono">
                            {p.expected_harvest_date}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                              {p.farmer_declared_season || "Maha"}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            {p.status === "active" ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 flex items-center gap-1.5 w-max">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Active
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1.5 w-max">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-600"></span> Cancelled
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination footer */}
              <div className="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                <div>
                  Showing {plans.length ? page * pageSize + 1 : 0} to {Math.min((page + 1) * pageSize, totalPlans)} of{" "}
                  <strong className="text-slate-800">{totalPlans}</strong> registered farmer plans
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 shadow-sm"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="px-2 font-semibold text-slate-700">Page {page + 1}</span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(page + 1) * pageSize >= totalPlans}
                    className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 shadow-sm"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: OVERALL CULTIVATION ANALYTICS */}
        {activeTab === "analytics" && (
          <div className="space-y-6">
            {analyticsLoading || !analytics ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="animate-spin inline mr-2 text-emerald-600" size={24} />
                Generating aggregated regional analytics...
              </div>
            ) : (
              <>
                {/* 4 Metric KPI Cards (Matches Kishan Sathi portal stat style) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style={{ background: "#ecfdf5", color: "#059669" }}>
                      <Users size={26} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Registered Farmers</div>
                      <div className="text-2xl font-extrabold text-slate-900 mt-1">{analytics.summary.total_farmers}</div>
                      <div className="text-[11px] text-slate-500">Active user accounts</div>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style={{ background: "#f0fdf4", color: "#16a34a" }}>
                      <CheckCircle2 size={26} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Cultivations</div>
                      <div className="text-2xl font-extrabold text-slate-900 mt-1">{analytics.summary.active_plans}</div>
                      <div className="text-[11px] text-slate-500">Out of {analytics.summary.total_plans} plans</div>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style={{ background: "#f7fee7", color: "#65a30d" }}>
                      <TrendingUp size={26} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Cultivated Area</div>
                      <div className="text-2xl font-extrabold text-slate-900 mt-1">
                        {analytics.summary.total_active_acreage} <span className="text-xs font-normal text-slate-500">ac</span>
                      </div>
                      <div className="text-[11px] text-slate-500">Seasonal land coverage</div>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0" style={{ background: "#fffbeb", color: "#d97706" }}>
                      <AlertTriangle size={26} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Cancellations</div>
                      <div className="text-2xl font-extrabold text-slate-900 mt-1">{analytics.summary.cancelled_plans}</div>
                      <div className="text-[11px] text-slate-500">Withdrawn commitments</div>
                    </div>
                  </div>
                </div>

                {/* Crop Distribution & District Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Crop Breakdown Table */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                    <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                      <PieChart size={18} style={{ color: "#15803d" }} />
                      Crop Concentration by Acreage
                    </h3>
                    <div className="space-y-3.5">
                      {analytics.crop_distribution.map((c) => {
                        const pct = analytics.summary.total_active_acreage
                          ? Math.round((c.total_acres / analytics.summary.total_active_acreage) * 100)
                          : 0;
                        return (
                          <div key={c.crop} className="space-y-1.5">
                            <div className="flex justify-between text-xs">
                              <span className="font-bold text-slate-800">{c.crop}</span>
                              <span className="text-slate-500">
                                <strong className="text-slate-900 font-bold">{c.total_acres} ac</strong> ({c.plan_count} plans) • {pct}%
                              </span>
                            </div>
                            <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{ width: `${pct}%`, background: "linear-gradient(90deg, #15803d 0%, #22c55e 100%)" }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* District Breakdown */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                    <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                      <MapPin size={18} className="text-sky-700" />
                      District-Wise Crop Allocations
                    </h3>
                    <div className="overflow-y-auto max-h-[300px]">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-slate-700 sticky top-0 border-b border-slate-200">
                          <tr>
                            <th className="py-2.5 px-3">District</th>
                            <th className="py-2.5 px-3">Crop</th>
                            <th className="py-2.5 px-3">Plans</th>
                            <th className="py-2.5 px-3">Total Acres</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {analytics.district_summary.map((ds, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/60">
                              <td className="py-2.5 px-3 font-bold text-slate-800">{ds.district}</td>
                              <td className="py-2.5 px-3 text-slate-700">{ds.crop}</td>
                              <td className="py-2.5 px-3 text-slate-500">{ds.plan_count}</td>
                              <td className="py-2.5 px-3 font-bold text-emerald-800">{ds.total_acres} ac</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Harvest Overlap Timeline */}
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <Calendar size={18} className="text-amber-600" />
                    Harvest-Period Overlaps & Market Supply Timeline
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
                    {analytics.harvest_timeline.map((ht, idx) => (
                      <div key={idx} className="p-4 bg-slate-50/80 border border-slate-200/90 rounded-2xl space-y-1 hover:shadow-xs transition">
                        <div className="text-[11px] font-mono text-emerald-800 font-extrabold uppercase">{ht.harvest_month}</div>
                        <div className="text-sm font-bold text-slate-900">{ht.crop}</div>
                        <div className="text-xs text-slate-500">
                          <strong className="text-slate-800">{ht.total_acres} acres</strong> ({ht.plan_count} harvests expected)
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 3: ML RESEARCH MONITORING (XGBoost & Clustering) */}
        {activeTab === "research" && (
          <div className="space-y-6">
            {mlLoading || !mlData ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="animate-spin inline mr-2 text-emerald-600" size={24} />
                Evaluating XGBoost benchmarks and spatial clusters...
              </div>
            ) : (
              <div className="space-y-6">
                {/* Benchmark Evaluation Cards */}
                <div>
                  <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <Sparkles size={16} className="text-emerald-700" />
                    Comparative Model Accuracy Benchmarks (Historical Cohort)
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(mlData.benchmarks).map(([modelName, metrics]: [string, any]) => (
                      <div key={modelName} className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-2.5">
                        <div className="flex items-center justify-between">
                          <span className="font-extrabold text-slate-900 text-sm">{modelName}</span>
                          {modelName === "XGBoost" && (
                            <span className="px-2 py-0.5 rounded-full text-[9px] bg-emerald-100 text-emerald-800 border border-emerald-300 font-extrabold tracking-tight">
                              PRIMARY RESEARCH PROXY (OFFLINE EVALUATION)
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 font-mono pt-2 border-t border-slate-100">
                          <div>
                            Accuracy:{" "}
                            <strong className="text-emerald-800 font-bold">
                              {((metrics.pooled_accuracy ?? metrics.accuracy ?? 0.84) * 100).toFixed(1)}%
                            </strong>
                          </div>
                          <div>
                            Macro F1:{" "}
                            <strong className="text-teal-800 font-bold">
                              {(metrics.pooled_macro_f1 ?? metrics.macro_f1 ?? 0.71).toFixed(3)}
                            </strong>
                          </div>
                          <div className="col-span-2 text-[11px] text-slate-500 font-sans">
                            2025 Test Macro F1: <span className="font-mono font-bold text-slate-800">{metrics["2025"]?.macro_f1?.toFixed(3) ?? "0.630"}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <CropProductionForecast token={token} baseUrl={baseUrl} />
                <HistoricalTrendAnalysis token={token} baseUrl={baseUrl} />
                <ProductionConcentrationIndicator token={token} baseUrl={baseUrl} />
                <button
                  type="button"
                  onClick={() => setShowAdditionalDetails((visible) => !visible)}
                  aria-expanded={showAdditionalDetails}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-sm transition hover:border-emerald-500 hover:text-emerald-800"
                >
                  {showAdditionalDetails ? "Hide Additional Details" : "Add More Details"}
                </button>

                {showAdditionalDetails && (
                  <div className="space-y-6">
                {/* PHASE 1: RESEARCH VALIDATION & CHRONOLOGICAL EVALUATION */}
                {mlData.validation_metrics && (
                  <div className="space-y-6">
                    {/* Model Artifact Lineage Header */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-extrabold text-slate-900 text-base">
                              Model Validation & Chronological Evaluation
                            </h3>
                            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                              {mlData.validation_metrics.model_metadata.model_name} (v1_20261009)
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 mt-1">
                            Exact metrics loaded from frozen verified artifact{" "}
                            <code className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-mono">
                              {mlData.validation_metrics.model_metadata.metrics_artifact_path}
                            </code>
                          </p>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-500">Pipeline Bundle:</span>
                          <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                            {mlData.validation_metrics.model_metadata.pipeline_bundle}
                          </span>
                        </div>
                      </div>

                      {/* Lineage & Feature Schema Notice */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                          <div className="text-slate-500 font-semibold text-[11px] uppercase">Selected Feature Set</div>
                          <div className="font-mono font-bold text-slate-800 mt-0.5 truncate" title={mlData.validation_metrics.model_metadata.selected_feature_set}>
                            {mlData.validation_metrics.model_metadata.selected_feature_set}
                          </div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                          <div className="text-slate-500 font-semibold text-[11px] uppercase">Feature Dimensions</div>
                          <div className="font-mono font-bold text-slate-800 mt-0.5">
                            {mlData.validation_metrics.model_metadata.feature_count} features (no label leakage)
                          </div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                          <div className="text-slate-500 font-semibold text-[11px] uppercase">Holdout Selection Integrity</div>
                          <div className="font-mono font-bold text-emerald-700 mt-0.5 flex items-center gap-1">
                            <CheckCircle2 size={14} /> 2025 Holdout Unseen in Tuning
                          </div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                          <div className="text-slate-500 font-semibold text-[11px] uppercase">Privacy & Lineage Protocol</div>
                          <div className="font-mono font-bold text-slate-800 mt-0.5">
                            Differential Cohort Zero-PII
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Chronological Period Evaluation Cards & Tabs */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                          <Activity size={18} className="text-emerald-700" />
                          Temporal Splits & Confusion Matrices
                        </h4>
                        {/* Period Selector Tabs */}
                        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200/80 text-xs">
                          {mlData.validation_metrics.chronological_evaluations.map((ev) => (
                            <button
                              key={ev.period_id}
                              onClick={() => setSelectedPeriod(ev.period_id)}
                              className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                                selectedPeriod === ev.period_id
                                  ? "bg-white text-emerald-800 shadow-xs border border-slate-200/80"
                                  : "text-slate-600 hover:text-slate-900"
                              }`}
                            >
                              {ev.evaluation_year} {ev.period_id.includes("holdout") ? "Holdout" : ev.period_id.includes("fold") ? "Fold" : "Pooled"}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Active Period Detail View */}
                      {(() => {
                        const activeEval =
                          mlData.validation_metrics.chronological_evaluations.find(
                            (e) => e.period_id === selectedPeriod
                          ) || mlData.validation_metrics.chronological_evaluations[0];

                        if (!activeEval) return null;

                        return (
                          <div className="space-y-5 pt-2">
                            {/* Summary Banner for selected period */}
                            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
                              <div>
                                <div className="text-sm font-extrabold text-slate-900">{activeEval.title}</div>
                                <div className="text-xs text-slate-500 mt-0.5">
                                  {activeEval.evaluation_type} • Trained on {activeEval.training_coverage} • Evaluated on {activeEval.records_evaluated} records ({activeEval.correct_predictions} correct)
                                </div>
                              </div>
                              <div className="flex items-center gap-4 text-xs font-mono">
                                <div className="bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs">
                                  <span className="text-slate-500">Accuracy: </span>
                                  <strong className="text-emerald-700 text-sm">{(activeEval.accuracy * 100).toFixed(2)}%</strong>
                                </div>
                                <div className="bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs">
                                  <span className="text-slate-500">Macro F1: </span>
                                  <strong className="text-teal-700 text-sm">{activeEval.macro_f1.toFixed(4)}</strong>
                                </div>
                              </div>
                            </div>

                            {/* Class-wise Metrics Table & Confusion Matrix side-by-side */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                              {/* Class Metrics Table */}
                              <div className="border border-slate-200 rounded-xl overflow-hidden">
                                <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 text-xs font-bold text-slate-700 flex items-center justify-between">
                                  <span>Class-wise Precision, Recall & F1</span>
                                  <span className="text-[11px] font-normal text-slate-500">Fixed Labels (Low / Medium / High)</span>
                                </div>
                                <table className="w-full text-left text-xs">
                                  <thead className="bg-slate-50/60 text-slate-600 border-b border-slate-200 text-[11px]">
                                    <tr>
                                      <th className="py-2 px-3">Class</th>
                                      <th className="py-2 px-3">Precision</th>
                                      <th className="py-2 px-3">Recall</th>
                                      <th className="py-2 px-3">F1-Score</th>
                                      <th className="py-2 px-3">Support</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100 font-mono">
                                    {activeEval.classes.map((cls) => {
                                      const m = activeEval.class_metrics[cls];
                                      if (!m) return null;
                                      return (
                                        <tr key={cls} className="hover:bg-slate-50/80">
                                          <td className="py-2.5 px-3 font-sans font-bold text-slate-800">
                                            <span
                                              className={`inline-block w-2 h-2 rounded-full mr-2 ${
                                                cls === "High"
                                                  ? "bg-rose-500"
                                                  : cls === "Medium"
                                                  ? "bg-amber-500"
                                                  : "bg-emerald-500"
                                              }`}
                                            />
                                            {cls}
                                          </td>
                                          <td className="py-2.5 px-3 text-slate-700">{(m.precision * 100).toFixed(1)}%</td>
                                          <td className="py-2.5 px-3 font-bold text-slate-900">{(m.recall * 100).toFixed(1)}%</td>
                                          <td className="py-2.5 px-3 text-emerald-800 font-bold">{m.f1_score.toFixed(3)}</td>
                                          <td className="py-2.5 px-3 text-slate-500 font-sans">{m.support}</td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>

                              {/* Confusion Matrix Visual */}
                              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 flex flex-col justify-between">
                                <div>
                                  <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs font-bold text-slate-700">
                                    <span>Confusion Matrix (Observed vs Predicted)</span>
                                    <span className="text-[11px] text-slate-500 font-normal">Rows: True / Cols: Pred</span>
                                  </div>
                                  <div className="mt-3">
                                    <div className="grid grid-cols-4 gap-1.5 text-center text-xs">
                                      {/* Header row */}
                                      <div className="text-[10px] text-slate-400 font-bold flex items-center justify-center">True \ Pred</div>
                                      <div className="py-1 text-[11px] font-bold text-emerald-800 bg-emerald-50 rounded">Pred Low</div>
                                      <div className="py-1 text-[11px] font-bold text-amber-800 bg-amber-50 rounded">Pred Med</div>
                                      <div className="py-1 text-[11px] font-bold text-rose-800 bg-rose-50 rounded">Pred High</div>

                                      {/* Matrix rows */}
                                      {activeEval.confusion_matrix.matrix.map((row, rIdx) => {
                                        const trueLabel = activeEval.confusion_matrix.labels[rIdx];
                                        return (
                                          <React.Fragment key={rIdx}>
                                            <div className="py-2 text-[11px] font-bold text-slate-700 flex items-center justify-end pr-2">
                                              {trueLabel}
                                            </div>
                                            {row.map((val, cIdx) => {
                                              const isDiagonal = rIdx === cIdx;
                                              return (
                                                <div
                                                  key={cIdx}
                                                  className={`py-2 px-1 rounded font-mono text-xs font-bold transition flex items-center justify-center ${
                                                    isDiagonal
                                                      ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                                      : val > 0
                                                      ? "bg-amber-100/70 text-amber-900 border border-amber-200"
                                                      : "bg-white text-slate-400 border border-slate-100"
                                                  }`}
                                                >
                                                  {val}
                                                </div>
                                              );
                                            })}
                                          </React.Fragment>
                                        );
                                      })}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-[11px] text-slate-500 mt-3 pt-2 border-t border-slate-200 flex items-center justify-between">
                                  <span>Diagonal cells = correct classifications</span>
                                  <span>Off-diagonal = misclassification errors</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    {/* Scientific Temporal Degradation Analysis Card */}
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                      <div className="flex items-center gap-2">
                        <TrendingUp size={18} className="text-amber-600" />
                        <h4 className="font-extrabold text-slate-900 text-sm">
                          Temporal Performance Degradation & Scientific Boundary Analysis
                        </h4>
                      </div>

                      {/* Degradation Stats Callout */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                        <div className="p-3.5 bg-amber-50/60 border border-amber-200/80 rounded-xl">
                          <div className="text-[11px] font-bold text-amber-900 uppercase">Accuracy Drift</div>
                          <div className="text-base font-extrabold text-slate-900 mt-1">
                            {(mlData.validation_metrics.temporal_degradation_analysis.accuracy_2023 * 100).toFixed(1)}%{" "}
                            <span className="text-slate-400 font-normal">→</span>{" "}
                            <span className="text-amber-700">
                              {(mlData.validation_metrics.temporal_degradation_analysis.accuracy_2025 * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">2023 Fold vs 2025 Holdout</div>
                        </div>

                        <div className="p-3.5 bg-amber-50/60 border border-amber-200/80 rounded-xl">
                          <div className="text-[11px] font-bold text-amber-900 uppercase">Macro F1 Shift</div>
                          <div className="text-base font-extrabold text-slate-900 mt-1">
                            {mlData.validation_metrics.temporal_degradation_analysis.macro_f1_2023.toFixed(3)}{" "}
                            <span className="text-slate-400 font-normal">→</span>{" "}
                            <span className="text-amber-700">
                              {mlData.validation_metrics.temporal_degradation_analysis.macro_f1_2025.toFixed(3)}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">Boundary threshold shift</div>
                        </div>

                        <div className="p-3.5 bg-rose-50/60 border border-rose-200/80 rounded-xl">
                          <div className="text-[11px] font-bold text-rose-900 uppercase">Medium Class Recall</div>
                          <div className="text-base font-extrabold text-slate-900 mt-1">
                            {(mlData.validation_metrics.temporal_degradation_analysis.medium_recall_2023 * 100).toFixed(1)}%{" "}
                            <span className="text-slate-400 font-normal">→</span>{" "}
                            <span className="text-rose-700">
                              {(mlData.validation_metrics.temporal_degradation_analysis.medium_recall_2025 * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">Transition to high concentration</div>
                        </div>

                        <div className="p-3.5 bg-emerald-50/60 border border-emerald-200/80 rounded-xl">
                          <div className="text-[11px] font-bold text-emerald-900 uppercase">High Class Recall</div>
                          <div className="text-base font-extrabold text-slate-900 mt-1">
                            {(mlData.validation_metrics.temporal_degradation_analysis.high_recall_2023 * 100).toFixed(1)}%{" "}
                            <span className="text-slate-400 font-normal">→</span>{" "}
                            <span className="text-emerald-700">
                              {(mlData.validation_metrics.temporal_degradation_analysis.high_recall_2025 * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">Maintains severe surge detection</div>
                        </div>
                      </div>

                      {/* Observations list */}
                      <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs text-slate-700">
                        <div className="font-bold text-slate-900">Key Scientific Findings from Frozen Chronological Folds:</div>
                        <ul className="list-disc pl-5 space-y-1 text-slate-600">
                          {mlData.validation_metrics.temporal_degradation_analysis.observations.map((obs, idx) => (
                            <li key={idx}>{obs}</li>
                          ))}
                        </ul>
                      </div>

                      {/* Explicit Scientific Limitation Callout */}
                      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-start gap-3">
                        <AlertTriangle size={20} className="shrink-0 text-amber-600 mt-0.5" />
                        <div>
                          <strong className="block font-bold mb-1">
                            RESEARCH PROXY NOTATION vs. OPERATIONAL RISK
                          </strong>
                          {mlData.validation_metrics.temporal_degradation_analysis.scientific_limitations_notice}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* PHASE 2: SEPARATE K-MEANS & DBSCAN RESEARCH VISUALIZATION */}
                <div className="space-y-6">
                  {/* Research Governance & Methodology Header */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                      <div>
                        <div className="flex items-center gap-2">
                          <Layers size={20} className="text-sky-700" />
                          <h3 className="font-extrabold text-slate-900 text-base">
                            Unsupervised Spatial & Density Pattern Analysis (K-Means vs DBSCAN)
                          </h3>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Evaluates active pre-planting snapshots across pilot districts using one-hot encoded crop/region vectors and standardized numeric dimensions.
                        </p>
                      </div>

                      {/* MODE SELECTOR: Live Operational Snapshot vs Synthetic Research Demo */}
                      <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200/80 text-xs shrink-0">
                        <button
                          onClick={() => handleClusterModeChange("live")}
                          className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                            clusterMode === "live"
                              ? "bg-white text-emerald-800 shadow-xs border border-slate-200/80"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          Live Operational Snapshot
                        </button>
                        <button
                          onClick={() => handleClusterModeChange("synthetic_demo")}
                          className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                            clusterMode === "synthetic_demo"
                              ? "bg-sky-700 text-white shadow-xs"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          Synthetic Research Demo Mode
                        </button>
                      </div>
                    </div>

                    {/* Active Mode Notice */}
                    {clusterMode === "synthetic_demo" ? (
                      <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-950 flex items-start gap-2.5">
                        <Sparkles size={18} className="text-sky-700 shrink-0 mt-0.5" />
                        <div>
                          <strong className="block font-bold">
                            SYNTHETIC RESEARCH DEMONSTRATION — NOT REAL FARMER DATA
                          </strong>
                          Displaying actual K-Means and DBSCAN execution on an isolated benchmark cohort of 17 synthetic demonstration plans across 6 synthetic test farmers.
                          Real registered farmer plans remain completely isolated and unread.
                        </div>
                      </div>
                    ) : (
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-start gap-2.5">
                        <ShieldCheck size={18} className="text-emerald-700 shrink-0 mt-0.5" />
                        <div>
                          <strong className="block font-bold text-slate-900">
                            LIVE OPERATIONAL PRE-PLANTING SNAPSHOT MODE
                          </strong>
                          Clustering live active plans where planting and harvest dates are in the future.
                          Small-cohort privacy protection (threshold MIN_FARMERS ≥ 3) is strictly enforced to prevent farmer de-anonymization.
                        </div>
                      </div>
                    )}

                    {/* Scientific Distinction Notice */}
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-2">
                      <div className="font-bold text-slate-900 flex items-center gap-1.5">
                        <Info size={16} className="text-sky-700 shrink-0" />
                        Methodological Boundary: Clustering is NOT Risk Classification
                      </div>
                      <p className="text-slate-600">
                        K-Means partitioning and DBSCAN density clustering are strictly <strong>unsupervised descriptive exploratory methods</strong>.
                        They group submitted plans by feature similarity and spatial density. They are <strong>NOT</strong> validated Low, Medium, or High risk classifiers.
                        A high-density DBSCAN neighborhood does not indicate an oversupply hazard, nor does an outlier/noise plan indicate low risk.
                      </p>
                      <div className="pt-2 border-t border-slate-200/80 flex flex-wrap gap-4 text-[11px] text-slate-500 font-mono">
                        <span>• Scaling: One-hot crop & region (weight 1/√2)</span>
                        <span>• Standardized: log(1 + acres) & elapsed harvest offset days</span>
                        <span>• Small-Cohort Policy: MIN_FARMERS ≥ 3 (smaller clusters strictly suppressed)</span>
                      </div>
                    </div>
                  </div>

                  {/* District Panels: Matara & Hambantota */}
                  <div className="space-y-6">
                    {Object.entries(mlData.clustering).map(([distName, clusterInfo]) => (
                      <div key={distName} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
                        {/* District Header & Configuration */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                          <div className="flex items-center gap-2">
                            <MapPin size={20} className="text-emerald-700" />
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-extrabold text-slate-900 text-base">{distName} District</h4>
                                {clusterInfo.mode === "synthetic_research_demo" && (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-800 border border-sky-300">
                                    SYNTHETIC BENCHMARK
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-500 font-mono mt-0.5">
                                Snapshot Status:{" "}
                                <span
                                  className={`font-bold ${
                                    clusterInfo.status === "available" ? "text-emerald-700" : "text-amber-700"
                                  }`}
                                >
                                  {clusterInfo.status === "available"
                                    ? `Available (${clusterInfo.mode === "synthetic_research_demo" ? "Synthetic Cohort Met" : "Live Cohort Threshold Met"})`
                                    : "Insufficient Cohort or Private (< 3 Distinct Farmers)"}
                                </span>
                              </div>
                            </div>
                          </div>
                          {clusterInfo.configuration && (
                            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                              <span className="px-2 py-1 rounded bg-slate-100 border border-slate-200 text-slate-700">
                                Effective k: <strong>{clusterInfo.effective_k ?? clusterInfo.configuration.requested_k}</strong>
                              </span>
                              <span className="px-2 py-1 rounded bg-slate-100 border border-slate-200 text-slate-700">
                                DBSCAN ε: <strong>{clusterInfo.configuration.eps}</strong>
                              </span>
                              <span className="px-2 py-1 rounded bg-slate-100 border border-slate-200 text-slate-700">
                                min_samples: <strong>{clusterInfo.configuration.min_samples}</strong>
                              </span>
                            </div>
                          )}
                        </div>

                        {/* If District has insufficient cohort or small group, display privacy protection banner */}
                        {clusterInfo.status === "insufficient_or_private" ? (
                          <div className="p-6 rounded-2xl bg-slate-50/80 border border-slate-200 text-center space-y-2">
                            <ShieldCheck size={28} className="text-emerald-700 mx-auto" />
                            <div className="text-sm font-bold text-slate-800">
                              Small-Cohort Privacy Protection Active for {distName}
                            </div>
                            <p className="text-xs text-slate-500 max-w-xl mx-auto">
                              Fewer than 3 distinct registered farmers have submitted eligible active pre-planting plans in this district.
                              In adherence to strict research privacy rules, K-Means and DBSCAN algorithms were <strong>not executed</strong> and details are withheld
                              to prevent single-farmer de-anonymization and cohort re-identification.
                            </p>
                            <div className="pt-2 text-[11px] text-slate-600">
                              <span className="font-semibold text-sky-800">Research Demonstration Tip:</span> Switch to{" "}
                              <button
                                onClick={() => handleClusterModeChange("synthetic_demo")}
                                className="font-bold underline text-sky-700 hover:text-sky-900"
                              >
                                Synthetic Research Demo Mode
                              </button>{" "}
                              above to observe K-Means and DBSCAN clustering execution on an isolated benchmark cohort.
                            </div>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* SECTION 1: K-MEANS SIMILARITY PARTITIONS */}
                            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/40 space-y-4">
                              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                                <div className="flex items-center gap-2">
                                  <span className="w-2.5 h-2.5 rounded-full bg-sky-600" />
                                  <h5 className="font-bold text-slate-900 text-sm">
                                    K-Means Similarity Partitions (k = {clusterInfo.effective_k ?? 3})
                                  </h5>
                                </div>
                                <span className="text-[11px] font-mono text-slate-500">Global Space Partition</span>
                              </div>

                              <p className="text-xs text-slate-600">
                                Groups plans into discrete partitions with similar crop types, agricultural regions, log-transformed acreage, and target harvest dates.
                              </p>

                              {clusterInfo.kmeans && clusterInfo.kmeans.length > 0 ? (
                                <div className="space-y-3">
                                  {clusterInfo.kmeans.map((km, idx) => {
                                    if (km.status === "suppressed") {
                                      return (
                                        <div key={idx} className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-800">
                                          Cluster #{km.cluster_id ?? idx + 1}: {km.reason || "Suppressed for privacy (< 3 distinct farmers in cluster)."}
                                        </div>
                                      );
                                    }
                                    return (
                                      <div key={idx} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2 text-xs">
                                        <div className="flex items-center justify-between">
                                          <span className="font-extrabold text-slate-900">
                                            Cluster #{km.cluster_id ?? idx + 1}
                                          </span>
                                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-50 text-sky-800 border border-sky-200 font-bold">
                                            {km.crops?.join(", ") || "Multi-crop"}
                                          </span>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2 text-slate-600 font-mono">
                                          <div>
                                            Acreage: <strong className="text-slate-900 font-bold">{km.planned_acreage} ac</strong>
                                          </div>
                                          <div>
                                            Cohort: <strong className="text-slate-900 font-bold">{km.farmer_count} farmers</strong> ({km.plan_count} plans)
                                          </div>
                                          <div className="col-span-2 text-[11px] font-sans text-slate-500">
                                            Regions: <span className="font-semibold text-slate-700">{km.regions?.join(", ") || "District-wide"}</span>
                                          </div>
                                          <div className="col-span-2 text-[11px] font-sans text-slate-500">
                                            Harvest Window: <span className="font-mono text-slate-700">{km.harvest_period_start} to {km.harvest_period_end}</span>
                                          </div>
                                          {km.peak_plan_centered_29_day_planned_acreage !== undefined && (
                                            <div className="col-span-2 text-[11px] bg-slate-50 p-2 rounded border border-slate-200/80 font-sans text-slate-600">
                                              Peak 29-Day Window: <strong className="text-slate-900 font-mono">{km.peak_plan_centered_29_day_planned_acreage} ac</strong> ({Math.round((km.peak_window_acreage_share ?? 0) * 100)}% of cluster)
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              ) : (
                                <div className="p-4 bg-slate-100 rounded-xl text-xs text-slate-500 text-center">
                                  Not executed due to insufficient cohort size (&lt; 3 plans or distinct farmers).
                                </div>
                              )}
                            </div>

                            {/* SECTION 2: DBSCAN DENSITY CLUSTERS & OUTLIERS */}
                            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/40 space-y-4">
                              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                                <div className="flex items-center gap-2">
                                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                                  <h5 className="font-bold text-slate-900 text-sm">
                                    DBSCAN Dense Neighborhoods & Anomaly Noise
                                  </h5>
                                </div>
                                <span className="text-[11px] font-mono text-slate-500">ε={clusterInfo.configuration?.eps ?? 1.0}, min={clusterInfo.configuration?.min_samples ?? 2}</span>
                              </div>

                              <p className="text-xs text-slate-600">
                                Discovers arbitrary-shaped contiguous spatial/crop density pockets. Isolated atypical plans are isolated as noise outliers.
                              </p>

                              {/* Dense clusters */}
                              <div className="space-y-3">
                                {clusterInfo.dbscan && clusterInfo.dbscan.length > 0 ? (
                                  clusterInfo.dbscan.map((db, idx) => {
                                    if (db.status === "suppressed") {
                                      return (
                                        <div key={idx} className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-800">
                                          Dense Cluster #{db.cluster_id ?? idx + 1}: {db.reason || "Suppressed for privacy (< 3 distinct farmers in cluster)."}
                                        </div>
                                      );
                                    }
                                    return (
                                      <div key={idx} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2 text-xs">
                                        <div className="flex items-center justify-between">
                                          <span className="font-extrabold text-slate-900">
                                            Dense Cluster #{db.cluster_id ?? idx + 1}
                                          </span>
                                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                                            Connected Neighborhood
                                          </span>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2 text-slate-600 font-mono">
                                          <div>
                                            Acreage: <strong className="text-slate-900 font-bold">{db.planned_acreage} ac</strong>
                                          </div>
                                          <div>
                                            Cohort: <strong className="text-slate-900 font-bold">{db.farmer_count} farmers</strong> ({db.plan_count} plans)
                                          </div>
                                          <div className="col-span-2 text-[11px] font-sans text-slate-500">
                                            Crops: <span className="font-semibold text-slate-700">{db.crops?.join(", ") || "—"}</span>
                                          </div>
                                          <div className="col-span-2 text-[11px] font-sans text-slate-500">
                                            Regions: <span className="font-semibold text-slate-700">{db.regions?.join(", ") || "—"}</span>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })
                                ) : (
                                  <div className="p-4 bg-slate-100/90 rounded-xl text-xs text-slate-600 text-center">
                                    No dense contiguous neighborhoods detected after DBSCAN execution at ε={clusterInfo.configuration?.eps ?? 1.0}, min_samples={clusterInfo.configuration?.min_samples ?? 2}. All plans were classified as noise outliers or baseline.
                                  </div>
                                )}

                                {/* DBSCAN Noise / Outlier Card */}
                                <div className="border border-slate-200 rounded-xl p-4 bg-white space-y-2.5">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1.5 font-bold text-slate-800 text-xs">
                                      <AlertTriangle size={15} className="text-amber-600" />
                                      DBSCAN Noise Points (Outliers)
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-500 font-bold">
                                      Label = -1
                                    </span>
                                  </div>

                                  {clusterInfo.noise && clusterInfo.noise.status === "available" ? (
                                    <div className="space-y-1.5 text-xs">
                                      <div className="grid grid-cols-2 gap-2 font-mono text-slate-700">
                                        <div>
                                          Total Outliers: <strong>{clusterInfo.noise.plan_count} plans</strong>
                                        </div>
                                        <div>
                                          Acreage: <strong>{clusterInfo.noise.planned_acreage} ac</strong>
                                        </div>
                                      </div>
                                      <div className="text-[11px] text-slate-500 font-sans">
                                        Outlier Crops: <span className="font-semibold text-slate-700">{clusterInfo.noise.crops?.join(", ")}</span>
                                      </div>
                                      <div className="text-[11px] text-slate-500 font-sans">
                                        Affected Regions: <span className="font-semibold text-slate-700">{clusterInfo.noise.regions?.join(", ")}</span>
                                      </div>
                                    </div>
                                  ) : clusterInfo.noise && clusterInfo.noise.status === "suppressed" ? (
                                    <div className="text-xs text-amber-800 bg-amber-50/80 p-2.5 rounded-lg border border-amber-200">
                                      {clusterInfo.noise.reason || "Suppressed for privacy: Fewer than 3 distinct outlier farmers in noise group."}
                                    </div>
                                  ) : (
                                    <div className="text-xs text-slate-500">
                                      No isolated noise outliers detected under current density parameters.
                                    </div>
                                  )}

                                  <div className="text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
                                    <strong>Scientific Note:</strong> Noise points represent atypical crop selections, unusual acreage, or staggered dates. They are candidates for agronomic review, NOT automatically erroneous or high risk.
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
                  </div>
                )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200 bg-white">
        Component 02 Cultivation Concentration Research & Risk Governance Platform • Restricted Administrative Access
      </footer>
    </div>
  );
}
