import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formats a millisecond duration as e.g. "1m 12s" / "340ms". */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

/** Formats a 0..1 confidence score as a percentage string. */
export function formatConfidence(score: number | null | undefined): string {
  if (score == null) return "—";
  // Clamp defensively — matches ConfidenceGauge. The backend now clamps confidence at the
  // source, but a value already sitting in the DB from before that fix (or any future write
  // path that forgets to) should never render as a nonsensical "2389%".
  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
