"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import { createExpense, ExpenseRecord, getExpenseSummary, listExpenses } from "@/src/lib/api";
import { getToken } from "@/src/lib/auth";

export default function ExpensesPage() {
  const [category, setCategory] = useState("supplies");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [expenses, setExpenses] = useState<ExpenseRecord[]>([]);
  const [todayTotal, setTodayTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadExpenses() {
    const token = getToken();
    if (!token) return;

    try {
      const [expenseRows, summary] = await Promise.all([listExpenses(token), getExpenseSummary(token)]);
      setExpenses(expenseRows);
      setTodayTotal(summary.total_amount);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load expenses";
      setError(message);
    }
  }

  useEffect(() => {
    void loadExpenses();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;

    const numericAmount = Number(amount);
    if (Number.isNaN(numericAmount) || numericAmount <= 0) {
      setError("Amount must be greater than zero");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await createExpense(token, {
        category,
        amount: numericAmount,
        notes: notes.trim(),
      });
      setAmount("");
      setNotes("");
      await loadExpenses();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save expense";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard allowedRoles={["admin", "doctor"]}>
      <AppShell>
        <section className="page-head theme-banner theme-expenses">
          <h1>Expenses Control</h1>
          <p>Track operational spend with category-level visibility.</p>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>Add Expense</h2>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                Category
                <select value={category} onChange={(event) => setCategory(event.target.value)}>
                  <option value="supplies">Supplies</option>
                  <option value="staff">Staff</option>
                  <option value="utilities">Utilities</option>
                  <option value="maintenance">Maintenance</option>
                </select>
              </label>
              <label>
                Amount
                <input
                  placeholder="₹0.00"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  required
                />
              </label>
              <label>
                Notes
                <input
                  placeholder="Expense description"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                />
              </label>
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={loading}>
                {loading ? "Saving..." : "Save Expense"}
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Recent Expenses</h2>
            </div>
            <ul className="list-clean">
              {expenses.length === 0 ? (
                <li>No expenses added yet.</li>
              ) : (
                expenses.slice(0, 6).map((expense) => (
                  <li key={expense.id}>
                    {expense.category} - ₹{expense.amount.toFixed(2)}
                  </li>
                ))
              )}
            </ul>
            <div className="summary-row total">
              <span>Today Total</span>
              <strong>₹{todayTotal.toFixed(2)}</strong>
            </div>
          </article>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
