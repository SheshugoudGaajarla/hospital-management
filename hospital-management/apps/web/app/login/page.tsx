"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/src/lib/api";
import { AppRole, setSession } from "@/src/lib/auth";

function defaultRouteByRole(role: AppRole): string {
  if (role === "operations") return "/op";
  if (role === "medical") return "/medical-bill";
  if (role === "laboratory") return "/laboratory";
  return "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await login(username, password);
      setSession(response.access_token, response.role);
      router.push(defaultRouteByRole(response.role));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-hero">
        <p className="hero-badge">Sri Laxmi Hospital</p>
        <h1>Happy Mother and Safe Children</h1>
        <p>
          Designed for operations, doctors, medical, laboratory, and admin teams with secure, clear workflows.
        </p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <h2>Sign In</h2>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </main>
  );
}
