import { useEffect, useState } from "react";
import { api, Locker, Notification, Size, SizeSpec } from "../api";
import { formatDimensions, formatVolume } from "../format";
import Page from "./Page";

const SIZES: Size[] = ["SMALL", "MEDIUM", "LARGE"];

export function AdminBody() {
  const [lockers, setLockers] = useState<Locker[]>([]);
  const [logs, setLogs] = useState<Notification[]>([]);
  const [specs, setSpecs] = useState<SizeSpec[]>([]);
  const [size, setSize] = useState<Size>("SMALL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSpec = specs.find((s) => s.size === size) ?? null;

  async function refresh() {
    try {
      const [l, n] = await Promise.all([api.listLockers(), api.notifications()]);
      setLockers(l);
      setLogs(n);
      setError(null);
    } catch {
      setError("Couldn't reach the backend. Retrying…");
    }
  }

  useEffect(() => {
    api.listSizes().then(setSpecs).catch(() => setSpecs([]));
    refresh();
    const t = setInterval(refresh, 3000); // auto-refresh transaction log
    return () => clearInterval(t);
  }, []);

  async function createLocker() {
    setBusy(true);
    setError(null);
    try {
      await api.createLocker(size);
      await refresh();
    } catch {
      setError("Couldn't create the locker. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Create locker</h2>
        <label>Size</label>
        <select value={size} onChange={(e) => setSize(e.target.value as Size)}>
          {SIZES.map((s) => {
            const spec = specs.find((x) => x.size === s);
            return (
              <option key={s} value={s}>
                {s}{spec ? ` — ${formatDimensions(spec.dimensions)} (${formatVolume(spec.dimensions)})` : ""}
              </option>
            );
          })}
        </select>
        {selectedSpec && (
          <div className="size-info muted">
            <span>📦 {formatDimensions(selectedSpec.dimensions)} · {formatVolume(selectedSpec.dimensions)}</span>
            <div>{selectedSpec.label}</div>
          </div>
        )}
        <button onClick={createLocker} disabled={busy}>{busy ? "Adding…" : "Add locker"}</button>
        {error && <div className="result err"><p>{error}</p></div>}
      </div>

      <div className="card">
        <h2>Locker map</h2>
        <p className="muted">Grouped by size, top to bottom: small, medium, large. Footprint scales (1&times;1 / 2&times;2 / 3&times;3). Green = free, blue = on hold, amber = in use, purple = open for pickup.</p>
        {lockers.length === 0 && <p className="muted">No lockers yet.</p>}
        {SIZES.map((s) => {
          const row = lockers.filter((l) => l.size === s);
          if (row.length === 0) return null;
          const cell = { SMALL: 72, MEDIUM: 108, LARGE: 144 }[s];
          return (
            <div className="locker-row" key={s}>
              <div className="locker-row-label">{s} ({row.length})</div>
              <div className="locker-row-cells">
                {row.map((l) => (
                  <div
                    key={l.id}
                    className={`locker-cell ${l.status.toLowerCase()}`}
                    style={{ width: cell, height: cell }}
                    title={`${l.id} · ${l.size} · ${l.status} · ${formatDimensions(l.dimensions)} (${formatVolume(l.dimensions)})`}
                  >
                    <span className="locker-id">{l.id}</span>
                    <span className="locker-size">{l.size}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="card">
        <h2>Lockers ({lockers.length})</h2>
        <table>
          <thead>
            <tr><th>ID</th><th>Size</th><th>Dimensions (W×D×H)</th><th>Volume</th><th>Status</th></tr>
          </thead>
          <tbody>
            {lockers.map((l) => (
              <tr key={l.id}>
                <td>{l.id}</td>
                <td>{l.size}</td>
                <td className="muted">{formatDimensions(l.dimensions)}</td>
                <td className="muted">{formatVolume(l.dimensions)}</td>
                <td><span className={`badge ${l.status.toLowerCase()}`}>{l.status}</span></td>
              </tr>
            ))}
            {lockers.length === 0 && (
              <tr><td colSpan={5} className="muted">No lockers yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Notification / transaction log</h2>
        <p className="muted">Auto-refreshes every 3s. Newest first.</p>
        <table>
          <thead>
            <tr><th>Time</th><th>Event</th><th>Outcome</th><th>Locker</th><th>Package</th><th>Detail</th></tr>
          </thead>
          <tbody>
            {logs.map((n) => (
              <tr key={n.id}>
                <td>{new Date(n.ts).toLocaleTimeString()}</td>
                <td>{n.event_type}</td>
                <td><span className={`badge ${n.outcome}`}>{n.outcome}</span></td>
                <td>{n.locker_id ?? "-"}</td>
                <td>{n.package_id ?? "-"}</td>
                <td className="muted">{n.detail}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={6} className="muted">No transactions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Admin() {
  return (
    <Page title="Master System View" icon="🗄️">
      <AdminBody />
    </Page>
  );
}
