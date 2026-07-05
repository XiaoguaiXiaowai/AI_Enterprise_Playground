export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

export function getApiBaseUrl(): string {
  const envValue = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envValue) return envValue;
  if (typeof window !== "undefined" && window.location?.origin) return window.location.origin;
  return "http://localhost:8000";
}

export async function apiGet<T>(path: string, token?: string): Promise<ApiResult<T>> {
  const url = `${getApiBaseUrl()}${path}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(url, { method: "GET", headers, cache: "no-store" });
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || `HTTP ${res.status}` };
    }
    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "request_failed" };
  }
}
