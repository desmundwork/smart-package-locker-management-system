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

// Which view this deployment surface serves, derived from the hostname:
//   admin.smart-locker.*    -> admin
//   agent.smart-locker.*    -> agent
//   customer.smart-locker.* -> customer
//   smart-locker.*          -> landing
// A build-time/global override (window.__VIEW__) wins if present.
export function currentView(): "landing" | "admin" | "agent" | "customer" {
  const override = (window as any).__VIEW__;
  if (override) return override;
  const host = window.location.hostname;
  if (host.startsWith("admin.")) return "admin";
  if (host.startsWith("agent.")) return "agent";
  if (host.startsWith("customer.")) return "customer";
  return "landing";
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
