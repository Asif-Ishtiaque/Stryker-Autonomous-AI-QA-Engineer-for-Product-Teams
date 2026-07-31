import { RunStatus, TERMINAL_RUN_STATUSES, type RunStepEvent, type RunOut, type StepStatus } from "./types";

export interface LiveStepView {
  key: string;
  sequence: number;
  name: string;
  status: StepStatus | string;
  message?: string | null;
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
    });
  }
  return Array.from(bySequence.values()).sort((a, b) => a.sequence - b.sequence);
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
