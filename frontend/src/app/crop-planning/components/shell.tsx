"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowRight,
  BarChart3,
  ChevronRight,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  NotebookPen,
  ShieldCheck,
  X,
  Sparkles,
  FileText,
  CalendarDays,
  Sprout,
  User,
  Bell,
  FlaskConical,
  type LucideIcon,
} from "lucide-react";
import { Button } from "./ui/button";
import { Brand } from "./brand";
import { Notice } from "./ui";
import { Protected, useSession } from "./session";
import { activeWorkspace, isPublicRoute, ROOT, WORKSPACE_NAV } from "../lib/navigation";

const icons: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  plans: FileText,
  analysis: BarChart3,
  crops: Sprout,
  planning: CalendarDays,
  research: FlaskConical,
  profile: User,
};

export function CropShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || ROOT;
  const router = useRouter();
  const { session, signOut, notice } = useSession();
  const [open, setOpen] = useState(false);
  const publicPage = isPublicRoute(pathname);
  const authPage = pathname === `${ROOT}/login` || pathname === `${ROOT}/register`;

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open || typeof document === "undefined") return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        (document.querySelector(".cp-menu-toggle") as HTMLButtonElement | null)?.focus();
      }
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [open]);

  async function logout() {
    setOpen(false);
    await signOut();
    router.replace(ROOT);
  }

  const links = (
    <>
      {WORKSPACE_NAV.map((item) => {
        const Icon = icons[item.icon] || LayoutDashboard;
        const isActive = activeWorkspace(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            onClick={() => setOpen(false)}
            style={
              isActive
                ? {
                  background: "#eaf5ea",
                  color: "#15803d",
                  fontWeight: 700,
                }
                : undefined
            }
          >
            <Icon size={19} aria-hidden="true" />
            <span>{item.label}</span>
            <ChevronRight className="cp-nav-chevron" size={15} aria-hidden="true" />
          </Link>
        );
      })}
    </>
  );

  if (publicPage) {
    if (authPage) return <>{children}</>;
    return (
      <div className="cp-root cp-public">
        <a href="#crop-main" className="cp-skip">
          Skip to content
        </a>
        <header className="cp-public-header">
          <div className="cp-public-nav">
            <Brand />
            <nav className="cp-public-links" aria-label="Public navigation">
              <Link href="/">
                Research Portal
              </Link>
              <Link href={ROOT} aria-current={pathname === ROOT ? "page" : undefined}>
                Crop Planning
              </Link>
              <Link href={`${ROOT}#features`}>What you can do</Link>
              <Link href={`${ROOT}#how-it-works`}>How it works</Link>
              <Link href={`${ROOT}#research`}>Research Model</Link>
            </nav>
            <div className="cp-public-auth">
              <Link href={`${ROOT}/login`}>Log in</Link>
              <Button asChild>
                <Link href={session ? `${ROOT}/dashboard` : `${ROOT}/register`}>
                  {session ? "My dashboard" : "Get started"}
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              </Button>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="cp-menu-toggle"
              aria-label={open ? "Close navigation" : "Open navigation"}
              aria-expanded={open}
              aria-controls="cp-public-mobile"
              onClick={() => setOpen((value) => !value)}
            >
              {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </Button>
          </div>
          {open && (
            <nav id="cp-public-mobile" className="cp-mobile-public" aria-label="Mobile public navigation">
              {[
                { href: ROOT, label: "Home" },
                { href: `${ROOT}/login`, label: "Login" },
                { href: `${ROOT}/register`, label: "Register" },
                ...(session ? [{ href: `${ROOT}/dashboard`, label: "Dashboard" }] : []),
              ].map((item) => (
                <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
                  {item.label}
                </Link>
              ))}
            </nav>
          )}
        </header>
        <main id="crop-main">
          {notice && pathname === ROOT && (
            <div className="cp-container cp-session-notice">
              <Notice kind="warning">{notice}</Notice>
            </div>
          )}
          {children}
        </main>
        <footer className="cp-public-footer">
          <div className="cp-container cp-footer-grid">
            <div>
              <Brand />
              <p>AI-based cultivation concentration risk analysis, alternative crop recommendation, and personalized cultivation planning.</p>
            </div>
            <nav aria-label="Footer navigation">
              <Link href={ROOT}>Home</Link>
              <Link href={`${ROOT}/login`}>Login</Link>
              <Link href={`${ROOT}/register`}>Register</Link>
              <Link href={`${ROOT}#features`}>Capabilities</Link>
              <Link href={`${ROOT}#research`}>Research Proxy</Link>
            </nav>
            <div className="cp-footer-research">
              <span>FINAL-YEAR RESEARCH · COMPONENT 02</span>
              <p>Cultivation concentration analysis, conditional crop comparison, and personalized planning system.</p>
              <div className="cp-footer-badge">
                <Sparkles size={13} aria-hidden="true" />
                <span>Matara & Hambantota Agricultural Focus</span>
              </div>
            </div>
          </div>
          <div className="cp-container cp-footer-bottom">
            <span>Built for informed agricultural decisions with privacy preservation.</span>
            <div className="cp-footer-credits">
              <a href="https://unsplash.com/photos/YnDuU2vTCY4" target="_blank" rel="noopener noreferrer">
                Agricultural photograph by Andreas Felske / Unsplash
              </a>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  const farmerInitial = (session?.farmer.login_identifier || "D").slice(0, 1).toUpperCase();
  const farmerName = session?.farmer.login_identifier || "dinithi";

  return (
    <div className="cp-root cp-private">
      <a href="#crop-main" className="cp-skip">
        Skip to content
      </a>
      <aside className="cp-sidebar">
        <Brand />
        <nav aria-label="Farmer navigation" style={{ marginTop: "12px" }}>
          {links}
        </nav>

        {/* Promo card matching Image 2 */}
        <div
          style={{
            marginTop: "auto",
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: "16px",
            padding: "16px",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "8px" }}>
            <svg width="44" height="38" viewBox="0 0 44 38" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="22" cy="33" rx="18" ry="4" fill="#a38260" opacity="0.3" />
              <path d="M8 32C11 29 19 28 22 28C25 28 33 29 36 32C32 34 27 35 22 35C17 35 12 34 8 32Z" fill="#8c6d48" />
              <path d="M22 29V14" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M22 21C27 19 33 20 34 16C34 13 30 13 25 17C23.5 18 22 19.5 22 21Z" fill="#22c55e" />
              <path d="M22 17C17 15 11 16 10 12C10 9 14 9 19 13C20.5 14 22 15.5 22 17Z" fill="#15803d" />
              <path d="M22 14C21 9 23 5 22 3C21 5 19 9 22 14Z" fill="#4ade80" />
            </svg>
          </div>
          <strong style={{ fontSize: "13px", color: "#14532d", display: "block", marginBottom: "4px" }}>
            Data-Driven Better Farming
          </strong>
          <p style={{ fontSize: "11px", color: "#475569", margin: 0, lineHeight: 1.5 }}>
            Safer crops. Better decisions. A resilient tomorrow.
          </p>
        </div>

        {/* Farmer Profile Card matching Image 2 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 14px",
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "14px",
            marginBottom: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                background: "#15803d",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: "14px",
              }}
            >
              {farmerInitial}
            </span>
            <div>
              <strong style={{ fontSize: "13px", color: "#0f172a", display: "block" }}>
                {farmerName}
              </strong>
              <small style={{ fontSize: "11px", color: "#64748b" }}>Farmer</small>
            </div>
          </div>
          <Link href={`${ROOT}/plans#profile`} style={{ color: "#94a3b8" }}>
            <ArrowRight size={16} />
          </Link>
        </div>

        {/* Logout Button */}
        {session && (
          <button
            type="button"
            onClick={() => void logout()}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              borderRadius: "10px",
              background: "transparent",
              border: "none",
              color: "#64748b",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "color 0.15s",
              textAlign: "left",
            }}
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        )}
      </aside>

      <div className="cp-workspace" style={{ background: "#f8faf7", minHeight: "100vh" }}>
        {/* Topbar matching Image 2 */}
        <header
          className="cp-topbar"
          style={{
            height: "70px",
            padding: "0 36px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "transparent",
            borderBottom: "none",
          }}
        >
          {/* Breadcrumb matching Mockup */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#64748b" }}>
            <span style={{ color: "#94a3b8" }}>Workspace</span>
            <ChevronRight size={14} style={{ color: "#cbd5e1" }} />
            <strong style={{ color: "#0f172a", fontWeight: 600 }}>
              {pathname.includes("/research-demo")
                ? "Research Lab (2025-2026)"
                : pathname.includes("risk-analysis")
                  ? "Risk Analysis"
                  : pathname.includes("suggested-crops")
                    ? "Suggested Crops"
                    : pathname.includes("cultivation-methods") || pathname.includes("cultivation-plan")
                      ? "Cultivation Planning"
                      : pathname.includes("plans")
                        ? "My Farm Plans"
                        : "Dashboard"}
            </strong>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            {/* Notification Bell */}
            <div
              style={{
                position: "relative",
                cursor: "pointer",
                color: "#475569",
                padding: "8px",
                borderRadius: "50%",
                background: "#ffffff",
                boxShadow: "0 2px 6px rgba(0,0,0,0.04)",
              }}
            >
              <Bell size={18} />
              <span
                style={{
                  position: "absolute",
                  top: "6px",
                  right: "6px",
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: "#ef4444",
                  border: "2px solid #ffffff",
                }}
              />
            </div>

            {/* Farmer Profile Pill */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "#ffffff",
                padding: "6px 14px 6px 8px",
                borderRadius: "9999px",
                boxShadow: "0 2px 6px rgba(0,0,0,0.04)",
              }}
            >
              <span
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  background: "#15803d",
                  color: "#ffffff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "13px",
                }}
              >
                {farmerInitial}
              </span>
              <div>
                <strong style={{ fontSize: "13px", color: "#0f172a", display: "block", lineHeight: 1.2 }}>
                  {farmerName}
                </strong>
                <small style={{ fontSize: "10px", color: "#64748b" }}>Farmer</small>
              </div>
            </div>

            <Button
              className="cp-menu-toggle"
              variant="ghost"
              size="icon"
              aria-label={open ? "Close navigation" : "Open navigation"}
              aria-expanded={open}
              aria-controls="cp-farmer-mobile"
              onClick={() => setOpen((value) => !value)}
            >
              {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </Button>
          </div>
        </header>

        {open && (
          <nav id="cp-farmer-mobile" className="cp-mobile-workspace" aria-label="Mobile farmer navigation">
            {links}
            <Link href={ROOT} onClick={() => setOpen(false)}>
              Public home
            </Link>
            {session && (
              <Button variant="ghost" onClick={() => void logout()}>
                <LogOut size={17} aria-hidden="true" />
                Log out
              </Button>
            )}
          </nav>
        )}

        <main id="crop-main" style={{ padding: "0 36px 48px" }}>
          <Protected>{children}</Protected>
        </main>
      </div>
    </div>
  );
}
