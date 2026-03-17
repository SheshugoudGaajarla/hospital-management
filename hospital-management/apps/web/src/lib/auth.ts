export type AppRole = "doctor" | "admin" | "laboratory" | "medical" | "operations";

const TOKEN_KEY = "hospital_access_token";
const ROLE_KEY = "hospital_role";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): AppRole | null {
  if (typeof window === "undefined") return null;
  const role = localStorage.getItem(ROLE_KEY);
  if (!role) return null;
  return role as AppRole;
}

export function setSession(token: string, role: AppRole): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}
