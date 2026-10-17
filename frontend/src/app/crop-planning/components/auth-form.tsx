"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  ShieldCheck,
  Sparkles,
  Sprout,
  User,
} from "lucide-react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Card, ErrorNotice, Field, inputProps, Notice } from "./ui";
import { useSession } from "./session";
import { ApiError } from "../lib/api";
import { validateCredentials } from "../lib/validation";

export default function AuthForm({ registration = false }: { registration?: boolean }) {
  const { api, signIn, notice, session } = useSession();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [show, setShow] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);

  const validation = validateCredentials({ login_identifier: identifier, password }, registration);
  if (registration && confirmation !== password) validation.confirmation = "Passwords must match.";
  const fieldError = (name: string) => fields[name] || (touched[name] ? validation[name] : undefined);
  const length = Array.from(password).length;

  function change(name: string, value: string) {
    ({ login_identifier: setIdentifier, password: setPassword, confirmation: setConfirmation }[name] as (value: string) => void)(value);
    setFields((previous) => ({ ...previous, [name]: "" }));
    setTouched((previous) => ({ ...previous, [name]: true }));
    setError(null);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    const credentials = { login_identifier: identifier.trim().toLowerCase(), password };
    setFields(validation);
    setTouched({ login_identifier: true, password: true, confirmation: true });
    if (Object.keys(validation).length) return;
    setBusy(true);
    try {
      if (registration) {
        await api.register(credentials);
        setSuccess(true);
        setPassword("");
        setConfirmation("");
      } else {
        await signIn(credentials);
        setPassword("");
        router.replace("/crop-planning/dashboard");
      }
    } catch (reason) {
      setError(reason);
      if (reason instanceof ApiError) setFields(reason.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cp-root cp-public cp-auth-page">
      <header className="portal-navbar">
        <div className="portal-navbar-inner">
          <Link href="/" className="portal-logo-group">
            <div className="portal-logo-icon"><Sprout size={26} /></div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span className="portal-logo-text">AgroDecision</span>
                <span style={{ fontSize: "11px", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", backgroundColor: "#dcfce7", color: "#166534" }}>AI</span>
              </div>
              <div className="portal-logo-tag">Your Farming Partner • AIMS Research</div>
            </div>
          </Link>
          <nav className="portal-nav-links" aria-label="Main navigation">
            <Link href="/">Home</Link>
            <Link href="/#about">About Us</Link>
            <Link href="/#features">Key Features</Link>
            <Link href="/#how-it-works">How It Works</Link>
            <Link href="/#services">Our Services</Link>
            <Link href="/#sdgs">SDGs</Link>
            <Link href="/#testimonials">Testimonials</Link>
          </nav>
          <div className="portal-nav-actions">
            <Link href="/crop-planning/login" className="portal-btn-login">Login</Link>
            <Link href="/crop-planning/register" className="portal-btn-signup">Sign Up <ArrowRight size={15} /></Link>
          </div>
        </div>
      </header>

      <main>
        <section className="cp-auth-layout cp-container">
          <aside className="cp-auth-story">
        <Image
          src="/crop-planning/agfarm_aerial.jpg"
          alt="Aerial view of lush green agricultural paddy fields"
          fill
          priority
          sizes="(max-width: 800px) 100vw, 45vw"
          className="cp-field-image"
        />
        <div className="cp-auth-story-overlay" />
        <div className="cp-auth-story-copy">
          <span className="cp-pill">
            <Sprout size={16} aria-hidden="true" />
            ROOTED IN YOUR NEXT SEASON
          </span>
          <h2>
            Your farm.<br />
            A fresh start.<br />
            <em>A clearer plan.</em>
          </h2>
          <p>A private workspace for your cultivation records, concentration risk analysis, and approved agricultural planning activities.</p>
          <span className="cp-auth-story-note">
            <ShieldCheck size={18} aria-hidden="true" />
            Thoughtful planning · Complete privacy preservation
          </span>
        </div>
          </aside>

          <div className="cp-auth-form-panel">
        <div className="cp-auth-card">
          <div className="cp-auth-card-header">
            <span className="cp-brand-mark mb-3">
              <Sprout size={22} strokeWidth={2.2} aria-hidden="true" />
            </span>
            <span className="cp-eyebrow">YOUR FARMER ACCOUNT</span>
            <h1>{registration ? "Start your next chapter." : "Good to see you again."}</h1>
            <p className="cp-auth-intro">
              {registration
                ? "Create a private workspace for your next cultivation season."
                : "Your cultivation plans are ready when you are."}
            </p>
          </div>

          {session ? (
            <Notice kind="success">
              You are logged in.{" "}
              <Link href="/crop-planning/dashboard">
                Open your workspace
                <ArrowRight size={14} aria-hidden="true" />
              </Link>
            </Notice>
          ) : success ? (
            <Card className="cp-auth-success">
              <span className="cp-success-symbol">
                <CheckCircle2 size={32} aria-hidden="true" />
              </span>
              <h2>Your account was created.</h2>
              <p>Log in with your new username and password to open your farmer workspace.</p>
              <Button asChild className="w-full">
                <Link href="/crop-planning/login">
                  Continue to login
                  <ArrowRight size={17} aria-hidden="true" />
                </Link>
              </Button>
            </Card>
          ) : (
            <form onSubmit={submit} noValidate className="cp-stack">
              {notice && <Notice kind="warning">{notice}</Notice>}
              <ErrorNotice error={error} />

              <Field
                label="Username"
                name="login_identifier"
                error={fieldError("login_identifier")}
                hint="3–100 letters, numbers, or . _ @ + -"
              >
                <Input
                  {...inputProps("login_identifier", fieldError("login_identifier"), true)}
                  value={identifier}
                  onChange={(event) => change("login_identifier", event.target.value)}
                  onBlur={() => setTouched((previous) => ({ ...previous, login_identifier: true }))}
                  placeholder="Your farmer username"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  maxLength={100}
                  disabled={busy}
                  required
                />
              </Field>

              <Field
                label="Password"
                name="password"
                error={fieldError("password")}
                hint={registration ? "15–128 characters. A memorable passphrase works well." : undefined}
              >
                <div className="cp-password-input">
                  <Input
                    {...inputProps("password", fieldError("password"), registration)}
                    type={show ? "text" : "password"}
                    value={password}
                    onChange={(event) => change("password", event.target.value)}
                    onBlur={() => setTouched((previous) => ({ ...previous, password: true }))}
                    placeholder={registration ? "Create a memorable passphrase" : "Your password"}
                    autoComplete={registration ? "new-password" : "current-password"}
                    className="pr-12"
                    disabled={busy}
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={show ? "Hide password" : "Show password"}
                    aria-pressed={show}
                    onClick={() => setShow((value) => !value)}
                  >
                    {show ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                  </Button>
                </div>
              </Field>

              {registration && (
                <>
                  <div className="cp-password-requirement">
                    <Check
                      size={14}
                      className={length >= 15 && length <= 128 ? "cp-check-met" : ""}
                      aria-hidden="true"
                    />
                    <span>
                      {length >= 15 && length <= 128
                        ? "Password length requirement met"
                        : "At least 15 characters; spaces are welcome"}
                    </span>
                  </div>

                  <Field label="Confirm password" name="confirmation" error={fieldError("confirmation")}>
                    <Input
                      {...inputProps("confirmation", fieldError("confirmation"))}
                      type={show ? "text" : "password"}
                      value={confirmation}
                      onChange={(event) => change("confirmation", event.target.value)}
                      onBlur={() => setTouched((previous) => ({ ...previous, confirmation: true }))}
                      placeholder="Enter your password again"
                      autoComplete="new-password"
                      disabled={busy}
                      required
                    />
                  </Field>
                </>
              )}

              <Button type="submit" disabled={busy} className="cp-auth-submit">
                {busy ? (
                  <Loader2 size={17} className="animate-spin" aria-hidden="true" />
                ) : (
                  <ArrowRight size={17} aria-hidden="true" />
                )}
                {busy ? "Please wait…" : registration ? "Create farmer account" : "Log in to your workspace"}
              </Button>

              <p className="cp-auth-switch">
                {registration ? "Already have an account? " : "New to AgFarm? "}
                <Link href={registration ? "/crop-planning/login" : "/crop-planning/register"}>
                  {registration ? "Log in" : "Create an account"}
                </Link>
              </p>
            </form>
          )}

          <div className="cp-auth-security">
            <ShieldCheck size={15} aria-hidden="true" />
            <span>Your session stays in this tab. Refreshing requires login again.</span>
          </div>
        </div>
          </div>
        </section>
      </main>

      <footer className="portal-footer">
        <div className="portal-container">
          <div className="portal-footer-grid">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <div style={{ width: "38px", height: "38px", borderRadius: "10px", background: "#15803d", display: "flex", alignItems: "center", justifyContent: "center", color: "#ffffff" }}><Sprout size={22} /></div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#ffffff" }}>AgroDecision AI</div>
                  <div style={{ fontSize: "11px", color: "#4ade80" }}>Better Farmers • Brighter Future</div>
                </div>
              </div>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#94a3b8", marginBottom: "16px" }}>
                Data-Driven Farmer Decision System for Collaborative Crop Planning and Market Risk Reduction.
              </p>
              <div style={{ fontSize: "12px", color: "#cbd5e1" }}>
                <strong>AIMS</strong> - Autonomous Intelligent Machines and Systems
                <br />Faculty of Computing • Information Technology (IT)
              </div>
            </div>
            <div className="portal-footer-col">
              <h4>Quick Links</h4>
              <ul>
                <li><Link href="/">Home</Link></li>
                <li><Link href="/#about">About Us</Link></li>
                <li><Link href="/#features">Key Features</Link></li>
                <li><Link href="/#services">Our Services</Link></li>
                <li><Link href="/crop-planning/login">Farmer Login</Link></li>
              </ul>
            </div>
            <div className="portal-footer-col">
              <h4>Research Modules</h4>
              <ul>
                <li><Link href="/crop-planning" style={{ color: "#4ade80", fontWeight: 700 }}>Component 02: Crop Planning (Live)</Link></li>
                <li><Link href="/#services">Component 01: Market Profit AI</Link></li>
                <li><Link href="/#services">Component 03: Produce Traceability & Waste</Link></li>
                <li><Link href="/#services">Component 04: Climate GIS Early Warning</Link></li>
              </ul>
            </div>
            <div className="portal-footer-col">
              <h4>Contact & Support</h4>
              <div style={{ fontSize: "13px", lineHeight: 1.8, color: "#94a3b8" }}>
                <div>+94 (0) 11 234 5678 / Support</div>
                <div>aims.research@agrodecision.lk</div>
                <div style={{ marginTop: "6px" }}>Faculty of Computing, Sri Lanka</div>
              </div>
            </div>
          </div>
          <div style={{ paddingTop: "28px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", fontSize: "12px", color: "#64748b" }}>
            <div>© 2026 AgroDecision AI. All rights reserved.</div>
            <div style={{ color: "#4ade80", fontWeight: 600 }}>Grow Together • Farmer • Technology • Prosperity 🌾</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
