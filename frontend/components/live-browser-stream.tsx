"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Loader2, VideoOff } from "lucide-react";
import { WS_BASE } from "@/lib/ws";
import { cn } from "@/lib/utils";

type StreamState = "connecting" | "live" | "ended" | "error";

/**
 * setLocalDescription() does NOT wait for ICE candidate gathering — candidates
 * normally arrive afterward via onicecandidate (trickle ICE). Since this
 * component sends exactly one SDP offer and never trickles further
 * candidates, that offer must already contain them, or the backend has no
 * way to reach this browser and ICE sits in "checking" until it times out.
 */
function waitForIceGatheringComplete(pc: RTCPeerConnection): Promise<void> {
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const onChange = () => {
      if (pc.iceGatheringState === "complete") {
        pc.removeEventListener("icegatheringstatechange", onChange);
        resolve();
      }
    };
    pc.addEventListener("icegatheringstatechange", onChange);
    // Safety net: proceed with whatever candidates exist so far rather than
    // hanging forever if gathering stalls (e.g. a slow/unreachable STUN server).
    setTimeout(() => {
      pc.removeEventListener("icegatheringstatechange", onChange);
      resolve();
    }, 4000);
  });
}

/**
 * True WebRTC live view of the browser a run is actually executing in.
 *
 * Signaling goes over `${WS_BASE}/api/v1/ws/runs/{runId}/stream` (see
 * backend/app/api/routers/stream.py): we send one SDP offer, get one SDP
 * answer back, then media flows peer-to-peer over the negotiated
 * RTCPeerConnection — no polling, no MJPEG-over-HTTP. The source is a CDP
 * screencast of the run's actual Playwright page (see
 * backend/app/agents/executors/web/screencast.py), relayed backend-worker →
 * backend-API over Redis, so this is the literal browser Stryker is driving,
 * not a synthetic re-render.
 */
export function LiveBrowserStream({ runId, enabled }: { runId: string; enabled: boolean }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [state, setState] = useState<StreamState>("connecting");

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    setState("connecting");

    // TURN is needed on THIS side too, not just the backend's: Chrome obfuscates host
    // candidates as mDNS ".local" hostnames by default (a privacy feature), and aiortc
    // (the Python backend) has no mDNS resolver — every host candidate this browser offers
    // is one the backend can never resolve, regardless of network reachability. Relay
    // candidates are never mDNS-obfuscated, so giving this side the same TURN server lets
    // both peers negotiate over real relay addresses (127.0.0.1:<port> via coturn) instead.
    const pc = new RTCPeerConnection({
      iceServers: [
        {
          urls: process.env.NEXT_PUBLIC_TURN_URL ?? "turn:localhost:3478",
          username: process.env.NEXT_PUBLIC_TURN_USERNAME ?? "stryker",
          credential: process.env.NEXT_PUBLIC_TURN_CREDENTIAL ?? "stryker-turn-secret",
        },
      ],
    });
    pc.addTransceiver("video", { direction: "recvonly" });

    pc.ontrack = (event) => {
      if (videoRef.current) videoRef.current.srcObject = event.streams[0];
      setState("live");
    };
    pc.onconnectionstatechange = () => {
      if (cancelled) return;
      if (pc.connectionState === "failed") setState("error");
      if (pc.connectionState === "closed") setState("ended");
    };

    const socket = new WebSocket(`${WS_BASE}/api/v1/ws/runs/${runId}/stream`);

    socket.onopen = async () => {
      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        await waitForIceGatheringComplete(pc);
        socket.send(JSON.stringify({ type: "offer", sdp: pc.localDescription?.sdp }));
      } catch {
        if (!cancelled) setState("error");
      }
    };
    socket.onmessage = async (event) => {
      try {
        const answer = JSON.parse(event.data);
        if (answer.type === "answer" && !cancelled) {
          await pc.setRemoteDescription({ type: "answer", sdp: answer.sdp });
        }
      } catch {
        if (!cancelled) setState("error");
      }
    };
    socket.onerror = () => {
      if (!cancelled) setState("error");
    };

    return () => {
      cancelled = true;
      socket.close();
      pc.close();
    };
  }, [runId, enabled]);

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-border bg-black">
      <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-contain" />
      {state !== "live" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/80 text-sm text-muted-foreground">
          {state === "connecting" && (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Connecting to live browser…
            </>
          )}
          {state === "error" && (
            <>
              <VideoOff className="h-5 w-5" />
              Live video unavailable — evidence screenshots below are still capturing.
            </>
          )}
          {state === "ended" && (
            <>
              <Camera className="h-5 w-5" />
              Run finished — stream closed.
            </>
          )}
        </div>
      )}
      <span
        className={cn(
          "absolute right-2 top-2 flex items-center gap-1.5 rounded-full border bg-background/80 px-2 py-0.5 text-xs font-medium",
          state === "live" ? "border-success/40 text-success" : "border-border text-muted-foreground",
        )}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", state === "live" ? "animate-pulse bg-success" : "bg-muted-foreground")} />
        {state === "live" ? "Live" : state}
      </span>
    </div>
  );
}
