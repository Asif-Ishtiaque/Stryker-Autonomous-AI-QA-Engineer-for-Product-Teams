import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 font-semibold tracking-tight", className)}>
      <span className="relative flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-primary to-indigo-400">
        <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5 text-primary-foreground">
          <path d="M4 12L10 18L20 6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span>Stryker</span>
    </div>
  );
}
