"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import {
  createMedicalBill,
  downloadReportFile,
  listMedicalBills,
  listOpVisits,
  MedicalBillRecord,
  OpVisit,
  updateMedicalBill,
} from "@/src/lib/api";
import { getToken } from "@/src/lib/auth";

function parseNonNegative(value: string): number {
  const parsed = Number(value);
  if (Number.isNaN(parsed) || parsed < 0) {
    throw new Error("All amounts must be valid non-negative numbers");
  }
  return parsed;
}

function prettyVisitStatus(status: OpVisit["status"]): string {
  if (status === "prescription_ready") return "Ready For Medical";
  if (status === "lab_processing") return "Lab Processing";
  if (status === "in_consultation") return "With Doctor";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function MedicalBillPage() {
  const [visits, setVisits] = useState<OpVisit[]>([]);
  const [bills, setBills] = useState<MedicalBillRecord[]>([]);
  const [selectedVisitId, setSelectedVisitId] = useState("");
  const [medicineFee, setMedicineFee] = useState("0");
  const [discount, setDiscount] = useState("0");
  const [tax, setTax] = useState("0");
  const [paymentMode, setPaymentMode] = useState("cash");
  const [billStatus, setBillStatus] = useState<"paid" | "unpaid">("paid");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionLoadingBillId, setActionLoadingBillId] = useState<number | null>(null);

  async function loadData() {
    const token = getToken();
    if (!token) return;

    try {
      const [visitRows, billRows] = await Promise.all([listOpVisits(token), listMedicalBills(token)]);
      setVisits(visitRows.filter((visit) => visit.status !== "cancelled" && visit.status !== "completed"));
      setBills(billRows);
      if (!selectedVisitId && visitRows.length > 0) {
        const activeVisit = visitRows.find((visit) => visit.status !== "cancelled" && visit.status !== "completed");
        if (activeVisit) setSelectedVisitId(String(activeVisit.id));
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load billing data";
      setError(message);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const selectedVisit = useMemo(
    () => visits.find((visit) => visit.id === Number(selectedVisitId)),
    [selectedVisitId, visits],
  );

  const medicineFeeNumber = useMemo(() => {
    const parsed = Number(medicineFee);
    return Number.isFinite(parsed) ? parsed : NaN;
  }, [medicineFee]);

  const netAmount = useMemo(() => {
    const subtotal = Number(medicineFee || 0);
    return Math.max(0, subtotal - Number(discount || 0) + Number(tax || 0));
  }, [medicineFee, discount, tax]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token || !selectedVisit) {
      setError("Select a valid OP visit before billing");
      return;
    }

    if (parseNonNegative(medicineFee) <= 0) {
      setError("Medicine fee must be greater than zero");
      return;
    }
    if (netAmount <= 0) {
      setError("Net payable must be greater than zero");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await createMedicalBill(token, {
        patient_id: selectedVisit.patient_id,
        op_visit_id: selectedVisit.id,
        medicine_fee: parseNonNegative(medicineFee),
        lab_fee: 0,
        discount: parseNonNegative(discount),
        tax: parseNonNegative(tax),
        payment_mode: paymentMode,
        status: billStatus,
      });
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create medical bill";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusUpdate(bill: MedicalBillRecord, nextStatus: "paid" | "refunded") {
    const token = getToken();
    if (!token) return;

    let refundReason: string | undefined;
    if (nextStatus === "refunded") {
      const entered = window.prompt("Enter refund reason");
      if (!entered || entered.trim().length < 3) {
        setError("Refund reason is required (minimum 3 characters).");
        return;
      }
      refundReason = entered.trim();
    }

    setError("");
    setActionLoadingBillId(bill.id);
    try {
      await updateMedicalBill(token, bill.id, {
        status: nextStatus,
        payment_mode: bill.payment_mode,
        refund_reason: refundReason,
      });
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update bill status";
      setError(message);
    } finally {
      setActionLoadingBillId(null);
    }
  }

  async function handleDownloadInvoice(bill: MedicalBillRecord) {
    const token = getToken();
    if (!token) return;
    setError("");
    setActionLoadingBillId(bill.id);
    try {
      await downloadReportFile(
        token,
        `/api/v1/medical-bills/${bill.id}/invoice.pdf`,
        `${bill.invoice_no}.pdf`,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to download invoice";
      setError(message);
    } finally {
      setActionLoadingBillId(null);
    }
  }

  return (
    <AuthGuard allowedRoles={["admin", "medical", "doctor"]}>
      <AppShell>
        <section className="page-head theme-banner theme-billing">
          <h1>Medical Billing</h1>
          <p>Record medicine billing only. OP consultation fee is collected at registration, and lab payment is collected in laboratory.</p>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>Create Bill</h2>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                Select OP Visit
                <select
                  value={selectedVisitId}
                  onChange={(event) => setSelectedVisitId(event.target.value)}
                  required
                >
                  {visits.length === 0 ? (
                    <option value="">No active visits available</option>
                  ) : (
                    visits.map((visit) => (
                      <option key={visit.id} value={visit.id}>
                        Token {visit.token_no} - {visit.patient_name} ({prettyVisitStatus(visit.status)})
                      </option>
                    ))
                  )}
                </select>
              </label>
              <label>
                Medicine Fee
                <input value={medicineFee} onChange={(e) => setMedicineFee(e.target.value)} required />
              </label>
              <label>
                Discount
                <input value={discount} onChange={(e) => setDiscount(e.target.value)} required />
              </label>
              <label>
                Tax
                <input value={tax} onChange={(e) => setTax(e.target.value)} required />
              </label>
              <label>
                Payment Mode
                <select value={paymentMode} onChange={(e) => setPaymentMode(e.target.value)}>
                  <option value="cash">Cash</option>
                  <option value="card">Card</option>
                  <option value="upi">UPI</option>
                </select>
              </label>
              <label>
                Initial Status
                <select value={billStatus} onChange={(e) => setBillStatus(e.target.value as "paid" | "unpaid")}>
                  <option value="paid">Paid</option>
                  <option value="unpaid">Unpaid</option>
                </select>
              </label>
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={loading || visits.length === 0 || !Number.isFinite(medicineFeeNumber) || medicineFeeNumber <= 0 || netAmount <= 0}>
                {loading ? "Creating..." : "Confirm Payment"}
              </button>
            </form>
          </article>

          <article className="panel sticky-summary">
            <div className="panel-head">
              <h2>Bill Summary</h2>
            </div>
            <div className="summary-row">
              <span>Patient</span>
              <strong>{selectedVisit?.patient_name ?? "-"}</strong>
            </div>
            <div className="summary-row">
              <span>OP Consultation Fee</span>
              <strong>₹{selectedVisit ? selectedVisit.consultation_fee.toFixed(2) : "0.00"} collected</strong>
            </div>
            <div className="summary-row">
              <span>Subtotal</span>
              <strong>
                ₹
                {Number(medicineFee || 0).toFixed(2)}
              </strong>
            </div>
            <div className="summary-row">
              <span>Discount</span>
              <strong>-₹{Number(discount || 0).toFixed(2)}</strong>
            </div>
            <div className="summary-row">
              <span>Tax</span>
              <strong>₹{Number(tax || 0).toFixed(2)}</strong>
            </div>
            <div className="summary-row total">
              <span>Net Payable</span>
              <strong>₹{netAmount.toFixed(2)}</strong>
            </div>
          </article>
        </section>

        <section className="panel" style={{ marginTop: "14px" }}>
          <div className="panel-head">
            <h2>Recent Bills</h2>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Patient</th>
                <th>Amount</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bills.length === 0 ? (
                <tr>
                  <td colSpan={6}>No bills generated yet.</td>
                </tr>
              ) : (
                bills.slice(0, 10).map((bill) => (
                  <tr key={bill.id}>
                    <td>{bill.invoice_no}</td>
                    <td>{bill.patient_name}</td>
                    <td>₹{bill.net_amount.toFixed(2)}</td>
                    <td>{bill.payment_mode}</td>
                    <td>{bill.status}</td>
                    <td>
                      <button type="button" onClick={() => void handleDownloadInvoice(bill)}>
                        Invoice PDF
                      </button>
                      {bill.status === "unpaid" && (
                        <button
                          type="button"
                          onClick={() => void handleStatusUpdate(bill, "paid")}
                          disabled={actionLoadingBillId === bill.id}
                        >
                          Mark Paid
                        </button>
                      )}
                      {bill.status === "paid" && (
                        <button
                          type="button"
                          onClick={() => void handleStatusUpdate(bill, "refunded")}
                          disabled={actionLoadingBillId === bill.id}
                        >
                          Refund
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
