"use client";

import { useEffect, useRef, useState } from "react";
import { TERMINAL_RUN_STATUSES, type RunStepEvent } from "./types";

export const WS_BASE = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/\/+$/, "");

export type SocketState = "connecting" | "open" | "closed" | "error";

/**
 * Subscribes to live execution events for a run over
 * `${NEXT_PUBLIC_WS_URL}/api/v1/ws/runs/{run_id}`.
 *
 * NOTE (known limitation, phase 1): the backend WebSocket endpoint
 * (app/api/routers/ws.py) does not authenticate the connection — anyone who
 * knows the run_id can subscribe. This is acceptable for now per the backend
 * team but should be revisited before this is exposed outside a trusted network.
 */
export function useRunEvents(runId: string | null, opts: { enabled?: boolean } = {}) {
  const { enabled = true } = opts;
  const [events, setEvents] = useState<RunStepEvent[]>([]);
  const [state, setState] = useState<SocketState>("connecting");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId || !enabled) return;

    setEvents([]);
    setState("connecting");

    const socket = new WebSocket(`${WS_BASE}/api/v1/ws/runs/${runId}`);
    socketRef.current = socket;

    socket.onopen = () => setState("open");

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as RunStepEvent;
        setEvents((prev) => [...prev, payload]);
        if (TERMINAL_RUN_STATUSES.includes(payload.run_status)) {
          socket.close();
        }
      } catch {
        // Ignore malformed frames rather than crashing the live view.
      }
    };

    socket.onerror = () => setState("error");
    socket.onclose = () => setState("closed");

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [runId, enabled]);

  return { events, state };
}
