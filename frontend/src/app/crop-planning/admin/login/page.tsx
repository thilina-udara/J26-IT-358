"use client";
import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  Sparkles,
  Sprout,
  Loader2,
  AlertCircle,
  Building2,
} from "lucide-react";
import { useAdminSession } from "../../lib/admin-session";

export default function AdminLoginPage() {
  const router = useRouter();
  const { login } = useAdminSession();

  const [username, setUsername] = useState("local.admin");
  const [password, setPassword] = useState("AdminPass@2026!");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await login({
        login_identifier: username.trim().toLowerCase(),
        password,
      });
      router.replace("/crop-planning/admin/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cp-root cp-public cp-auth-page min-h-screen flex flex-col justify-between" style={{ backgroundColor: "#fbfdfa", color: "#0f172a" }}>
      {/* Top Navbar matching Kishan Sathi / AgroDecision AI Home */}
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
            <Link href="/crop-planning/login" className="portal-btn-login">
              Farmer Login
            </Link>
            <Link href="/crop-planning/register" className="portal-btn-signup">
              Sign Up <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Login Layout */}
      <main className="flex-1 py-12 px-4 flex items-center justify-center">
        <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch bg-white border border-slate-200/90 rounded-3xl shadow-xl overflow-hidden">
          
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
                <ShieldCheck size={14} /> OFFICER PORTAL
              </span>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white leading-tight">
                Regional Crop Risk & Cultivation Governance
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Authorized agricultural administration for Matara & Hambantota districts. Inspect all farmers&apos; plans, monitor acreage concentration, and view predictive AI models.
              </p>
            </div>

            <div className="relative z-10 pt-8 border-t border-emerald-900/60 mt-8 space-y-2.5 text-xs text-emerald-200/90">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-emerald-400" />
                <span>Aggregated crop supply & harvest timing</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400" />
                <span>Restricted officer role-based authentication</span>
              </div>
            </div>
          </div>

          {/* Right Form Container */}
          <div className="md:col-span-7 p-6 md:p-10 flex flex-col justify-center">
            <div className="mb-6">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center mb-3 shadow-xs">
                <ShieldCheck size={26} />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Agricultural Officer Sign In</h1>
              <p className="text-xs text-slate-500 mt-1">
                Enter your administrative credentials to open the regional crop intelligence console.
              </p>
            </div>

            {error && (
              <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5">
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Officer Username / Identifier
                </label>
                <div className="relative">
                  <Building2 size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. local.admin"
                    autoCapitalize="none"
                    spellCheck={false}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-600 focus:bg-white text-sm transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Passphrase
                </label>
                <div className="relative">
                  <Lock size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter administrator passphrase"
                    className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-600 focus:bg-white text-sm transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full mt-2 py-3 px-4 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md transition disabled:opacity-50"
                style={{ backgroundColor: "#15803d" }}
              >
                {busy ? (
                  <>
                    <Loader2 size={18} className="animate-spin" /> Authenticating Officer...
                  </>
                ) : (
                  <>
                    Enter Agricultural Officer Console <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500">
              <span className="font-semibold text-slate-700">Development Credentials:</span>{" "}
              User: <code className="text-emerald-700 font-bold">local.admin</code> | Pass:{" "}
              <code className="text-emerald-700 font-bold">AdminPass@2026!</code>
            </div>
          </div>
        </div>
      </main>

      <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200 bg-white">
        Component 02 Cultivation Concentration Research Platform • Department of Agriculture & AIMS Research
      </footer>
    </div>
  );
}
