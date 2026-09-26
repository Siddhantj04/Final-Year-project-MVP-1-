const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("rl_token");
}

export function setAuth(token: string, role: string, email: string) {
  localStorage.setItem("rl_token", token);
  localStorage.setItem("rl_role", role);
  localStorage.setItem("rl_email", email);
}

export function clearAuth() {
  localStorage.removeItem("rl_token");
  localStorage.removeItem("rl_role");
  localStorage.removeItem("rl_email");
}

export function getAuthRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("rl_role");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (auth) {
    const token = getToken();
    if (!token) {
      throw new ApiError("You are not logged in.", 401);
    }
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Unable to reach the server. Check your connection.", 0);
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `Request failed (${response.status}).`;
    throw new ApiError(detail, response.status);
  }

  return data as T;
}

export function mediaUrl(path: string): string {
  const token = getToken();
  return `${API_URL}${path}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
}

export async function fetchBlob(path: string): Promise<string> {
  const token = getToken();
  if (!token) throw new ApiError("You are not logged in.", 401);
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError("Failed to load image.", response.status);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export { API_URL };
