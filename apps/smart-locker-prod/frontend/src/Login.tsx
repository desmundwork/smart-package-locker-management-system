import React, { useState } from "react";
import { login } from "./auth";

/**
 * Login gate shown when a protected view is opened without a valid session.
 * On success it stores the token and calls onSuccess so the parent re-renders
 * the underlying view.
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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: "10vh auto", fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 20 }}>Smart Locker — {view}</h1>
      <p style={{ color: "#666", fontSize: 14 }}>Sign in to continue.</p>
      <form onSubmit={submit}>
        <label style={{ display: "block", marginBottom: 8 }}>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        <label style={{ display: "block", marginBottom: 8 }}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        {error && <p style={{ color: "#c00", fontSize: 14 }}>{error}</p>}
        <button type="submit" disabled={busy} style={{ padding: "8px 16px" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
