"use client";
import { Button } from "./ui/button";
import { Card, Notice } from "./ui";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { createApi, type FarmerApi } from "../lib/api";
import type { Credentials, Session } from "../lib/contracts";

interface SessionContext { session: Session | null; api: FarmerApi; notice: string; signIn: (credentials: Credentials) => Promise<void>; signOut: () => Promise<void> }
const Context = createContext<SessionContext | null>(null);
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [notice, setNotice] = useState("");
  const current = useRef<Session | null>(null);
  const generation = useRef(0);
  const clear = useCallback((message = "") => {
    generation.current++;
    current.current = null;
    setSession(null);
    setNotice(message);
    if (typeof window !== "undefined" && window.sessionStorage) {
      try { window.sessionStorage.removeItem("agfarm_session"); } catch { }
    }
  }, []);
  const api = useMemo(() => createApi(process.env.NEXT_PUBLIC_CULTIVATION_API_URL || "http://127.0.0.1:8000", () => current.current?.access_token ?? null, () => clear("Your session has expired or was revoked. Please log in again.")), [clear]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    try {
      const saved = window.sessionStorage.getItem("agfarm_session");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.access_token && Date.parse(parsed.expires_at) > Date.now()) {
          current.current = parsed;
          setSession(parsed);
        }
      }
    } catch { }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    try {
      if (session) {
        window.sessionStorage.setItem("agfarm_session", JSON.stringify(session));
      } else {
        window.sessionStorage.removeItem("agfarm_session");
      }
    } catch { }
  }, [session]);

  useEffect(() => {
    if (!session) return;
    const remaining = Date.parse(session.expires_at) - Date.now();
    const timer = setTimeout(() => clear("Your session has expired. Please log in again."), Math.max(0, Math.min(remaining, 2147483647)));
    return () => clearTimeout(timer);
  }, [session, clear]);
  async function signIn(credentials: Credentials) {
    const attempt = ++generation.current;
    const result = await api.login(credentials);
    if (attempt !== generation.current) return;
    current.current = result;
    try {
      const farmer = await api.me();
      if (attempt !== generation.current) return;
      const verified = { ...result, farmer };
      current.current = verified; setSession(verified); setNotice("");
    } catch (error) { if (attempt === generation.current) clear(); throw error; }
  }
  async function signOut() {
    const pending = api.logout();
    clear();
    try { await pending; } catch { setNotice("Logged out on this device. Server revocation could not be confirmed; the session will expire automatically."); }
  }
  return <Context.Provider value={{ session, api, notice, signIn, signOut }}>{children}</Context.Provider>;
}
export function useSession() { const value = useContext(Context); if (!value) throw new Error("SessionProvider is required"); return value; }
export function AccessGate({ authenticated, notice, children }: { authenticated: boolean; notice?: string; children: React.ReactNode }) {
  if (!authenticated) return <Card className="cp-access [&>div]:p-6 sm:[&>div]:p-10"><span className="cp-eyebrow">YOUR FARM, YOUR RECORDS</span><h1>A little planning goes a long way.</h1><p>Log in to manage your cultivation plans and explore the evidence available for your next season.</p>{notice && <Notice kind="warning">{notice}</Notice>}<div className="cp-actions"><Button asChild><Link href="/crop-planning/login">Log in</Link></Button><Button asChild variant="outline"><Link href="/crop-planning/register">Create an account</Link></Button></div><p className="cp-muted">Your session stays in this tab’s memory. Refreshing requires a new login.</p></Card>;
  return <>{children}</>;
}
export function Protected({ children }: { children: React.ReactNode }) { const { session, notice } = useSession(); return <AccessGate authenticated={!!session} notice={notice}>{children}</AccessGate>; }

