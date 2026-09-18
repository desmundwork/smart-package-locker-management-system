import React, { useEffect, useState } from "react";
import { DemoCredential, fetchDemoCredentials, login } from "./auth";

const VIEW_META: Record<string, { title: string; icon: string }> = {
  admin: { title: "Admin", icon: "🗄️" },
  agent: { title: "Delivery Agent", icon: "🚚" },
  customer: { title: "Customer", icon: "🙋" },
};

/**
 * Login gate shown when a protected view is opened without a valid session.
 * On success it stores the token and calls onSuccess so the parent re-renders
 * the underlying view.
 *
 * Styled with the app's dark theme tokens (var(--bg/panel/accent/...) from
 * styles.css) for visual consistency with the operator views. In REVIEW_MODE
 * the backend returns the seeded demo credentials for this view, shown in a
 * panel with one-click prefill so reviewers can sign in easily.
 */
export default function Login({
  view,
  onSuccess,
}: {
  view: string;
  onSuccess: () => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<DemoCredential | null>(null);

  const meta = VIEW_META[view] ?? { title: view, icon: "🔐" };
  const targetHost = typeof window !== "undefined" ? window.location.host : "";

  useEffect(() => {
    let active = true;
    fetchDemoCredentials(view).then((res) => {
      if (!active) return;
      if (res.review_mode && res.credentials.length > 0) {
        setDemo(res.credentials[0]);
      }
    });
    return () => {
      active = false;
    };
  }, [view]);

  async function doLogin(u: string, p: string) {
    setError(null);
    setBusy(true);
    try {
      await login(u, p);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await doLogin(username, password);
  }

  return (
    <>
      <div className="header">
        <div className="logo">E.</div>
        <h1>Smart Package Locker Management System</h1>
      </div>

      <div className="wrap mobile">
        {/* Enlarged, emphasized module identity */}
        <div style={{ textAlign: "center", margin: "16px 0 24px" }}>
          <div style={{ fontSize: 60, lineHeight: 1 }} aria-hidden="true">
            {meta.icon}
          </div>
          <div
            className="muted"
            style={{ letterSpacing: 2, textTransform: "uppercase", marginTop: 12 }}
          >
            Smart Package Locker
          </div>
          <h2 style={{ fontSize: "2rem", fontWeight: 800, margin: "4px 0 0", color: "var(--accent)" }}>
            {meta.title}
          </h2>
          <p className="muted" style={{ fontSize: ".95rem", marginTop: 6 }}>
            Sign in to the {meta.title} module{targetHost ? ` · ${targetHost}` : ""}.
          </p>
        </div>

        {/* Reviewer credentials panel (only when the backend is in review mode) */}
        {demo && (
          <div
            className="card"
            style={{ borderColor: "var(--accent)" }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--accent)" }}>
              🔎 Reviewer credentials (verification stage)
            </div>
            <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: ".95rem" }}>
              <div>
                username: <b style={{ color: "var(--accent)" }}>{demo.username}</b>
              </div>
              <div>
                password: <b style={{ color: "var(--accent)" }}>{demo.password}</b>
              </div>
            </div>
            <button
              type="button"
              onClick={() => doLogin(demo.username, demo.password)}
              disabled={busy}
            >
              {busy ? "Signing in…" : `Sign in as ${demo.role}`}
            </button>
            <div className="muted" style={{ fontSize: ".78rem", marginTop: 8 }}>
              Shown because REVIEW_MODE is on. Disable it for real production.
            </div>
          </div>
        )}

        <form className="card" onSubmit={submit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <p style={{ color: "#f19a94", fontSize: ".9rem", marginBottom: 0 }}>{error}</p>
          )}
          <button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </>
  );
}
