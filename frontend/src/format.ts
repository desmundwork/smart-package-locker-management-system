import { Dimensions } from "./api";

// "30 × 40 × 15 cm" — W × D × H.
export function formatDimensions(d: Dimensions): string {
  return `${d.width_cm} × ${d.depth_cm} × ${d.height_cm} cm`;
}

// "18 L" — interior volume.
export function formatVolume(d: Dimensions): string {
  return `${d.volume_litres} L`;
}

// Money-style storage charge; falls back gracefully when absent.
export function formatCharge(amount: number | null): string {
  if (amount == null) return "—";
  return `$${amount.toFixed(2)}`;
}
