// Production API client. Identical surface to the POC's api.ts, but every call
// goes through authFetch so the JWT bearer token is attached and 401s clear the
// session. This file REPLACES the POC's src/api.ts in the production build.
import { authFetch } from "./auth";

export type Size = "SMALL" | "MEDIUM" | "LARGE";

export interface Dimensions {
  width_cm: number;
  depth_cm: number;
  height_cm: number;
  volume_litres: number;
}

export interface SizeSpec {
  size: Size;
  dimensions: Dimensions;
  label: string;
}

export interface Locker {
  id: string;
  size: Size;
  status: "AVAILABLE" | "HELD" | "OCCUPIED" | "OPEN";
  created_at: string;
  dimensions: Dimensions;
}

export interface HoldResult {
  held: boolean;
  package_id: string | null;
  locker_id: string | null;
  pickup_code: string | null;
  message: string;
}

export interface CompleteResult {
  stored: boolean;
  locker_id: string | null;
  pickup_code: string | null;
  package_id: string | null;
  message: string;
}

export interface CancelResult {
  cancelled: boolean;
  message: string;
}

export interface PickupResult {
  opened: boolean;
  locker_id: string | null;
  package_id: string | null;
  storage_charge: number | null;
  stored_at: string | null;
  retrieved_at: string | null;
  billable_days: number | null;
  message: string;
}

export interface CloseResult {
  closed: boolean;
  message: string;
}

export interface Notification {
  id: number;
  ts: string;
  event_type: string;
  outcome: "SUCCESS" | "FAILURE";
  locker_id: string | null;
  package_id: string | null;
  detail: string;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  listSizes: () => authFetch("/api/sizes").then(json<SizeSpec[]>),
  listLockers: () => authFetch("/api/lockers").then(json<Locker[]>),
  createLocker: (size: Size) =>
    authFetch("/api/lockers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ size }),
    }).then(json<Locker>),
  holdLocker: (size: Size) =>
    authFetch("/api/packages/hold", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ size }),
    }).then(json<HoldResult>),
  completeStore: (package_id: string) =>
    authFetch("/api/packages/complete", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ package_id }),
    }).then(json<CompleteResult>),
  cancelHold: (package_id: string) =>
    authFetch("/api/packages/cancel", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ package_id }),
    }).then(json<CancelResult>),
  openPickup: (locker_id: string, pickup_code: string) =>
    authFetch("/api/pickups/open", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ locker_id, pickup_code }),
    }).then(json<PickupResult>),
  closePickup: (locker_id: string) =>
    authFetch("/api/pickups/close", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ locker_id }),
    }).then(json<CloseResult>),
  notifications: () => authFetch("/api/notifications").then(json<Notification[]>),
};
