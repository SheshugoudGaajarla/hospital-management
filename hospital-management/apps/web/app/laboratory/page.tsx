"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import {
  createLabOrder,
  downloadLabReport,
  LabCatalogItem,
  LabOrderRecord,
  LabOrderStatus,
  listLabCatalog,
  listLabOrders,
  listOpVisits,
  OpVisit,
  updateLabOrder,
} from "@/src/lib/api";
import { getToken } from "@/src/lib/auth";

function prettyVisitStatus(status: OpVisit["status"]): string {
  if (status === "in_consultation") return "With Doctor";
  if (status === "lab_processing") return "Lab Processing";
  if (status === "prescription_ready") return "Ready For Medical";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function LaboratoryPage() {
  const [orders, setOrders] = useState<LabOrderRecord[]>([]);
  const [visits, setVisits] = useState<OpVisit[]>([]);
  const [catalog, setCatalog] = useState<LabCatalogItem[]>([]);
  const [selectedVisitId, setSelectedVisitId] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState<"all" | "common" | "pediatrics" | "gynecology">("all");
  const [selectedTestCodes, setSelectedTestCodes] = useState<string[]>(["CBC"]);
  const [customTestName, setCustomTestName] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("0");
  const [paymentStatus, setPaymentStatus] = useState<"paid" | "unpaid">("paid");
  const [paymentMode, setPaymentMode] = useState("cash");
  const [statusFilter, setStatusFilter] = useState<"all" | LabOrderStatus>("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoadingOrderId, setActionLoadingOrderId] = useState<number | null>(null);

  async function loadData() {
    const token = getToken();
    if (!token) return;
    try {
      const [orderRows, visitRows, catalogRows] = await Promise.all([listLabOrders(token), listOpVisits(token), listLabCatalog(token)]);
      setOrders(orderRows);
      setVisits(visitRows);
      setCatalog(catalogRows);
      if (!selectedVisitId && visitRows.length > 0) {
        setSelectedVisitId(String(visitRows[0].id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load laboratory data");
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const filteredCatalog = useMemo(
    () => catalog.filter((item) => departmentFilter === "all" || item.department === "common" || item.department === departmentFilter),
    [catalog, departmentFilter],
  );

  const groupedCatalog = useMemo(() => {
    return filteredCatalog.reduce<Record<string, LabCatalogItem[]>>((acc, item) => {
      const key = item.department;
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});
  }, [filteredCatalog]);

  useEffect(() => {
    if (filteredCatalog.length === 0) return;
    const allowedCodes = new Set(filteredCatalog.map((item) => item.code));
    setSelectedTestCodes((current) => {
      const valid = current.filter((code) => allowedCodes.has(code));
      return valid.length > 0 ? valid : [filteredCatalog[0].code];
    });
  }, [filteredCatalog]);

  function toggleTestCode(code: string) {
    setSelectedTestCodes((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token || !selectedVisitId) return;
    setLoading(true);
    setError("");
    try {
      await createLabOrder(token, {
        op_visit_id: Number(selectedVisitId),
        test_codes: selectedTestCodes,
        custom_test_name: customTestName.trim() || undefined,
        payment_amount: Number(paymentAmount || 0),
        payment_status: paymentStatus,
        payment_mode: paymentStatus === "paid" ? paymentMode : undefined,
      });
      setCustomTestName("");
      setPaymentAmount("0");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create lab order");
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(order: LabOrderRecord, nextStatus: LabOrderStatus) {
    const token = getToken();
    if (!token) return;
    const needsResult = nextStatus === "completed";
    const result = needsResult ? window.prompt("Enter result summary") ?? "" : order.result_summary ?? "";
    if (needsResult && result.trim().length < 3) {
      setError("Result summary is required to complete a test");
      return;
    }
    setActionLoadingOrderId(order.id);
    setError("");
    try {
      await updateLabOrder(token, order.id, {
        status: nextStatus,
        result_summary: result.trim() || undefined,
      });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update lab order");
    } finally {
      setActionLoadingOrderId(null);
    }
  }

  async function handleCollectPayment(order: LabOrderRecord) {
    const token = getToken();
    if (!token) return;
    const amount = window.prompt("Enter collected amount", String(order.payment_amount));
    if (!amount) return;
    const mode = window.prompt("Enter payment mode: cash/card/upi", order.payment_mode ?? "cash");
    if (!mode) return;
    setActionLoadingOrderId(order.id);
    setError("");
    try {
      await updateLabOrder(token, order.id, {
        payment_amount: Number(amount),
        payment_status: "paid",
        payment_mode: mode.trim().toLowerCase(),
      });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update payment");
    } finally {
      setActionLoadingOrderId(null);
    }
  }

  async function handlePrint(order: LabOrderRecord) {
    const token = getToken();
    if (!token) return;
    setActionLoadingOrderId(order.id);
    setError("");
    try {
      await downloadLabReport(token, order.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to print lab report");
    } finally {
      setActionLoadingOrderId(null);
    }
  }

  const filteredOrders = useMemo(
    () => orders.filter((order) => statusFilter === "all" || order.status === statusFilter),
    [orders, statusFilter],
  );

  const selectedTestNames = useMemo(
    () => selectedTestCodes.map((code) => catalog.find((item) => item.code === code)?.name ?? code),
    [catalog, selectedTestCodes],
  );

  return (
    <AuthGuard allowedRoles={["admin", "laboratory"]}>
      <AppShell>
        <section className="page-head theme-banner theme-dashboard">
          <h1>Laboratory</h1>
          <p>Record tests from the doctor paper, collect lab payment, process status, and print the report.</p>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>New Lab Entry</h2>
            </div>
            <form className="form-grid" onSubmit={handleCreate}>
              <label>
                OP Visit
                <select value={selectedVisitId} onChange={(event) => setSelectedVisitId(event.target.value)} required>
                  {visits.length === 0 ? (
                    <option value="">No OP visits</option>
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
                Specialty Filter
                <select value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value as "all" | "common" | "pediatrics" | "gynecology")}>
                  <option value="all">All Tests</option>
                  <option value="pediatrics">Pediatrics + Common</option>
                  <option value="gynecology">Gynecology + Common</option>
                  <option value="common">Common Tests</option>
                </select>
              </label>
              <div className="selection-panel">
                <div className="selection-head">
                  <span>Tests</span>
                  <span className="muted">{selectedTestCodes.length} selected</span>
                </div>
                {selectedTestNames.length > 0 && (
                  <div className="selection-summary">
                    {selectedTestNames.map((name) => (
                      <span key={name} className="chip chip-subtle">
                        {name}
                      </span>
                    ))}
                  </div>
                )}
                <div className="catalog-grid">
                  {Object.entries(groupedCatalog).map(([department, items]) => (
                    <section key={department} className="catalog-group">
                      <div className="catalog-group-head">
                        <h3>{department.charAt(0).toUpperCase() + department.slice(1)}</h3>
                        <span>{items.length} tests</span>
                      </div>
                      <div className="catalog-items">
                        {items.map((item) => {
                          const selected = selectedTestCodes.includes(item.code);
                          return (
                            <button
                              key={item.code}
                              type="button"
                              className={`catalog-item${selected ? " selected" : ""}`}
                              onClick={() => toggleTestCode(item.code)}
                            >
                              <span className="catalog-item-check">{selected ? "Selected" : "Select"}</span>
                              <strong>{item.name}</strong>
                              <span>{item.category}</span>
                            </button>
                          );
                        })}
                      </div>
                    </section>
                  ))}
                </div>
              </div>
              <label className="inline-label">
                Custom Test
                <input value={customTestName} onChange={(event) => setCustomTestName(event.target.value)} placeholder="Write custom test if not found" />
              </label>
              <label>
                Lab Payment Amount
                <input value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} />
              </label>
              <label>
                Payment Status
                <select value={paymentStatus} onChange={(event) => setPaymentStatus(event.target.value as "paid" | "unpaid")}>
                  <option value="paid">Paid</option>
                  <option value="unpaid">Unpaid</option>
                </select>
              </label>
              <label>
                Payment Mode
                <select value={paymentMode} onChange={(event) => setPaymentMode(event.target.value)} disabled={paymentStatus !== "paid"}>
                  <option value="cash">Cash</option>
                  <option value="card">Card</option>
                  <option value="upi">UPI</option>
                </select>
              </label>
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={loading || visits.length === 0 || (selectedTestCodes.length === 0 && customTestName.trim().length === 0)}>
                {loading ? "Creating..." : "Record Lab Order"}
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Lab Worklist</h2>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | LabOrderStatus)}>
                <option value="all">All Status</option>
                <option value="ordered">Ordered</option>
                <option value="collected">Collected</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Ordered Tests</th>
                  <th>Payment</th>
                  <th>Status</th>
                  <th>Result</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={6}>No lab orders.</td>
                  </tr>
                ) : (
                  filteredOrders.map((order) => (
                    <tr key={order.id}>
                      <td>
                        {order.patient_name}
                        <div className="muted">{order.doctor_name}</div>
                      </td>
                      <td>
                        <div className="selection-summary">
                          {order.items.map((item) => (
                            <span key={item.id} className="chip chip-subtle">
                              {item.test_name}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        INR {order.payment_amount.toFixed(2)}
                        <div className="muted">
                          {order.payment_status}{order.payment_mode ? ` / ${order.payment_mode}` : ""}
                        </div>
                      </td>
                      <td>{order.status}</td>
                      <td>{order.result_summary ?? "-"}</td>
                      <td className="action-cell">
                        {order.payment_status !== "paid" && (
                          <button className="action-btn" type="button" disabled={actionLoadingOrderId === order.id} onClick={() => void handleCollectPayment(order)}>
                            Collect Payment
                          </button>
                        )}
                        {order.status === "ordered" && (
                          <button className="action-btn" type="button" disabled={actionLoadingOrderId === order.id} onClick={() => void handleStatusChange(order, "collected")}>
                            Mark Collected
                          </button>
                        )}
                        {(order.status === "ordered" || order.status === "collected") && (
                          <button className="action-btn" type="button" disabled={actionLoadingOrderId === order.id} onClick={() => void handleStatusChange(order, "processing")}>
                            Mark Processing
                          </button>
                        )}
                        {order.status === "processing" && (
                          <button className="action-btn" type="button" disabled={actionLoadingOrderId === order.id} onClick={() => void handleStatusChange(order, "completed")}>
                            Mark Done
                          </button>
                        )}
                        {order.status === "completed" && (
                          <button className="action-btn" type="button" disabled={actionLoadingOrderId === order.id} onClick={() => void handlePrint(order)}>
                            Print Report
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </article>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
