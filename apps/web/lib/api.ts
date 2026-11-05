import type { AuthResponse, Settings, SettingsInput } from "@/lib/types";

export const TOKEN_KEY = "meridian_token";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function messageFrom(body: unknown): string {
  if (!body || typeof body !== "object") return "La requête a échoué.";
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const text = detail
      .map((item) => {
        if (typeof item === "object" && item && "msg" in item) return String(item.msg);
        return "";
      })
      .filter(Boolean)
      .join(" ");
    return text || "Données invalides.";
  }
  return "La requête a échoué.";
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api/geo${path}`, { ...init, headers });
  if (response.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    const path = window.location.pathname;
    const publicPage = ["/login", "/register", "/forgot-password", "/reset-password", "/verify-email"].some((item) =>
      path.startsWith(item),
    );
    if (!publicPage) window.location.assign("/login");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(messageFrom(body), response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function login(email: string, password: string) {
  return api<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(name: string, email: string, password: string) {
  return api<{ message: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export function resendVerification(email: string) {
  return api<{ message: string }>("/auth/resend", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function verifyEmail(token: string) {
  return api<{ message: string }>("/auth/verify", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function requestPasswordReset(email: string) {
  return api<{ message: string }>("/auth/forgot", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, password: string) {
  return api<{ message: string }>("/auth/reset", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export function saveSettings(input: SettingsInput) {
  return api<Settings>("/settings", { method: "PUT", body: JSON.stringify(input) });
}

/** Questions proposées par Claude, autant que le forfait en envoie par mois. Rien n'est enregistré. */
export function generateQuestions(input: Pick<SettingsInput, "brandName" | "domain" | "sector"> & { existing: string[] }) {
  return api<{ questions: string[] }>("/settings/queries/generate", { method: "POST", body: JSON.stringify(input) });
}
