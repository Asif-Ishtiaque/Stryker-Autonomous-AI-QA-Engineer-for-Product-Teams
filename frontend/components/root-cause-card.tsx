import { AlertTriangle, Eye, Target, User, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatConfidence } from "@/lib/utils";
import type { RootCauseAnalysis } from "@/lib/types";

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

const COMPONENT_LABEL: Record<string, string> = {
  frontend: "Frontend",
  backend: "Backend",
  api: "API",
  database: "Database",
  infra: "Infra/DevOps",
  test_data: "Test data",
  third_party: "Third-party",
  unknown: "Unknown",
};

export function RootCauseCard({ analysis }: { analysis: RootCauseAnalysis }) {
  return (
    <div className="rounded-lg border border-destructive/20 bg-destructive/[0.04] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-sm font-medium">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          Root cause analysis
        </p>
        <div className="flex items-center gap-2">
          {analysis.severity && (
            <Badge variant={SEVERITY_VARIANT[analysis.severity] ?? "outline"} className="capitalize">
              {analysis.severity}
            </Badge>
          )}
          <span className="text-xs text-muted-foreground">{formatConfidence(analysis.confidence)} confidence</span>
        </div>
      </div>

      <p className="mb-4 text-sm font-medium leading-relaxed">{analysis.root_cause}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Observed</p>
          <p className="text-sm leading-relaxed text-foreground/90">{analysis.observed_behavior}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Expected</p>
          <p className="text-sm leading-relaxed text-foreground/90">{analysis.expected_behavior}</p>
        </div>
      </div>

      {analysis.evidence.length > 0 && (
        <div className="mt-4">
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Eye className="h-3.5 w-3.5" />
            Evidence
          </p>
          <ul className="space-y-1">
            {analysis.evidence.map((item, idx) => (
              <li key={idx} className="text-sm leading-relaxed text-foreground/90">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Wrench className="h-3.5 w-3.5" />
            Suggested fix
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">{analysis.suggested_fix}</p>
        </div>
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <Target className="h-3.5 w-3.5" />
            Affected component
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">
            {COMPONENT_LABEL[analysis.affected_component] ?? analysis.affected_component}
          </p>
        </div>
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <User className="h-3.5 w-3.5" />
            Likely owner
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">{analysis.likely_owner}</p>
        </div>
      </div>
    </div>
  );
}
