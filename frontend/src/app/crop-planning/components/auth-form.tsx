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
  );
}
