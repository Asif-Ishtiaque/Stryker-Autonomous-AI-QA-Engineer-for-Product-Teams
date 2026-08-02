import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Renders when a query's `isError` is true. Without this, callers that only
 * branch on isLoading/empty-data collapse a fetch failure into either a
 * misleading "no data yet" empty state or a permanent loading skeleton
 * (isLoading goes false, but the expected data never arrives) — the user
 * sees nothing telling them a request actually failed, just gets stuck.
 */
export function ErrorState({
  title = "Couldn't load this",
  description = "Something went wrong fetching this data.",
  onRetry,
  className,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-destructive/40 py-16 text-center",
        className,
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-5 w-5 text-destructive" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="mx-auto max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}
