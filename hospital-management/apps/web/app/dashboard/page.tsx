"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import {
  DailySummary,
  getDailySummary,
  getExpenseTrend,
  getOpSummary,
  getRevenueTrend,
  OpSummary,
  TrendPoint,
} from "@/src/lib/api";
import { getRole, getToken } from "@/src/lib/auth";

function formatInr(value: number): string {
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function trendDelta(points: TrendPoint[]): string {
  if (points.length < 2) return "0%";
  const latest = points[points.length - 1]?.value ?? 0;
  const prev = points[points.length - 2]?.value ?? 0;
  if (prev === 0) return latest === 0 ? "0%" : "+100%";
  const pct = ((latest - prev) / prev) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export default function DashboardPage() {
  const role = getRole();
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [opSummary, setOpSummary] = useState<OpSummary | null>(null);
  const [revenueTrend, setRevenueTrend] = useState<TrendPoint[]>([]);
  const [expenseTrend, setExpenseTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      const token = getToken();
      if (!token) return;

      setLoading(true);
      setError("");

      try {
        const [daily, op, revenue, expense] = await Promise.all([
          getDailySummary(token),
          getOpSummary(token),
          getRevenueTrend(token, 7),
          getExpenseTrend(token, 7),
        ]);

        setSummary(daily);
        setOpSummary(op);
        setRevenueTrend(revenue);
        setExpenseTrend(expense);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load dashboard reports";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    void loadDashboard();
  }, []);

  const kpis = [
    {
      label: "Today OP Count",
      value: summary ? String(summary.op_count) : "-",
      trend: trendDelta(revenueTrend),
    },
    {
      label: "Pending Queue",
      value: summary ? String(summary.pending_queue) : "-",
      trend: opSummary ? `${opSummary.waiting} waiting / ${opSummary.prescription_ready} ready` : "-",
    },
    {
      label: "Revenue Today",
      value: summary ? formatInr(summary.revenue) : "-",
      trend: trendDelta(revenueTrend),
    },
    {
      label: "Expenses Today",
      value: summary ? formatInr(summary.expenses) : "-",
      trend: trendDelta(expenseTrend),
    },
  ];

  return (
    <AuthGuard allowedRoles={["admin", "doctor", "laboratory", "medical"]}>
      <AppShell>
        <section className="page-head theme-banner theme-dashboard">
          <h1>Operational Dashboard</h1>
          <p>Single view of OP flow, billing progress, and financial pulse.</p>
        </section>

        {error && <p className="error">{error}</p>}
        {loading && <p>Loading dashboard reports...</p>}

        <section className="kpi-grid">
          {kpis.map((kpi) => (
            <article key={kpi.label} className="kpi-card">
              <p className="kpi-label">{kpi.label}</p>
              <p className="kpi-value">{kpi.value}</p>
              <p className="kpi-trend">{kpi.trend}</p>
            </article>
          ))}
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>Today Queue Summary</h2>
              <span className="chip">Live</span>
            </div>
            {opSummary ? (
              <ul className="list-clean">
                <li>Total Visits - {opSummary.total}</li>
                <li>Waiting - {opSummary.waiting}</li>
                <li>In Consultation - {opSummary.in_consultation}</li>
                <li>Lab Processing - {opSummary.lab_processing}</li>
                <li>Ready For Medical - {opSummary.prescription_ready}</li>
                <li>Completed - {opSummary.completed}</li>
                <li>Cancelled - {opSummary.cancelled}</li>
              </ul>
            ) : (
              <p>No queue summary available.</p>
            )}
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Quick Actions</h2>
            </div>
            <div className="action-grid">
              {(role === "admin" || role === "doctor") && (
                <Link href="/doctor" className="action-card">
                  Doctor Queue
                </Link>
              )}
              {role === "admin" && (
                <Link href="/admin/users" className="action-card">
                  Manage Users
                </Link>
              )}
              {role === "admin" && (
                <Link href="/op" className="action-card">
                  Open OP Desk
                </Link>
              )}
              {(role === "admin" || role === "medical" || role === "doctor") && (
                <Link href="/medical-bill" className="action-card">
                  Generate Bills
                </Link>
              )}
              {(role === "admin" || role === "doctor") && (
                <Link href="/expenses" className="action-card">
                  Add Expense
                </Link>
              )}
              {(role === "admin" || role === "laboratory" || role === "doctor") && (
                <Link href="/reports/daily-print" className="action-card">
                  Daily Report
                </Link>
              )}
            </div>
            {summary && (
              <div className="summary-row total" style={{ marginTop: "14px" }}>
                <span>Net Collection</span>
                <strong>{formatInr(summary.net_collection)}</strong>
              </div>
            )}
          </article>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
