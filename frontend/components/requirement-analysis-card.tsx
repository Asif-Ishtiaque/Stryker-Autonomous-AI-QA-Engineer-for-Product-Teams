import { AlertTriangle, CheckCircle2, Lightbulb, ShieldQuestion, Sparkles } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { formatConfidence } from "@/lib/utils";
import type { RequirementAnalysis } from "@/lib/types";

function AnalysisList({
  icon: Icon,
  label,
  items,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  items: string[];
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </p>
      <ul className="space-y-1">
        {items.map((item, idx) => (
          <li key={idx} className="text-sm leading-relaxed text-foreground/90">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RequirementAnalysisCard({ analysis }: { analysis: RequirementAnalysis }) {
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/[0.04] p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="flex items-center gap-1.5 text-sm font-medium">
          <Sparkles className="h-4 w-4 text-primary" />
          Stryker&apos;s understanding
        </p>
        <span className="text-xs text-muted-foreground">{formatConfidence(analysis.confidence)} confidence</span>
      </div>

      <p className="mb-4 text-sm leading-relaxed">{analysis.understood_intent}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <AnalysisList icon={CheckCircle2} label="Expected outcomes" items={analysis.expected_outcomes} />
        <AnalysisList icon={ShieldQuestion} label="Inferred validations" items={analysis.inferred_validations} />
      </div>

      {(analysis.identified_risks.length > 0 || analysis.predicted_edge_cases.length > 0) && (
        <>
          <Separator className="my-4" />
          <div className="grid gap-4 sm:grid-cols-2">
            <AnalysisList icon={AlertTriangle} label="Identified risks" items={analysis.identified_risks} />
            <AnalysisList icon={Lightbulb} label="Predicted edge cases" items={analysis.predicted_edge_cases} />
          </div>
        </>
      )}
    </div>
  );
}
