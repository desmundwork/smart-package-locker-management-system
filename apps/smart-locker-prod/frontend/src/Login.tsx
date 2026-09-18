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
 * In REVIEW_MODE the backend returns the seeded demo credentials for this view,
 * which we show in a panel with one-click prefill so reviewers can sign in
 * without hunting for passwords.
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
    <div style={{ maxWidth: 420, margin: "8vh auto", padding: "0 16px", fontFamily: "system-ui" }}>
      {/* Enlarged, emphasized module identity */}
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <div style={{ fontSize: 64, lineHeight: 1 }} aria-hidden="true">
          {meta.icon}
        </div>
        <div
          style={{
            fontSize: 13,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: "#888",
            marginTop: 12,
          }}
        >
          Smart Package Locker
        </div>
        <h1 style={{ fontSize: 34, fontWeight: 800, margin: "4px 0 0" }}>{meta.title}</h1>
        <p style={{ color: "#666", fontSize: 15, marginTop: 6 }}>
          Sign in to the {meta.title} module.
        </p>
      </div>

      {/* Reviewer credentials panel (only when the backend is in review mode) */}
      {demo && (
        <div
          style={{
            border: "1px solid #d6e4ff",
            background: "#f0f6ff",
            borderRadius: 10,
            padding: "12px 14px",
            marginBottom: 18,
            fontSize: 14,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 4 }}>
            🔎 Reviewer credentials (verification stage)
          </div>
          <div style={{ fontFamily: "ui-monospace, Menlo, monospace" }}>
            <div>username: <b>{demo.username}</b></div>
            <div>password: <b>{demo.password}</b></div>
          </div>
          <button
            type="button"
            onClick={() => doLogin(demo.username, demo.password)}
            disabled={busy}
            style={{
              marginTop: 10,
              padding: "8px 14px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {busy ? "Signing in…" : `Sign in as ${demo.role}`}
          </button>
          <div style={{ color: "#7a7a7a", fontSize: 12, marginTop: 8 }}>
            Shown because REVIEW_MODE is on. Disable it for real production.
          </div>
        </div>
      )}

      <form onSubmit={submit}>
        <label style={{ display: "block", marginBottom: 12 }}>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            style={{ width: "100%", padding: 10, marginTop: 4, fontSize: 15 }}
          />
        </label>
        <label style={{ display: "block", marginBottom: 12 }}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            style={{ width: "100%", padding: 10, marginTop: 4, fontSize: 15 }}
          />
        </label>
        {error && <p style={{ color: "#c00", fontSize: 14 }}>{error}</p>}
        <button
          type="submit"
          disabled={busy}
          style={{ padding: "10px 20px", fontSize: 15, fontWeight: 600, cursor: "pointer" }}
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
