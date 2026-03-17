"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import {
  DailySummary,
  DateRangeSummary,
  downloadCsvReport,
  ExpenseCategoryPoint,
  getDateRangeSummary,
  getDailySummary,
  getDoctorOpSummary,
  getExpenseCategorySummary,
  getOpSummary,
  DoctorOpSummaryPoint,
  OpSummary,
} from "@/src/lib/api";
import { getToken } from "@/src/lib/auth";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function offsetIsoDate(days: number): string {
  const now = new Date();
  now.setDate(now.getDate() + days);
  return now.toISOString().slice(0, 10);
}

function formatInr(value: number): string {
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export default function DailyPrintPage() {
  const [selectedDate, setSelectedDate] = useState(todayIsoDate());
  const [rangeStartDate, setRangeStartDate] = useState(offsetIsoDate(-6));
  const [rangeEndDate, setRangeEndDate] = useState(todayIsoDate());
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [opSummary, setOpSummary] = useState<OpSummary | null>(null);
  const [rangeSummary, setRangeSummary] = useState<DateRangeSummary | null>(null);
  const [doctorSummary, setDoctorSummary] = useState<DoctorOpSummaryPoint[]>([]);
  const [expenseByCategory, setExpenseByCategory] = useState<ExpenseCategoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [advancedLoading, setAdvancedLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadData(dateValue: string) {
    const token = getToken();
    if (!token) return;

    setLoading(true);
    setError("");
    try {
      const [daily, op] = await Promise.all([
        getDailySummary(token, dateValue),
        getOpSummary(token, dateValue),
      ]);
      setSummary(daily);
      setOpSummary(op);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load daily report";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(selectedDate);
  }, []);

  async function loadAdvancedData(startDate: string, endDate: string) {
    const token = getToken();
    if (!token) return;

    setAdvancedLoading(true);
    setError("");
    try {
      const [summaryData, doctorData, expenseData] = await Promise.all([
        getDateRangeSummary(token, startDate, endDate),
        getDoctorOpSummary(token, startDate, endDate),
        getExpenseCategorySummary(token, startDate, endDate),
      ]);
      setRangeSummary(summaryData);
      setDoctorSummary(doctorData);
      setExpenseByCategory(expenseData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load analytics";
      setError(message);
    } finally {
      setAdvancedLoading(false);
    }
  }

  useEffect(() => {
    void loadAdvancedData(rangeStartDate, rangeEndDate);
  }, []);

  async function handleExport(endpoint: string, filename: string) {
    const token = getToken();
    if (!token) return;
    try {
      await downloadCsvReport(token, endpoint, filename);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Export failed";
      setError(message);
    }
  }

  return (
    <AuthGuard allowedRoles={["admin", "doctor", "laboratory"]}>
      <AppShell>
        <section className="page-head theme-banner theme-dashboard">
          <h1>Daily Operations Report</h1>
          <p>Printable summary for finance and operations review.</p>
        </section>

        <section className="panel" style={{ marginTop: "14px" }}>
          <div className="panel-head">
            <h2>Report Controls</h2>
          </div>
          <div className="form-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
            <label>
              Report Date
              <input
                type="date"
                value={selectedDate}
                onChange={(event) => setSelectedDate(event.target.value)}
              />
            </label>
            <button type="button" onClick={() => void loadData(selectedDate)}>
              Refresh Report
            </button>
            <button type="button" onClick={() => window.print()} className="secondary-btn">
              Print Report
            </button>
            <button
              type="button"
              onClick={() =>
                void handleExport(
                  `/api/v1/reports/daily-summary.pdf?date=${selectedDate}`,
                  `daily-summary-${selectedDate}.pdf`,
                )
              }
            >
              Download PDF
            </button>
          </div>
          <div className="action-grid" style={{ marginTop: "12px" }}>
            <button
              type="button"
              onClick={() =>
                void handleExport(
                  `/api/v1/reports/daily-summary.csv?date=${selectedDate}`,
                  `daily-summary-${selectedDate}.csv`,
                )
              }
            >
              Download Daily Summary CSV
            </button>
            <button
              type="button"
              onClick={() =>
                void handleExport(
                  `/api/v1/reports/op-visits.csv?date=${selectedDate}`,
                  `op-visits-${selectedDate}.csv`,
                )
              }
            >
              Download OP CSV
            </button>
            <button
              type="button"
              onClick={() =>
                void handleExport(
                  `/api/v1/reports/medical-bills.csv?date=${selectedDate}`,
                  `medical-bills-${selectedDate}.csv`,
                )
              }
            >
              Download Bills CSV
            </button>
            <button
              type="button"
              onClick={() =>
                void handleExport(
                  `/api/v1/reports/expenses.csv?date=${selectedDate}`,
                  `expenses-${selectedDate}.csv`,
                )
              }
            >
              Download Expenses CSV
            </button>
          </div>
        </section>

        <section className="panel" style={{ marginTop: "14px" }}>
          <div className="panel-head">
            <h2>Advanced Analytics</h2>
          </div>
          <div className="form-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
            <label>
              Start Date
              <input
                type="date"
                value={rangeStartDate}
                onChange={(event) => setRangeStartDate(event.target.value)}
              />
            </label>
            <label>
              End Date
              <input
                type="date"
                value={rangeEndDate}
                onChange={(event) => setRangeEndDate(event.target.value)}
              />
            </label>
            <button type="button" onClick={() => void loadAdvancedData(rangeStartDate, rangeEndDate)}>
              Load Range Analytics
            </button>
          </div>

          {advancedLoading && <p style={{ marginTop: "10px" }}>Loading analytics...</p>}

          {rangeSummary && (
            <div style={{ marginTop: "14px" }}>
              <h3>
                Range Summary ({rangeSummary.start_date} to {rangeSummary.end_date})
              </h3>
              <div className="summary-row"><span>Total OP Visits</span><strong>{rangeSummary.op_count}</strong></div>
              <div className="summary-row"><span>Revenue</span><strong>{formatInr(rangeSummary.revenue)}</strong></div>
              <div className="summary-row"><span>Expenses</span><strong>{formatInr(rangeSummary.expenses)}</strong></div>
              <div className="summary-row total"><span>Net Collection</span><strong>{formatInr(rangeSummary.net_collection)}</strong></div>
            </div>
          )}

          <div className="split-grid" style={{ marginTop: "14px" }}>
            <article className="panel">
              <h3>Doctor-wise OP</h3>
              {doctorSummary.length === 0 ? (
                <p>No doctor OP records in selected range.</p>
              ) : (
                <ul className="list-clean">
                  {doctorSummary.map((row) => (
                    <li key={row.doctor_name}>
                      {row.doctor_name} - {row.total_visits} visits ({row.completed_visits} completed)
                    </li>
                  ))}
                </ul>
              )}
            </article>
            <article className="panel">
              <h3>Expense by Category</h3>
              {expenseByCategory.length === 0 ? (
                <p>No expense records in selected range.</p>
              ) : (
                <ul className="list-clean">
                  {expenseByCategory.map((row) => (
                    <li key={row.category}>
                      {row.category} - {formatInr(row.amount)}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </div>
        </section>

        {loading && <p>Loading report...</p>}
        {error && <p className="error">{error}</p>}

        <section className="print-report" style={{ marginTop: "14px" }}>
          <article className="panel print-block">
            <h2>Sri Laxmi Hospital</h2>
            <p>Happy Mother and Safe Children</p>
            <p>
              <strong>Date:</strong> {selectedDate}
            </p>
          </article>

          <article className="panel print-block">
            <h2>Financial Summary</h2>
            <div className="summary-row"><span>Revenue</span><strong>{formatInr(summary?.revenue ?? 0)}</strong></div>
            <div className="summary-row"><span>Expenses</span><strong>{formatInr(summary?.expenses ?? 0)}</strong></div>
            <div className="summary-row total"><span>Net Collection</span><strong>{formatInr(summary?.net_collection ?? 0)}</strong></div>
          </article>

          <article className="panel print-block">
            <h2>OP Summary</h2>
            <ul className="list-clean">
              <li>Total Visits - {opSummary?.total ?? 0}</li>
              <li>Waiting - {opSummary?.waiting ?? 0}</li>
              <li>In Consultation - {opSummary?.in_consultation ?? 0}</li>
              <li>Lab Processing - {opSummary?.lab_processing ?? 0}</li>
              <li>Ready For Medical - {opSummary?.prescription_ready ?? 0}</li>
              <li>Completed - {opSummary?.completed ?? 0}</li>
              <li>Cancelled - {opSummary?.cancelled ?? 0}</li>
            </ul>
          </article>

          <article className="panel print-block">
            <h2>Sign Off</h2>
            <p>Prepared by: ____________________</p>
            <p>Verified by: ____________________</p>
            <p>Authorized signatory: ____________________</p>
          </article>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
