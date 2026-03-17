"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { clearSession, getRole, getToken } from "@/src/lib/auth";

export default function NoAccessPage() {
  const router = useRouter();
  const role = getRole();
  const token = getToken();

  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [router, token]);

  function handleGoHome() {
    if (!role) {
      router.replace("/login");
      return;
    }
    if (role === "operations") {
      router.replace("/op");
      return;
    }
    if (role === "medical") {
      router.replace("/medical-bill");
      return;
    }
    if (role === "laboratory") {
      router.replace("/laboratory");
      return;
    }
    if (role === "doctor") {
      router.replace("/doctor");
      return;
    }
    router.replace("/dashboard");
  }

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

  if (!token) {
    return null;
  }

  return (
    <main className="login-layout">
      <section className="auth-card">
        <h2>No Access</h2>
        <p className="muted">You do not have permission to open this page.</p>
        <p className="muted">Current role: {role ?? "unknown"}</p>
        <button type="button" onClick={handleGoHome}>
          Go To Allowed Page
        </button>
        <button type="button" className="secondary-btn" onClick={handleLogout}>
          Logout
        </button>
      </section>
    </main>
  );
}
