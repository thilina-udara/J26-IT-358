"use client";
import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ShieldCheck,
  Sprout,
  Users,
  Lock,
  User,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  Building2,
  Sparkles,
} from "lucide-react";
import { useSession } from "../components/session";
import { useAdminSession } from "../lib/admin-session";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { signIn: farmerSignIn, session: farmerSession, notice: farmerNotice } = useSession();
  const { login: adminLogin } = useAdminSession();

  const [activeRole, setActiveRole] = useState<"farmer" | "admin">("farmer");

  // Farmer form state
  const [farmerId, setFarmerId] = useState("");
  const [farmerPass, setFarmerPass] = useState("");
  const [showFarmerPass, setShowFarmerPass] = useState(false);
  const [farmerBusy, setFarmerBusy] = useState(false);
  const [farmerError, setFarmerError] = useState<string | null>(null);

  // Admin form state
  const [adminId, setAdminId] = useState("local.admin");
  const [adminPass, setAdminPass] = useState("AdminPass@2026!");
  const [showAdminPass, setShowAdminPass] = useState(false);
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);

  async function handleFarmerSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFarmerError(null);
    if (!farmerId.trim() || !farmerPass) {
      setFarmerError("Please enter both username and password.");
      return;
    }
    setFarmerBusy(true);
    try {
      await farmerSignIn({
        login_identifier: farmerId.trim().toLowerCase(),
        password: farmerPass,
      });
      router.replace("/crop-planning/dashboard");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setFarmerError(err.message);
      } else if (err instanceof Error) {
        setFarmerError(err.message);
      } else {
        setFarmerError("Farmer authentication failed. Check credentials.");
      }
    } finally {
      setFarmerBusy(false);
    }
  }

  async function handleAdminSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAdminError(null);
    if (!adminId.trim() || !adminPass) {
      setAdminError("Please enter both identifier and password.");
      return;
    }
    setAdminBusy(true);
    try {
      await adminLogin({
        login_identifier: adminId.trim().toLowerCase(),
        password: adminPass,
      });
      router.replace("/crop-planning/admin/dashboard");
    } catch (err: unknown) {
      setAdminError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setAdminBusy(false);
    }
  }

  return (
    <div className="cp-root cp-public cp-auth-page min-h-screen flex flex-col justify-between bg-slate-50 text-slate-900">
      {/* Top Navbar */}
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
                  AI
                </span>
              </div>
              <div className="portal-logo-tag">Your Farming Partner • AIMS Research</div>
            </div>
          </Link>
          <nav className="portal-nav-links" aria-label="Main navigation">
            <Link href="/">Home</Link>
            <Link href="/crop-planning">Crop Planning</Link>
            <Link href="/#about">About Us</Link>
            <Link href="/#features">Key Features</Link>
            <Link href="/#services">Services</Link>
          </nav>
          <div className="portal-nav-actions">
            <Link href="/crop-planning/register" className="portal-btn-signup">
              Create Farmer Account <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Authentication Section */}
      <main className="flex-1 py-8 px-4 flex items-center justify-center">
        <div className="max-w-5xl w-full grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch bg-white border border-slate-200/90 rounded-3xl shadow-xl overflow-hidden">
          
          {/* Left Story Banner */}
          <div className="md:col-span-5 relative bg-emerald-950 text-white p-8 md:p-10 flex flex-col justify-between overflow-hidden">
            <Image
              src="/crop-planning/agfarm_aerial.jpg"
              alt="Aerial view of green agricultural paddy fields"
              fill
              priority
              className="object-cover opacity-25"
            />
            <div className="relative z-10 space-y-4">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <Sprout size={14} /> AI-POWERED CROP PLANNING
              </span>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white leading-tight">
                Secure Portal Access for Agriculture.
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Connect to your personalized crop planning workspace or sign in as an Agricultural Officer to oversee regional cultivation trends and AI risk analyses.
              </p>
            </div>

            <div className="relative z-10 pt-8 border-t border-emerald-900/60 mt-8 space-y-2.5 text-xs text-emerald-200/90">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400" />
                <span>Zero cross-farmer plan disclosure on farmer accounts</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-emerald-400" />
                <span>Regional concentration analytics for officers</span>
              </div>
            </div>
          </div>

          {/* Right Form Container */}
          <div className="md:col-span-7 p-6 md:p-10 flex flex-col justify-center">
            {/* Role Switcher Tabs */}
            <div className="mb-6">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Select Login Portal
              </label>
              <div className="grid grid-cols-2 gap-2 p-1.5 bg-slate-100 rounded-2xl border border-slate-200">
                <button
                  type="button"
                  onClick={() => setActiveRole("farmer")}
                  className={`py-3 px-4 rounded-xl text-sm font-semibold flex items-center justify-center gap-2.5 transition-all ${
                    activeRole === "farmer"
                      ? "bg-white text-emerald-800 shadow-sm border border-emerald-200/70"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                  }`}
                >
                  <Users size={18} className={activeRole === "farmer" ? "text-emerald-600" : "text-slate-400"} />
                  <span>Farmer Login</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveRole("admin")}
                  className={`py-3 px-4 rounded-xl text-sm font-semibold flex items-center justify-center gap-2.5 transition-all ${
                    activeRole === "admin"
                      ? "bg-emerald-900 text-white shadow-sm border border-emerald-800"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                  }`}
                >
                  <ShieldCheck size={18} className={activeRole === "admin" ? "text-emerald-300" : "text-slate-400"} />
                  <span>Admin / Officer</span>
                </button>
              </div>
            </div>

            {/* TAB 1: FARMER LOGIN FORM */}
            {activeRole === "farmer" && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-900">Farmer Workspace Login</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Sign in to access your individual cultivation plans, risk analyses, and crop guidelines.
                  </p>
                </div>

                {farmerNotice && (
                  <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-xs">
                    {farmerNotice}
                  </div>
                )}

                {farmerError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center gap-2">
                    <AlertCircle size={16} className="shrink-0" />
                    <span>{farmerError}</span>
                  </div>
                )}

                <form onSubmit={handleFarmerSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Farmer Username
                    </label>
                    <div className="relative">
                      <User size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="text"
                        required
                        value={farmerId}
                        onChange={(e) => setFarmerId(e.target.value)}
                        placeholder="e.g. dinithi"
                        autoCapitalize="none"
                        spellCheck={false}
                        className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-emerald-600 focus:bg-white transition"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Password
                    </label>
                    <div className="relative">
                      <Lock size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type={showFarmerPass ? "text" : "password"}
                        required
                        value={farmerPass}
                        onChange={(e) => setFarmerPass(e.target.value)}
                        placeholder="Enter your farmer password"
                        className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-emerald-600 focus:bg-white transition"
                      />
                      <button
                        type="button"
                        onClick={() => setShowFarmerPass(!showFarmerPass)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showFarmerPass ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={farmerBusy}
                    className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-md transition disabled:opacity-50"
                  >
                    {farmerBusy ? (
                      <>
                        <Loader2 size={18} className="animate-spin" /> Verifying...
                      </>
                    ) : (
                      <>
                        Sign In to Farmer Portal <ArrowRight size={17} />
                      </>
                    )}
                  </button>
                </form>

                <div className="pt-2 text-center text-xs text-slate-500">
                  New farmer?{" "}
                  <Link href="/crop-planning/register" className="font-semibold text-emerald-700 hover:underline">
                    Create a free account
                  </Link>
                </div>
              </div>
            )}

            {/* TAB 2: ADMIN / OFFICER LOGIN FORM */}
            {activeRole === "admin" && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <ShieldCheck size={22} className="text-emerald-700" />
                    Agricultural Officer Login
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Sign in to view all registered farmers&apos; plans, acreage, and AI risk monitoring.
                  </p>
                </div>

                {adminError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center gap-2">
                    <AlertCircle size={16} className="shrink-0" />
                    <span>{adminError}</span>
                  </div>
                )}

                <form onSubmit={handleAdminSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Officer Identifier / Username
                    </label>
                    <div className="relative">
                      <Building2 size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="text"
                        required
                        value={adminId}
                        onChange={(e) => setAdminId(e.target.value)}
                        placeholder="local.admin"
                        autoCapitalize="none"
                        spellCheck={false}
                        className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-emerald-600 focus:bg-white transition"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Passphrase
                    </label>
                    <div className="relative">
                      <Lock size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type={showAdminPass ? "text" : "password"}
                        required
                        value={adminPass}
                        onChange={(e) => setAdminPass(e.target.value)}
                        placeholder="AdminPass@2026!"
                        className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-emerald-600 focus:bg-white transition"
                      />
                      <button
                        type="button"
                        onClick={() => setShowAdminPass(!showAdminPass)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showAdminPass ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={adminBusy}
                    className="w-full py-3 px-4 rounded-xl bg-emerald-800 hover:bg-emerald-900 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-md transition disabled:opacity-50"
                  >
                    {adminBusy ? (
                      <>
                        <Loader2 size={18} className="animate-spin" /> Authenticating Officer...
                      </>
                    ) : (
                      <>
                        Enter Admin Dashboard <ArrowRight size={17} />
                      </>
                    )}
                  </button>
                </form>

                {/* Default dev credentials */}
                <div className="p-3 bg-slate-100 rounded-xl border border-slate-200 text-xs text-slate-600">
                  <span className="font-semibold text-slate-800">Officer Credentials:</span> User:{" "}
                  <code className="text-emerald-700 font-bold">local.admin</code> | Pass:{" "}
                  <code className="text-emerald-700 font-bold">AdminPass@2026!</code>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200 bg-white">
        Component 02 Cultivation Concentration Research Platform • Department of Agriculture & AIMS Research
      </footer>
    </div>
  );
}
