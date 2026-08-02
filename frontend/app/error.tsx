"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Catches unhandled render errors anywhere under the root layout (both the
 * (auth) and (dashboard) route groups). Without this, an uncaught exception
 * in any client component — a null-deref building dashboard stats, a bad
 * validation_checklist shape hitting JSON.stringify, etc. — falls through to
 * Next's default handling with no local recovery affordance: a blank/broken
 * page with no "try again" for the user. See global-error.tsx for the
 * (rarer) case of an error in the root layout itself.
 */
export default function ErrorBoundary({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Unhandled render error", error);
  }, [error]);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background p-6 text-center">
      <AlertTriangle className="h-10 w-10 text-destructive" />
      <div>
        <h1 className="text-lg font-semibold">Something went wrong</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          An unexpected error occurred while rendering this page. You can try again, or go back and retry.
        </p>
      </div>
      <Button onClick={reset}>
        <RotateCw className="h-3.5 w-3.5" />
        Try again
      </Button>
    </div>
  );
}
