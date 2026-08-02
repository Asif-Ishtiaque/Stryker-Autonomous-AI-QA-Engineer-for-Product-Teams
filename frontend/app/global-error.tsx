"use client";

import { useEffect } from "react";

/**
 * Catches errors thrown by the root layout itself (app/layout.tsx) — the one
 * case app/error.tsx can't cover, since a boundary can't catch errors in its
 * own parent layout. Per Next.js's App Router contract this must render its
 * own <html>/<body>, since it replaces the root layout entirely when active.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Unhandled root layout error", error);
  }, [error]);

  return (
    <html lang="en" className="dark">
      <body style={{ background: "#0a0a0f", color: "#e5e5e5", fontFamily: "sans-serif" }}>
        <div style={{ display: "flex", height: "100vh", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, textAlign: "center", padding: 24 }}>
          <h1 style={{ fontSize: 18, fontWeight: 600 }}>Something went wrong</h1>
          <p style={{ maxWidth: 320, fontSize: 14, opacity: 0.7 }}>
            The application failed to load. Try refreshing the page.
          </p>
          <button
            onClick={reset}
            style={{ padding: "8px 16px", borderRadius: 8, background: "#6d5ef2", color: "white", border: "none", cursor: "pointer" }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
