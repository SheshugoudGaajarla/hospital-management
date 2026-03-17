"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import {
  ConsultationRecord,
  createConsultation,
  downloadConsultationPdf,
  getConsultation,
  LabOrderRecord,
  listLabOrders,
  listOpVisits,
  OpVisit,
  updateConsultation,
  updateOpVisitStatus,
} from "@/src/lib/api";
import { getToken } from "@/src/lib/auth";

function prettyStatus(status: OpVisit["status"]): string {
  if (status === "in_consultation") return "With Doctor";
  if (status === "lab_processing") return "Lab Processing";
  if (status === "prescription_ready") return "Ready For Medical";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function DoctorPage() {
  const [visits, setVisits] = useState<OpVisit[]>([]);
  const [labOrders, setLabOrders] = useState<LabOrderRecord[]>([]);
  const [consultationVisitId, setConsultationVisitId] = useState<number | null>(null);
  const [consultationRecord, setConsultationRecord] = useState<ConsultationRecord | null>(null);
  const [consultationLoading, setConsultationLoading] = useState(false);
  const [consultationError, setConsultationError] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | OpVisit["status"]>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [vitals, setVitals] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [advice, setAdvice] = useState("");
  const [prescriptionMedicines, setPrescriptionMedicines] = useState("");
  const [prescriptionDosage, setPrescriptionDosage] = useState("");
  const [prescriptionDuration, setPrescriptionDuration] = useState("");
  const [prescriptionNotes, setPrescriptionNotes] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [pageError, setPageError] = useState("");

  async function loadVisits() {
    const token = getToken();
    if (!token) return;
    try {
      const queue = await listOpVisits(token);
      setVisits(queue);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Failed to load doctor queue");
    }
  }

  useEffect(() => {
    void loadVisits();
  }, []);

  function loadConsultationForm(record: ConsultationRecord | null) {
    setConsultationRecord(record);
    setChiefComplaint(record?.chief_complaint ?? "");
    setVitals(record?.vitals ?? "");
    setDiagnosis(record?.diagnosis ?? "");
    setClinicalNotes(record?.clinical_notes ?? "");
    setAdvice(record?.advice ?? "");
    setPrescriptionMedicines(record?.prescription_medicines ?? "");
    setPrescriptionDosage(record?.prescription_dosage ?? "");
    setPrescriptionDuration(record?.prescription_duration ?? "");
    setPrescriptionNotes(record?.prescription_notes ?? "");
    setFollowUpDate(record?.follow_up_date ?? "");
  }

  async function openVisit(visit: OpVisit, startConsultation = false) {
    const token = getToken();
    if (!token) return;
    setConsultationVisitId(visit.id);
    setConsultationLoading(true);
    setConsultationError("");
    try {
      if (startConsultation && visit.status === "waiting") {
        await updateOpVisitStatus(token, visit.id, "in_consultation");
      }

      const [recordResult, labResult] = await Promise.allSettled([
        getConsultation(token, visit.id),
        listLabOrders(token, visit.id),
      ]);

      if (recordResult.status === "fulfilled") {
        loadConsultationForm(recordResult.value);
      } else {
        const message = recordResult.reason instanceof Error ? recordResult.reason.message : "Failed to load consultation";
        if (message.includes("Consultation not found")) {
          loadConsultationForm(null);
          setConsultationError("No consultation notes saved for this visit yet.");
        } else {
          loadConsultationForm(null);
          setConsultationError(message);
        }
      }

      if (labResult.status === "fulfilled") {
        setLabOrders(labResult.value);
      } else {
        setLabOrders([]);
      }

      await loadVisits();
    } finally {
      setConsultationLoading(false);
    }
  }

  async function saveConsultationCore(): Promise<boolean> {
    if (!consultationVisitId) return false;
    if (!chiefComplaint.trim()) {
      setConsultationError("Chief complaint is required.");
      return false;
    }
    const token = getToken();
    if (!token) return false;

    setConsultationLoading(true);
    setConsultationError("");
    try {
      const payload = {
        chief_complaint: chiefComplaint.trim(),
        vitals: vitals.trim() || undefined,
        diagnosis: diagnosis.trim() || undefined,
        clinical_notes: clinicalNotes.trim() || undefined,
        advice: advice.trim() || undefined,
        prescription_medicines: prescriptionMedicines.trim() || undefined,
        prescription_dosage: prescriptionDosage.trim() || undefined,
        prescription_duration: prescriptionDuration.trim() || undefined,
        prescription_notes: prescriptionNotes.trim() || undefined,
        follow_up_date: followUpDate || null,
      };
      const saved = consultationRecord
        ? await updateConsultation(token, consultationVisitId, payload)
        : await createConsultation(token, consultationVisitId, payload);
      loadConsultationForm(saved);
      return true;
    } catch (err) {
      setConsultationError(err instanceof Error ? err.message : "Failed to save consultation");
      return false;
    } finally {
      setConsultationLoading(false);
    }
  }

  async function handleSaveConsultation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await saveConsultationCore();
  }

  async function handleFinalizeVisit() {
    const token = getToken();
    if (!token || !consultationVisitId) return;
    const selectedVisit = visits.find((visit) => visit.id === consultationVisitId);
    if (!selectedVisit) return;
    const saved = await saveConsultationCore();
    if (!saved) return;
    if (selectedVisit.status === "in_consultation") {
      await updateOpVisitStatus(token, consultationVisitId, "prescription_ready");
      await loadVisits();
    }
  }

  async function handlePrintConsultation() {
    const token = getToken();
    if (!token || !consultationVisitId) return;
    const selectedVisit = visits.find((visit) => visit.id === consultationVisitId) ?? null;
    try {
      await downloadConsultationPdf(token, consultationVisitId, selectedVisit?.token_no);
    } catch (err) {
      setConsultationError(err instanceof Error ? err.message : "Failed to download prescription");
    }
  }

  const filteredVisits = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return visits.filter((visit) => {
      const statusMatch = statusFilter === "all" || visit.status === statusFilter;
      const textMatch =
        q.length === 0 ||
        visit.uhid.toLowerCase().includes(q) ||
        visit.patient_name.toLowerCase().includes(q) ||
        visit.village_town.toLowerCase().includes(q) ||
        String(visit.token_no).includes(q);
      return statusMatch && textMatch;
    });
  }, [searchTerm, statusFilter, visits]);

  const selectedVisit = useMemo(
    () => visits.find((visit) => visit.id === consultationVisitId) ?? null,
    [consultationVisitId, visits],
  );

  const pendingLabOrders = useMemo(
    () => labOrders.filter((order) => order.status !== "completed").length,
    [labOrders],
  );
  const isVisitLocked = selectedVisit?.status === "prescription_ready" || selectedVisit?.status === "completed";

  const waitingCount = useMemo(() => visits.filter((visit) => visit.status === "waiting").length, [visits]);
  const doctorCount = useMemo(() => visits.filter((visit) => visit.status === "in_consultation").length, [visits]);
  const labCount = useMemo(() => visits.filter((visit) => visit.status === "lab_processing").length, [visits]);
  const readyCount = useMemo(() => visits.filter((visit) => visit.status === "prescription_ready").length, [visits]);
  const completedCount = useMemo(() => visits.filter((visit) => visit.status === "completed").length, [visits]);

  return (
    <AuthGuard allowedRoles={["admin", "doctor"]}>
      <AppShell>
        <section className="page-head theme-banner theme-dashboard">
          <h1>Doctor Workspace</h1>
          <p>Review OP intake, examine the patient, request tests, finalize prescription, then hand off to medical.</p>
        </section>

        {pageError && <p className="error">{pageError}</p>}

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>Doctor Queue</h2>
              <div className="chip-row">
                <span className="chip">{waitingCount} waiting</span>
                <span className="chip chip-subtle">{doctorCount} active</span>
                <span className="chip chip-subtle">{labCount} in lab</span>
                <span className="chip chip-subtle">{readyCount} ready for medical</span>
                <span className="chip chip-subtle">{completedCount} completed</span>
              </div>
            </div>
            <div className="toolbar">
              <input
                placeholder="Search by token, UHID, patient, village"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | OpVisit["status"])}>
                <option value="all">All Status</option>
                <option value="waiting">Waiting</option>
                <option value="in_consultation">With Doctor</option>
                <option value="lab_processing">Lab Processing</option>
                <option value="prescription_ready">Ready For Medical</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Token</th>
                  <th>UHID</th>
                  <th>Patient</th>
                  <th>Village/Town</th>
                  <th>Age</th>
                  <th>Vitals</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredVisits.length === 0 ? (
                  <tr>
                    <td colSpan={8}>No patients in queue.</td>
                  </tr>
                ) : (
                  filteredVisits.map((visit) => (
                    <tr key={visit.id}>
                      <td>{visit.token_no}</td>
                      <td>{visit.uhid}</td>
                      <td>{visit.patient_name}</td>
                      <td>{visit.village_town}</td>
                      <td>{visit.age}</td>
                      <td>{visit.weight_kg.toFixed(2)} kg / {visit.bp}</td>
                      <td>
                        <span className={visit.status === "waiting" ? "badge waiting" : visit.status === "in_consultation" ? "badge active" : visit.status === "completed" ? "badge done" : "badge active"}>
                          {prettyStatus(visit.status)}
                        </span>
                      </td>
                      <td className="action-cell">
                        {visit.status === "waiting" && (
                          <button className="action-btn" type="button" onClick={() => void openVisit(visit, true)}>
                            Start Visit
                          </button>
                        )}
                        {visit.status !== "waiting" && (
                          <button className="action-btn" type="button" onClick={() => void openVisit(visit)}>
                            {visit.status === "completed" ? "View Visit" : "Open Visit"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </article>

          <article className="panel sticky-summary">
            <div className="panel-head">
              <h2>Clinical Flow</h2>
            </div>
            <ul className="list-clean">
              <li>1. Take patient from waiting queue.</li>
              <li>2. Examine patient and write notes or prescription on paper.</li>
              <li>3. Laboratory records tests from the paper request.</li>
              <li>4. Review completed lab results.</li>
              <li>5. Send patient to medical hall with paper prescription.</li>
            </ul>
            {selectedVisit && pendingLabOrders > 0 && (
              <p className="muted" style={{ marginTop: "12px" }}>
                {pendingLabOrders} lab order{pendingLabOrders === 1 ? "" : "s"} still pending for this patient.
              </p>
            )}
          </article>
        </section>

        <section className="panel" style={{ marginTop: "14px" }}>
          <div className="panel-head">
            <h2>Consultation And Orders</h2>
          </div>
          {!consultationVisitId && <p>Select a patient from the doctor queue.</p>}
          {consultationVisitId && (
            <form className="form-grid" onSubmit={handleSaveConsultation}>
              <p>
                <strong>Visit:</strong>{" "}
                {selectedVisit ? `Token ${selectedVisit.token_no} - ${selectedVisit.patient_name}` : `#${consultationVisitId}`}
              </p>
              {selectedVisit && (
                <p className="muted">
                  Status: <strong>{prettyStatus(selectedVisit.status)}</strong> | Vitals: {selectedVisit.weight_kg.toFixed(2)} kg / {selectedVisit.bp}
                </p>
              )}
              {consultationRecord && (
                <p className="muted">
                  Last Updated: {new Date(consultationRecord.updated_at).toLocaleString("en-IN")}
                </p>
              )}

              <label>
                Chief Complaint
                <input value={chiefComplaint} onChange={(event) => setChiefComplaint(event.target.value)} placeholder="Primary complaint" disabled={consultationLoading || isVisitLocked} required />
              </label>
              <label>
                Vitals / Examination
                <input value={vitals} onChange={(event) => setVitals(event.target.value)} placeholder="Pulse, temperature, examination notes" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Diagnosis
                <input value={diagnosis} onChange={(event) => setDiagnosis(event.target.value)} placeholder="Working diagnosis" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Clinical Notes
                <textarea value={clinicalNotes} onChange={(event) => setClinicalNotes(event.target.value)} rows={4} placeholder="Clinical findings and assessment" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Advice
                <textarea value={advice} onChange={(event) => setAdvice(event.target.value)} rows={3} placeholder="Advice to patient" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Prescription Medicines
                <textarea value={prescriptionMedicines} onChange={(event) => setPrescriptionMedicines(event.target.value)} rows={4} placeholder="Medicine names" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Prescription Dosage
                <textarea value={prescriptionDosage} onChange={(event) => setPrescriptionDosage(event.target.value)} rows={3} placeholder="Dosage instructions" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Prescription Duration
                <input value={prescriptionDuration} onChange={(event) => setPrescriptionDuration(event.target.value)} placeholder="e.g. 5 days" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Prescription Notes
                <textarea value={prescriptionNotes} onChange={(event) => setPrescriptionNotes(event.target.value)} rows={3} placeholder="Special notes for medical team" disabled={consultationLoading || isVisitLocked} />
              </label>
              <label>
                Follow-up Date
                <input type="date" value={followUpDate} onChange={(event) => setFollowUpDate(event.target.value)} disabled={consultationLoading || isVisitLocked} />
              </label>

              <div>
                <strong>Lab Results</strong>
                <p className="muted">Laboratory staff record tests from the doctor paper and update results here when completed.</p>
                {labOrders.length === 0 ? (
                  <p className="muted" style={{ marginTop: "10px" }}>
                    No lab records for this visit yet.
                  </p>
                ) : (
                  <table className="table" style={{ marginTop: "10px" }}>
                    <thead>
                      <tr>
                        <th>Ordered Tests</th>
                        <th>Status</th>
                        <th>Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {labOrders.map((order) => (
                        <tr key={order.id}>
                          <td>
                            <div className="selection-summary">
                              {order.items.map((item) => (
                                <span key={item.id} className="chip chip-subtle">
                                  {item.test_name}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td>{order.status}</td>
                          <td>{order.result_summary ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {consultationError && <p className="error">{consultationError}</p>}
              {selectedVisit?.status === "prescription_ready" || selectedVisit?.status === "completed" ? (
                <p className="muted">This visit is ready for the medical team or already completed. Use Print Prescription for handoff.</p>
              ) : (
                <>
                  <button type="submit" disabled={consultationLoading}>
                    {consultationLoading ? "Saving..." : consultationRecord ? "Update Consultation" : "Save Consultation"}
                  </button>
                  <button
                    type="button"
                    className="secondary-btn"
                    disabled={consultationLoading || !selectedVisit || selectedVisit.status !== "in_consultation" || pendingLabOrders > 0}
                    onClick={() => void handleFinalizeVisit()}
                  >
                    {pendingLabOrders > 0 ? "Pending Lab Results" : "Send To Medical"}
                  </button>
                </>
              )}
              <button
                type="button"
                className="secondary-btn"
                disabled={consultationLoading || !consultationRecord}
                onClick={() => void handlePrintConsultation()}
              >
                Print Prescription
              </button>
            </form>
          )}
        </section>
      </AppShell>
    </AuthGuard>
  );
}
