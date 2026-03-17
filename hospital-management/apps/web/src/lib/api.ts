import { AppRole } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type LoginResponse = {
  access_token: string;
  token_type: string;
  role: AppRole;
};

type MeResponse = {
  id: number;
  username: string;
  full_name: string;
  role: AppRole;
};

export type OpVisit = {
  id: number;
  patient_id: number;
  uhid: string;
  patient_name: string;
  village_town: string;
  age: number;
  weight_kg: number;
  bp: string;
  token_no: number;
  doctor_name: string;
  consultation_fee: number;
  consultation_payment_mode: string;
  consultation_paid_at: string;
  status: string;
  visit_date: string;
};

export type OpVisitStatus = "waiting" | "in_consultation" | "lab_processing" | "prescription_ready" | "completed" | "cancelled";

export type AppUser = {
  id: number;
  username: string;
  full_name: string;
  role: AppRole;
};

export type ConsultationRecord = {
  id: number;
  op_visit_id: number;
  chief_complaint: string;
  vitals: string | null;
  diagnosis: string | null;
  clinical_notes: string | null;
  advice: string | null;
  prescription_medicines: string | null;
  prescription_dosage: string | null;
  prescription_duration: string | null;
  prescription_notes: string | null;
  follow_up_date: string | null;
  created_at: string;
  updated_at: string;
};

export type ExpenseRecord = {
  id: number;
  category: string;
  amount: number;
  notes: string | null;
  expense_date: string;
};

export type MedicalBillRecord = {
  id: number;
  invoice_no: string;
  patient_id: number;
  patient_name: string;
  op_visit_id: number | null;
  lab_fee: number;
  medicine_fee: number;
  discount: number;
  tax: number;
  net_amount: number;
  payment_mode: string;
  status: string;
  paid_at: string | null;
  refunded_at: string | null;
  refund_reason: string | null;
  created_at: string;
};

export type DailySummary = {
  date: string;
  op_count: number;
  pending_queue: number;
  revenue: number;
  expenses: number;
  net_collection: number;
};

export type TrendPoint = {
  date: string;
  value: number;
};

export type OpSummary = {
  date: string;
  total: number;
  waiting: number;
  in_consultation: number;
  lab_processing: number;
  prescription_ready: number;
  completed: number;
  cancelled: number;
};

export type DateRangeSummary = {
  start_date: string;
  end_date: string;
  total_days: number;
  op_count: number;
  revenue: number;
  expenses: number;
  net_collection: number;
};

export type DoctorOpSummaryPoint = {
  doctor_name: string;
  total_visits: number;
  completed_visits: number;
};

export type ExpenseCategoryPoint = {
  category: string;
  amount: number;
};

export type LabOrderStatus = "ordered" | "collected" | "processing" | "completed";

export type LabOrderItemRecord = {
  id: number;
  test_code: string;
  test_name: string;
  department: string;
  category: string;
};

export type LabOrderRecord = {
  id: number;
  op_visit_id: number;
  patient_name: string;
  doctor_name: string;
  status: LabOrderStatus;
  payment_amount: number;
  payment_status: string;
  payment_mode: string | null;
  result_summary: string | null;
  items: LabOrderItemRecord[];
  ordered_at: string;
  reported_at: string | null;
  paid_at: string | null;
};

export type LabCatalogItem = {
  code: string;
  name: string;
  department: string;
  category: string;
};

async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Login failed");
  }

  return response.json() as Promise<LoginResponse>;
}

export async function getCurrentUser(token: string): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/auth/me", token, { method: "GET" });
}

export async function listUsers(token: string): Promise<AppUser[]> {
  return apiFetch<AppUser[]>("/api/v1/auth/users", token, { method: "GET" });
}

export async function createUser(
  token: string,
  payload: { username: string; full_name: string; role: AppRole; password: string },
): Promise<AppUser> {
  return apiFetch<AppUser>("/api/v1/auth/users", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDailySummary(token: string, date?: string): Promise<DailySummary> {
  const suffix = date ? `?date=${encodeURIComponent(date)}` : "";
  return apiFetch<DailySummary>(`/api/v1/reports/daily-summary${suffix}`, token, { method: "GET" });
}

export async function getRevenueTrend(token: string, days = 7): Promise<TrendPoint[]> {
  return apiFetch<TrendPoint[]>(`/api/v1/reports/revenue-trend?days=${days}`, token, { method: "GET" });
}

export async function getExpenseTrend(token: string, days = 7): Promise<TrendPoint[]> {
  return apiFetch<TrendPoint[]>(`/api/v1/reports/expense-trend?days=${days}`, token, { method: "GET" });
}

export async function getOpSummary(token: string, date?: string): Promise<OpSummary> {
  const suffix = date ? `?date=${encodeURIComponent(date)}` : "";
  return apiFetch<OpSummary>(`/api/v1/reports/op-summary${suffix}`, token, { method: "GET" });
}

export async function getDateRangeSummary(
  token: string,
  startDate: string,
  endDate: string,
): Promise<DateRangeSummary> {
  return apiFetch<DateRangeSummary>(
    `/api/v1/reports/date-range-summary?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    token,
    { method: "GET" },
  );
}

export async function getDoctorOpSummary(
  token: string,
  startDate: string,
  endDate: string,
): Promise<DoctorOpSummaryPoint[]> {
  return apiFetch<DoctorOpSummaryPoint[]>(
    `/api/v1/reports/doctor-op-summary?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    token,
    { method: "GET" },
  );
}

export async function getExpenseCategorySummary(
  token: string,
  startDate: string,
  endDate: string,
): Promise<ExpenseCategoryPoint[]> {
  return apiFetch<ExpenseCategoryPoint[]>(
    `/api/v1/reports/expense-category-summary?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    token,
    { method: "GET" },
  );
}

export async function createOpVisit(
  token: string,
  payload: {
    patient_name: string;
    village_town: string;
    age: number;
    weight_kg: number;
    bp: string;
    doctor_name: string;
    consultation_fee: number;
    consultation_payment_mode: string;
  },
): Promise<OpVisit> {
  return apiFetch<OpVisit>("/api/v1/op-visits", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listOpVisits(token: string): Promise<OpVisit[]> {
  return apiFetch<OpVisit[]>("/api/v1/op-visits", token, { method: "GET" });
}

export async function updateOpVisitStatus(
  token: string,
  visitId: number,
  status: OpVisitStatus,
): Promise<OpVisit> {
  return apiFetch<OpVisit>(`/api/v1/op-visits/${visitId}/status`, token, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function getConsultation(
  token: string,
  visitId: number,
): Promise<ConsultationRecord> {
  return apiFetch<ConsultationRecord>(`/api/v1/op-visits/${visitId}/consultation`, token, { method: "GET" });
}

export async function createConsultation(
  token: string,
  visitId: number,
  payload: {
    chief_complaint: string;
    vitals?: string;
    diagnosis?: string;
    clinical_notes?: string;
    advice?: string;
    prescription_medicines?: string;
    prescription_dosage?: string;
    prescription_duration?: string;
    prescription_notes?: string;
    follow_up_date?: string | null;
  },
): Promise<ConsultationRecord> {
  return apiFetch<ConsultationRecord>(`/api/v1/op-visits/${visitId}/consultation`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateConsultation(
  token: string,
  visitId: number,
  payload: {
    chief_complaint?: string;
    vitals?: string;
    diagnosis?: string;
    clinical_notes?: string;
    advice?: string;
    prescription_medicines?: string;
    prescription_dosage?: string;
    prescription_duration?: string;
    prescription_notes?: string;
    follow_up_date?: string | null;
  },
): Promise<ConsultationRecord> {
  return apiFetch<ConsultationRecord>(`/api/v1/op-visits/${visitId}/consultation`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function createExpense(
  token: string,
  payload: { category: string; amount: number; notes?: string },
): Promise<ExpenseRecord> {
  return apiFetch<ExpenseRecord>("/api/v1/expenses", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listExpenses(token: string): Promise<ExpenseRecord[]> {
  return apiFetch<ExpenseRecord[]>("/api/v1/expenses", token, { method: "GET" });
}

export async function updateExpense(
  token: string,
  expenseId: number,
  payload: { category?: string; amount?: number; notes?: string },
): Promise<ExpenseRecord> {
  return apiFetch<ExpenseRecord>(`/api/v1/expenses/${expenseId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getExpenseSummary(token: string): Promise<{ total_amount: number }> {
  return apiFetch<{ total_amount: number }>("/api/v1/expenses/summary", token, { method: "GET" });
}

export async function createMedicalBill(
  token: string,
  payload: {
    patient_id: number;
    op_visit_id?: number | null;
    lab_fee: number;
    medicine_fee: number;
    discount: number;
    tax: number;
    payment_mode: string;
    status: "paid" | "unpaid";
  },
): Promise<MedicalBillRecord> {
  return apiFetch<MedicalBillRecord>("/api/v1/medical-bills", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listMedicalBills(token: string): Promise<MedicalBillRecord[]> {
  return apiFetch<MedicalBillRecord[]>("/api/v1/medical-bills", token, { method: "GET" });
}

export async function updateMedicalBill(
  token: string,
  billId: number,
  payload: { status: "paid" | "unpaid" | "refunded"; payment_mode?: string; refund_reason?: string },
): Promise<MedicalBillRecord> {
  return apiFetch<MedicalBillRecord>(`/api/v1/medical-bills/${billId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listLabOrders(token: string, opVisitId?: number): Promise<LabOrderRecord[]> {
  const suffix = opVisitId ? `?op_visit_id=${opVisitId}` : "";
  return apiFetch<LabOrderRecord[]>(`/api/v1/lab-orders${suffix}`, token, { method: "GET" });
}

export async function listLabCatalog(token: string): Promise<LabCatalogItem[]> {
  return apiFetch<LabCatalogItem[]>("/api/v1/lab-orders/catalog", token, { method: "GET" });
}

export async function createLabOrder(
  token: string,
  payload: {
    op_visit_id: number;
    test_codes?: string[];
    custom_test_name?: string;
    payment_amount?: number;
    payment_status?: "paid" | "unpaid";
    payment_mode?: string;
  },
): Promise<LabOrderRecord[]> {
  return apiFetch<LabOrderRecord[]>("/api/v1/lab-orders", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateLabOrder(
  token: string,
  orderId: number,
  payload: {
    status?: LabOrderStatus;
    result_summary?: string;
    payment_amount?: number;
    payment_status?: "paid" | "unpaid";
    payment_mode?: string;
  },
): Promise<LabOrderRecord> {
  return apiFetch<LabOrderRecord>(`/api/v1/lab-orders/${orderId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function downloadLabReport(
  token: string,
  orderId: number,
): Promise<void> {
  return downloadReportFile(token, `/api/v1/lab-orders/${orderId}/report.pdf`, `lab_order_${orderId}.pdf`);
}

export async function downloadReportFile(
  token: string,
  endpoint: string,
  filename: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to download ${filename}`);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadCsvReport(
  token: string,
  endpoint: string,
  filename: string,
): Promise<void> {
  await downloadReportFile(token, endpoint, filename);
}

export async function downloadConsultationPdf(token: string, visitId: number, tokenNo?: number): Promise<void> {
  const filename = tokenNo ? `consultation-token-${tokenNo}.pdf` : `consultation-visit-${visitId}.pdf`;
  await downloadReportFile(token, `/api/v1/op-visits/${visitId}/consultation.pdf`, filename);
}
