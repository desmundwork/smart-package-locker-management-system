// Production auth client: login, token storage, and an authenticated fetch
// wrapper. The POC's api.ts is patched at build time to route through
// authFetch so every /api call carries the bearer token.

export type Role = "ADMIN" | "AGENT" | "CUSTOMER";

const TOKEN_KEY = "smartlocker.token";
const ROLE_KEY = "smartlocker.role";
const USER_KEY = "smartlocker.user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): Role | null {
  return localStorage.getItem(ROLE_KEY) as Role | null;
}

export function getUsername(): string | null {
  return localStorage.getItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  role: Role;
  username: string;
}

export async function login(username: string, password: string): Promise<LoginResult> {
  // OAuth2 password flow expects form-encoded body.
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    throw new Error(res.status === 401 ? "Invalid username or password" : `Login failed (${res.status})`);
  }
  const data = (await res.json()) as LoginResult;
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(ROLE_KEY, data.role);
  localStorage.setItem(USER_KEY, data.username);
  return data;
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(USER_KEY);
}

export interface DemoCredential {
  view: string;
  role: Role;
  username: string;
  password: string;
}

export interface DemoCredentialsResponse {
  review_mode: boolean;
  credentials: DemoCredential[];
}

// Fetch seeded demo credentials for the given view. Returns review_mode=false
// (and an empty list) when the server isn't in review mode, so the caller shows
// nothing in a real production deployment.
export async function fetchDemoCredentials(view?: string): Promise<DemoCredentialsResponse> {
  const qs = view ? `?view=${encodeURIComponent(view)}` : "";
  try {
    const res = await fetch(`/api/auth/demo-credentials${qs}`);
    if (!res.ok) return { review_mode: false, credentials: [] };
    return (await res.json()) as DemoCredentialsResponse;
  } catch {
    return { review_mode: false, credentials: [] };
  }
}

// Drop-in replacement for fetch that injects the bearer token and, on a 401,
// clears the session so the UI falls back to the login screen.
export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) headers.set("authorization", `Bearer ${token}`);
  const res = await fetch(input, { ...init, headers });
  if (res.status === 401) {
    logout();
    // Reload to re-render the login gate.
    if (typeof window !== "undefined") window.location.reload();
  }
  return res;
}

export type View = "landing" | "admin" | "agent" | "customer";
const VIEW_NAMES: View[] = ["admin", "agent", "customer"];

// Is the app being accessed via a bare IP address (e.g. 56.69.57.18) rather
// than a domain name? On a bare IP the per-view *subdomain* model can't work
// (admin.56.69.57.18 isn't valid), so we route by URL path instead.
export function isBareIpHost(): boolean {
  const host = window.location.hostname;
  // IPv4, IPv6, or localhost -> treat as "no usable app subdomain".
  return (
    /^\d{1,3}(\.\d{1,3}){3}$/.test(host) ||
    host === "localhost" ||
    host.includes(":") // IPv6
  );
}

// Whether this deployment addresses views by subdomain (admin.smart-locker.…)
// or by path (/admin). Subdomains are used only when the host looks like a
// real domain that contains the app name; otherwise fall back to paths so the
// app is fully usable on a bare IP or localhost.
export function usesSubdomainRouting(): boolean {
  return !isBareIpHost() && window.location.hostname.includes("smart-locker");
}

// Which view this surface serves. Resolution order:
//   1. explicit override (window.__VIEW__)
//   2. subdomain  (admin.smart-locker.…)   — domain deployments
//   3. URL path   (/admin, /agent, /customer) — bare IP / localhost / fallback
//   4. landing
export function currentView(): View {
  const override = (window as any).__VIEW__;
  if (override) return override;

  const host = window.location.hostname;
  if (host.startsWith("admin.")) return "admin";
  if (host.startsWith("agent.")) return "agent";
  if (host.startsWith("customer.")) return "customer";

  // Path-based fallback: /admin, /agent, /customer (with or without trailing /).
  const seg = window.location.pathname.split("/").filter(Boolean)[0];
  if (seg && (VIEW_NAMES as string[]).includes(seg)) return seg as View;

  return "landing";
}

// URL that opens a given view, honouring the deployment's routing style.
//   subdomain mode: https://admin.smart-locker.yeng.click/
//   path mode:      http://56.69.57.18:8100/admin
export function viewUrl(view: View): string {
  const { protocol, host } = window.location;
  if (usesSubdomainRouting()) return `${protocol}//${view}.${host}/`;
  return `${protocol}//${host}/${view}`;
}

// Human-readable label for a view's destination (shown on the landing cards).
export function viewTarget(view: View): string {
  const { host } = window.location;
  return usesSubdomainRouting() ? `${view}.${host}` : `${host}/${view}`;
}

// The role required to use a given view surface.
export function requiredRoleFor(view: string): Role | null {
  switch (view) {
    case "admin":
      return "ADMIN";
    case "agent":
      return "AGENT";
    case "customer":
      return "CUSTOMER";
    default:
      return null; // landing needs no specific role
  }
}
