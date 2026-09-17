import { useEffect, useState } from "react";
import { api, Locker, PickupResult, Size } from "../api";
import { formatCharge, formatDimensions } from "../format";
import Page from "./Page";

// Same size ordering + footprint scaling as the Admin locker map, so the
// customer sees lockers arranged consistently across views.
const SIZES: Size[] = ["SMALL", "MEDIUM", "LARGE"];
const CELL_PX: Record<Size, number> = { SMALL: 72, MEDIUM: 108, LARGE: 144 };

export function CustomerBody() {
  const [lockerId, setLockerId] = useState("");
  const [code, setCode] = useState("");
  const [lockers, setLockers] = useState<Locker[]>([]);
  const [open, setOpen] = useState<PickupResult | null>(null); // step 2 state (locker unlocked)
  const [error, setError] = useState<string | null>(null);
  const [doneMsg, setDoneMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Lockers currently holding a package awaiting pickup are the selectable set.
  const pickable = lockers.filter((l) => l.status === "OCCUPIED");

  async function refresh() {
    try {
      setLockers(await api.listLockers());
    } catch {
      // Non-fatal: the grid stays as-is; the unlock call surfaces errors.
    }
  }

  // Keep the grid current while on step 1 (another pickup may change what's
  // awaiting). Stop polling once a locker is open (step 2).
  useEffect(() => {
    if (open) return;
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [open]);

  // If the selected locker stops being pickable (someone else collected it),
  // clear the stale selection.
  useEffect(() => {
    if (lockerId && !pickable.some((l) => l.id === lockerId)) setLockerId("");
  }, [lockers]); // eslint-disable-line react-hooks/exhaustive-deps

  // Step 1: validate the code and unlock the selected locker.
  async function openLocker() {
    setBusy(true);
    setError(null);
    setDoneMsg(null);
    try {
      const res = await api.openPickup(lockerId.trim(), code.trim().toUpperCase());
      if (res.opened) setOpen(res);
      else setError(res.message);
    } catch {
      setError("Something went wrong reaching the locker system. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  // Step 2: customer confirms the door is shut; locker becomes available again.
  async function closeLocker() {
    if (!open?.locker_id) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.closePickup(open.locker_id);
      setDoneMsg(res.message);
      setOpen(null);
      setLockerId("");
      setCode("");
    } catch {
      setError("Couldn't confirm the door is closed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Collect your package</h2>

      {/* Step 1 — pick your locker and enter the code */}
      {!open && (
        <>
          <p className="muted">Step 1 of 2 — tap your locker, then enter your pickup code.</p>

          <label>Available lockers</label>
          {pickable.length === 0 ? (
            <p className="muted">No packages are waiting for pickup right now.</p>
          ) : (
            <div role="radiogroup" aria-label="Select an available locker">
              {SIZES.map((s) => {
                const row = pickable.filter((l) => l.size === s);
                if (row.length === 0) return null;
                const cell = CELL_PX[s];
                return (
                  <div className="locker-row" key={s}>
                    <div className="locker-row-label">{s} ({row.length})</div>
                    <div className="locker-row-cells">
                      {row.map((l) => {
                        const selected = l.id === lockerId;
                        return (
                          <button
                            key={l.id}
                            type="button"
                            role="radio"
                            aria-checked={selected}
                            className={`locker-cell occupied picker-cell${selected ? " selected" : ""}`}
                            style={{ width: cell, height: cell }}
                            onClick={() => setLockerId(selected ? "" : l.id)}
                            disabled={busy}
                            title={`${l.id} · ${l.size} · ${formatDimensions(l.dimensions)}`}
                          >
                            <span className="locker-id">{l.id}</span>
                            <span className="locker-size">{l.size}</span>
                            {selected && <span className="picker-check" aria-hidden="true">✓</span>}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <label>Pickup code</label>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="6-character code"
            disabled={busy}
            inputMode="text"
            autoCapitalize="characters"
          />
          <button onClick={openLocker} disabled={busy || !lockerId || !code}>
            {busy ? "Checking…" : lockerId ? `🔓 Unlock ${lockerId}` : "🔓 Select a locker first"}
          </button>

          {doneMsg && <div className="result ok"><p>🎉 {doneMsg}</p></div>}
          {error && <div className="result err"><p>{error}</p></div>}
        </>
      )}

      {/* Step 2 — locker unlocked, confirm door closed */}
      {open && (
        <div className="result ok">
          <p className="muted">Step 2 of 2 — your locker is open</p>
          <p style={{ fontSize: "1.25rem", margin: "6px 0" }}>
            🔓 Locker <strong>{open.locker_id}</strong> is unlocked
          </p>
          <p>{open.message}</p>
          <div className="charge">
            <span className="charge-amount">Storage charge: {formatCharge(open.storage_charge)}</span>
            {open.billable_days != null && (
              <span className="muted">
                {open.billable_days} billable day{open.billable_days === 1 ? "" : "s"}
                {open.stored_at ? ` · stored ${new Date(open.stored_at).toLocaleString()}` : ""}
              </span>
            )}
          </div>
          <button onClick={closeLocker} disabled={busy}>
            {busy ? "Closing…" : "🔒 I've taken my package — close the door"}
          </button>
          <p className="muted" style={{ marginTop: 8 }}>
            Please close the door so the locker is secured for the next customer.
          </p>
          {error && <div className="result err"><p>{error}</p></div>}
        </div>
      )}
    </div>
  );
}

export default function Customer() {
  return (
    <Page title="Customer Pickup" icon="🙋" mobile>
      <CustomerBody />
    </Page>
  );
}
