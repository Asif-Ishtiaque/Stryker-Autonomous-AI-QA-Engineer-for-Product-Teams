import { RunStatus, TERMINAL_RUN_STATUSES, type RunStepEvent, type RunOut, type StepStatus } from "./types";

export interface LiveStepView {
  key: string;
  sequence: number;
  name: string;
  status: StepStatus | string;
  message?: string | null;
  stepId?: string | null;
  evidence?: { id: string; evidence_type: string }[];
}

/**
 * The backend only persists Step rows once the whole run finishes (see
 * backend/app/execution/tasks.py::_persist_final_state) — while a run is in
 * progress, the *only* source of per-step truth is the stream of
 * RunStepEvent frames over the WebSocket. This folds those events into an
 * ordered, deduplicated-by-sequence list suitable for rendering a live
 * timeline before the authoritative Step+Evidence rows exist.
 */
export function deriveLiveSteps(events: RunStepEvent[]): LiveStepView[] {
  const bySequence = new Map<number, LiveStepView>();
  for (const event of events) {
    if (event.sequence == null || !event.name) continue;
    bySequence.set(event.sequence, {
      key: `live-${event.sequence}`,
      sequence: event.sequence,
      name: event.name,
      status: event.step_status ?? "waiting",
      message: event.message,
      stepId: event.step_id,
      evidence: event.evidence ?? undefined,
    });
  }
  return Array.from(bySequence.values()).sort((a, b) => a.sequence - b.sequence);
}

export interface ReasoningEntry {
  key: string;
  sequence: number | null;
  text: string;
}

/** AI Reasoning panel feed — every `reasoning` narration emitted by the executor as it works. */
export function deriveReasoningLog(events: RunStepEvent[]): ReasoningEntry[] {
  return events
    .filter((e) => e.reasoning)
    .map((e, idx) => ({ key: `reason-${idx}`, sequence: e.sequence ?? null, text: e.reasoning as string }));
}

export interface ConsoleEntry {
  key: string;
  type: string;
  text: string;
}

/** Live Console panel feed — every browser console message as it's emitted, not just the last 50 at step-end. */
export function deriveConsoleLog(events: RunStepEvent[]): ConsoleEntry[] {
  return events
    .filter((e) => e.console)
    .map((e, idx) => ({ key: `console-${idx}`, type: e.console!.type, text: e.console!.text }));
}

export interface NetworkEntry {
  key: string;
  url: string;
  method: string;
}

/** Live Network panel feed — every finished request as it happens, not just the last 50 at step-end. */
export function deriveNetworkLog(events: RunStepEvent[]): NetworkEntry[] {
  return events
    .filter((e) => e.network)
    .map((e, idx) => ({ key: `network-${idx}`, url: e.network!.url, method: e.network!.method }));
}

/** The latest run-level status seen over the socket, falling back to the last known REST value. */
export function latestRunStatus(events: RunStepEvent[], fallback: RunStatus): RunStatus {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].run_status) return events[i].run_status;
  }
  return fallback;
}

/** The most recent free-text status message that isn't tied to a specific step (e.g. "Generating execution plan"). */
export function latestPhaseMessage(events: RunStepEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].sequence == null && events[i].message) return events[i].message ?? null;
  }
  return null;
}

export function latestConfidenceScore(events: RunStepEvent[], fallback: number | null | undefined): number | null {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].confidence_score != null) return events[i].confidence_score as number;
  }
  return fallback ?? null;
}

export function isRunTerminal(status: RunStatus): boolean {
  return TERMINAL_RUN_STATUSES.includes(status);
}

export function hasStepsData(run: RunOut | undefined): boolean {
  return !!run && run.steps.length > 0;
}
