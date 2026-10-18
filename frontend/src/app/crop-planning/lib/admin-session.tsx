"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export interface AdminAccount {
  admin_id: string;
  login_identifier: string;
  full_name: string;
  role: "admin" | "officer";
  authentication_method: string;
  created_at: string;
}

export interface AdminSession {
  access_token: string;
  token_type: string;
  expires_in: number;
  expires_at: string;
  admin: AdminAccount;
}

interface AdminSessionContextType {
  session: AdminSession | null;
  loading: boolean;
  login: (credentials: { login_identifier: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  token: string | null;
}

const AdminSessionContext = createContext<AdminSessionContextType | null>(null);

export function AdminSessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const baseUrl = process.env.NEXT_PUBLIC_CULTIVATION_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("agfarm_admin_session");
      if (saved) {
        const parsed: AdminSession = JSON.parse(saved);
        if (parsed.expires_at && Date.parse(parsed.expires_at) > Date.now()) {
          setSession(parsed);
        } else {
          sessionStorage.removeItem("agfarm_admin_session");
        }
      }
    } catch {
      // Ignore sessionStorage parsing errors
    } finally {
      setLoading(false);
    }
  }, []);

  async function login(credentials: { login_identifier: string; password: string }) {
    const res = await fetch(`${baseUrl}/api/admin/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    });

    if (!res.ok) {
      let message = "Invalid admin credentials or account is disabled.";
      try {
        const body = await res.json();
        if (body.detail) message = typeof body.detail === "string" ? body.detail : "Login failed.";
      } catch {
        // use default error message
      }
      throw new Error(message);
    }

    const data: AdminSession = await res.json();
    setSession(data);
    sessionStorage.setItem("agfarm_admin_session", JSON.stringify(data));
  }

  async function logout() {
    if (session?.access_token) {
      try {
        await fetch(`${baseUrl}/api/admin/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
      } catch {
        // Ignore network errors on logout
      }
    }
    setSession(null);
    sessionStorage.removeItem("agfarm_admin_session");
    router.replace("/crop-planning/admin/login");
  }

  return (
    <AdminSessionContext.Provider
      value={{
        session,
        loading,
        login,
        logout,
        token: session?.access_token || null,
      }}
    >
      {children}
    </AdminSessionContext.Provider>
  );
}

export function useAdminSession() {
  const context = useContext(AdminSessionContext);
  if (!context) {
    throw new Error("useAdminSession must be used within an AdminSessionProvider");
  }
  return context;
}
