"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import { createOpVisit, listOpVisits, OpVisit } from "@/src/lib/api";
import { getRole, getToken } from "@/src/lib/auth";

function prettyStatus(status: OpVisit["status"]): string {
  if (status === "in_consultation") return "With Doctor";
  if (status === "lab_processing") return "Lab Processing";
  if (status === "prescription_ready") return "Ready For Medical";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function OpPage() {
  const role = getRole();
  const isOperationsOnly = role === "operations";

  const [patientName, setPatientName] = useState("");
  const [villageTown, setVillageTown] = useState("");
  const [age, setAge] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [bp, setBp] = useState("");
  const [doctorName, setDoctorName] = useState("Dr Viday Sagar Reddy");
  const [consultationFee, setConsultationFee] = useState("300");
  const [consultationPaymentMode, setConsultationPaymentMode] = useState("cash");
  const [visits, setVisits] = useState<OpVisit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [registrationMessage, setRegistrationMessage] = useState("");

  async function loadVisits() {
    if (isOperationsOnly) return;
    const token = getToken();
    if (!token) return;
    try {
      setVisits(await listOpVisits(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load OP queue");
    }
  }

  useEffect(() => {
    void loadVisits();
  }, [isOperationsOnly]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;

    const numericAge = Number(age);
    if (Number.isNaN(numericAge) || numericAge < 0 || numericAge > 120) {
      setError("Age must be between 0 and 120");
      return;
    }
    const numericWeight = Number(weightKg);
    if (Number.isNaN(numericWeight) || numericWeight <= 0 || numericWeight > 300) {
      setError("Weight must be greater than 0 and up to 300 kg");
      return;
    }
    const bpText = bp.trim().replace(/\s+/g, "");
    if (!/^\d{2,3}\/\d{2,3}$/.test(bpText)) {
      setError("BP must be in format 120/80");
      return;
    }
    const numericConsultationFee = Number(consultationFee);
    if (Number.isNaN(numericConsultationFee) || numericConsultationFee < 0) {
      setError("Consultation fee must be a valid non-negative amount");
      return;
    }

    setLoading(true);
    setError("");
    setRegistrationMessage("");
    try {
      const created = await createOpVisit(token, {
        patient_name: patientName.trim(),
        village_town: villageTown.trim(),
        age: numericAge,
        weight_kg: numericWeight,
        bp: bpText,
        doctor_name: doctorName,
        consultation_fee: numericConsultationFee,
        consultation_payment_mode: consultationPaymentMode,
      });
      setPatientName("");
      setVillageTown("");
      setAge("");
      setWeightKg("");
      setBp("");
      setConsultationFee("300");
      setConsultationPaymentMode("cash");
      setRegistrationMessage(
        `Queued successfully. Token ${created.token_no}, UHID ${created.uhid}, OP fee ₹${created.consultation_fee.toFixed(2)} collected by ${created.consultation_payment_mode}.`,
      );
      await loadVisits();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record OP visit");
    } finally {
      setLoading(false);
    }
  }

  const waitingCount = useMemo(() => visits.filter((visit) => visit.status === "waiting").length, [visits]);
  const doctorCount = useMemo(() => visits.filter((visit) => visit.status === "in_consultation").length, [visits]);
  const labCount = useMemo(() => visits.filter((visit) => visit.status === "lab_processing").length, [visits]);
  const readyCount = useMemo(() => visits.filter((visit) => visit.status === "prescription_ready").length, [visits]);
  const completedCount = useMemo(() => visits.filter((visit) => visit.status === "completed").length, [visits]);

  return (
    <AuthGuard allowedRoles={["admin", "operations"]}>
      <AppShell>
        <section className="page-head theme-banner theme-op">
          <h1>OP Desk</h1>
          <p>Register the patient, generate token and UHID, then hand off to the doctor queue.</p>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>New OP Registration</h2>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                Patient Name
                <input value={patientName} onChange={(event) => setPatientName(event.target.value)} placeholder="Enter full name" required />
              </label>
              <label>
                Village/Town
                <input value={villageTown} onChange={(event) => setVillageTown(event.target.value)} placeholder="Enter village or town" required />
              </label>
              <label>
                Age
                <input value={age} onChange={(event) => setAge(event.target.value)} placeholder="Enter age" required />
              </label>
              <label>
                Weight (kg)
                <input value={weightKg} onChange={(event) => setWeightKg(event.target.value)} placeholder="Enter weight in kg" required />
              </label>
              <label>
                BP (systolic/diastolic)
                <input value={bp} onChange={(event) => setBp(event.target.value)} placeholder="120/80" required />
              </label>
              <label>
                Doctor
                <select value={doctorName} onChange={(event) => setDoctorName(event.target.value)}>
                  <option>Dr Viday Sagar Reddy</option>
                  <option>Dr Ch Maduri</option>
                </select>
              </label>
              <label>
                OP Consultation Fee
                <input value={consultationFee} onChange={(event) => setConsultationFee(event.target.value)} placeholder="300" required />
              </label>
              <label>
                Payment Mode
                <select value={consultationPaymentMode} onChange={(event) => setConsultationPaymentMode(event.target.value)}>
                  <option value="cash">Cash</option>
                  <option value="card">Card</option>
                  <option value="upi">UPI</option>
                </select>
              </label>
              {error && <p className="error">{error}</p>}
              {registrationMessage && <p className="muted">{registrationMessage}</p>}
              <button type="submit" disabled={loading}>
                {loading ? "Recording..." : "Record OP"}
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Handoff Flow</h2>
              {!isOperationsOnly && <Link href="/doctor" className="action-card">Open Doctor Queue</Link>}
            </div>
            <div className="chip-row">
              <span className="chip">{waitingCount} waiting</span>
              <span className="chip chip-subtle">{doctorCount} with doctor</span>
              <span className="chip chip-subtle">{labCount} in lab</span>
              <span className="chip chip-subtle">{readyCount} ready for medical</span>
              <span className="chip chip-subtle">{completedCount} completed</span>
            </div>
            <ul className="list-clean" style={{ marginTop: "12px" }}>
              <li>1. OP captures vitals and assigns doctor.</li>
              <li>2. Doctor opens own queue and examines the patient.</li>
              <li>3. Doctor may request lab tests if needed.</li>
              <li>4. Laboratory processes ordered tests and updates results.</li>
              <li>5. Doctor reviews results and writes final prescription.</li>
              <li>6. Medical team dispenses medicines and closes the visit.</li>
            </ul>
            <p className="muted" style={{ marginTop: "12px" }}>
              OP desk does not handle consultation notes, lab processing, or medicine workflow.
            </p>
          </article>
        </section>

        {!isOperationsOnly && (
          <section className="panel" style={{ marginTop: "14px" }}>
            <div className="panel-head">
              <h2>Recent Registrations</h2>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Token</th>
                  <th>UHID</th>
                  <th>Patient</th>
                  <th>Village/Town</th>
                  <th>Age</th>
                  <th>Weight</th>
                  <th>BP</th>
                  <th>Doctor</th>
                  <th>OP Fee</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visits.length === 0 ? (
                  <tr>
                    <td colSpan={10}>No registrations yet.</td>
                  </tr>
                ) : (
                  visits.slice(0, 12).map((visit) => (
                    <tr key={visit.id}>
                      <td>{visit.token_no}</td>
                      <td>{visit.uhid}</td>
                      <td>{visit.patient_name}</td>
                      <td>{visit.village_town}</td>
                      <td>{visit.age}</td>
                      <td>{visit.weight_kg.toFixed(2)} kg</td>
                      <td>{visit.bp}</td>
                      <td>{visit.doctor_name}</td>
                      <td>₹{visit.consultation_fee.toFixed(2)}</td>
                      <td>
                        <span className={visit.status === "waiting" ? "badge waiting" : visit.status === "completed" ? "badge done" : "badge active"}>
                          {prettyStatus(visit.status)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </section>
        )}
      </AppShell>
    </AuthGuard>
  );
}
