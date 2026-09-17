import { useEffect, useState } from "react";
import { api, CompleteResult, HoldResult, Locker, Size, SizeSpec } from "../api";
import { formatDimensions, formatVolume } from "../format";
import CopyButton from "./CopyButton";
import Page from "./Page";

// Smallest -> largest. Index doubles as the fit rank (mirrors the backend).
const SIZES: Size[] = ["SMALL", "MEDIUM", "LARGE"];
const sizeRank = (s: Size) => SIZES.indexOf(s);

function randomSize(): Size {
  return SIZES[Math.floor(Math.random() * SIZES.length)];
}

// Smallest AVAILABLE locker that fits the package (rank >= package rank),
// tie-broken by id — the same choice hold_locker would make on the backend.
function recommendLocker(lockers: Locker[], size: Size): Locker | null {
  const fitting = lockers
    .filter((l) => l.status === "AVAILABLE" && sizeRank(l.size) >= sizeRank(size))
    .sort((a, b) => sizeRank(a.size) - sizeRank(b.size) || a.id.localeCompare(b.id));
  return fitting[0] ?? null;
}

export function AgentBody() {
  const [size, setSize] = useState<Size>(randomSize); // incoming parcel size (simulated)
  const [specs, setSpecs] = useState<SizeSpec[]>([]);
  const [lockers, setLockers] = useState<Locker[]>([]);
  const [hold, setHold] = useState<HoldResult | null>(null); // step 2 state (a live hold)
  const [done, setDone] = useState<CompleteResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listSizes().then(setSpecs).catch(() => setSpecs([]));
  }, []);

  async function refreshLockers() {
    try {
      setLockers(await api.listLockers());
    } catch {
      // Non-fatal; the recommendation just goes stale until the next poll.
    }
  }

  // Poll availability so admin-created (or freed) lockers update the
  // recommendation live. Pause polling while a hold is in progress (step 2).
  useEffect(() => {
    if (hold) return;
    refreshLockers();
    const t = setInterval(refreshLockers, 3000);
    return () => clearInterval(t);
  }, [hold]);

  const selectedSpec = specs.find((s) => s.size === size) ?? null;
  const recommended = recommendLocker(lockers, size);

  // Re-roll the incoming package; the recommendation recomputes from state.
  function changePackage() {
    setNotice(null);
    setDone(null);
    setSize((prev) => {
      // Avoid repeating the same size so "Change package" always feels responsive.
      let next = randomSize();
      if (SIZES.length > 1) while (next === prev) next = randomSize();
      return next;
    });
  }

  // Step 1: reserve a locker and open its door.
  async function openLocker() {
    setBusy(true);
    setNotice(null);
    setDone(null);
    try {
      const res = await api.holdLocker(size);
      if (res.held) setHold(res);
      else {
        setNotice(res.message);
        refreshLockers(); // availability may have changed; refresh the recommendation
      }
    } catch {
      setNotice("Something went wrong reaching the locker system. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  // Step 2a: confirm the package is inside; close and store.
  async function confirmStored() {
    if (!hold?.package_id) return;
    setBusy(true);
    setNotice(null);
    try {
      const res = await api.completeStore(hold.package_id);
      setDone(res);
      setHold(null);
      setSize(randomSize()); // next incoming parcel
    } catch {
      setNotice("Couldn't confirm the package. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  // Step 2b: back out; release the locker.
  async function cancel() {
    if (!hold?.package_id) return;
    setBusy(true);
    setNotice(null);
    try {
      const res = await api.cancelHold(hold.package_id);
      setNotice(res.message);
      setHold(null);
    } catch {
      setNotice("Couldn't release the locker. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Store a package</h2>

      {/* Step 1 — an incoming parcel + the recommended locker */}
      {!hold && (
        <>
          <p className="muted">Step 1 of 2 — here's the incoming parcel and the locker we recommend.</p>

          <label>Incoming package</label>
          <div className="parcel">
            <span className="parcel-size">📦 {size}</span>
            {selectedSpec && (
              <span className="muted">{formatDimensions(selectedSpec.dimensions)} · {formatVolume(selectedSpec.dimensions)}</span>
            )}
            {selectedSpec && <div className="muted">{selectedSpec.label}</div>}
          </div>
          <button className="btn-secondary" onClick={changePackage} disabled={busy}>
            🔄 Change package
          </button>

          <label>Recommended locker</label>
          {recommended ? (
            <div className="reco">
              <span className="reco-id">✅ {recommended.id}</span>
              <span className="muted">{recommended.size} · {formatDimensions(recommended.dimensions)}</span>
              {recommended.size !== size && (
                <div className="muted">No {size} locker free — recommending the next size up.</div>
              )}
            </div>
          ) : (
            <div className="result err">
              <p>No locker is free for a {size} package right now.</p>
              <p className="muted">Try "Change package", or wait for a locker to free up — this updates automatically.</p>
            </div>
          )}

          <button onClick={openLocker} disabled={busy || !recommended}>
            {busy ? "Finding a locker…" : recommended ? `Open ${recommended.id}` : "No locker available"}
          </button>

          {done && (
            <div className="result ok">
              <p>{done.message}</p>
              <p className="muted">Pickup code shared with customer</p>
              <div className="code-row">
                <span className="code">{done.pickup_code}</span>
                {done.pickup_code && <CopyButton value={done.pickup_code} label="Copy code" />}
              </div>
              <button onClick={() => setDone(null)} disabled={busy}>Store another package</button>
            </div>
          )}
          {notice && <div className="result err"><p>{notice}</p></div>}
        </>
      )}

      {/* Step 2 — locker open, confirm or cancel */}
      {hold && (
        <div className="result ok">
          <p className="muted">Step 2 of 2 — the locker is open</p>
          <p style={{ fontSize: "1.25rem", margin: "6px 0" }}>
            🔓 Locker <strong>{hold.locker_id}</strong> is open
          </p>
          <p>{hold.message}</p>
          <p className="muted">Pickup code (shared once you confirm)</p>
          <div className="code-row">
            <span className="code">{hold.pickup_code}</span>
            {hold.pickup_code && <CopyButton value={hold.pickup_code} label="Copy code" />}
          </div>
          <button onClick={confirmStored} disabled={busy}>
            {busy ? "Closing…" : "✓ Confirm package is inside"}
          </button>
          <button className="btn-secondary" onClick={cancel} disabled={busy}>
            Cancel &amp; release locker
          </button>
          {notice && <div className="result err"><p>{notice}</p></div>}
        </div>
      )}
    </div>
  );
}

export default function Agent() {
  return (
    <Page title="Delivery Agent" icon="🚚" mobile>
      <AgentBody />
    </Page>
  );
}
