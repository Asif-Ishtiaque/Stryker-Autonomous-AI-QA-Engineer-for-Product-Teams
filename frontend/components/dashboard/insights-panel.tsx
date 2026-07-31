import { AlertCircle, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardData } from "@/lib/dashboard-data";

/**
 * Simple client-side derived observations — NOT a model call. These are
 * plainly-labeled statistics computed from data already on screen, not an
 * AI-generated summary.
 */
export function InsightsPanel({ data }: { data: DashboardData }) {
  const insights: { icon: React.ComponentType<{ className?: string }>; text: string }[] = [];

  if (data.passRate != null) {
    if (data.passRate < 0.5) {
      insights.push({
        icon: TrendingDown,
        text: `Overall pass rate is ${Math.round(data.passRate * 100)}% — below half of finished runs are passing.`,
      });
    } else if (data.passRate > 0.9) {
      insights.push({ icon: TrendingUp, text: `Pass rate is strong at ${Math.round(data.passRate * 100)}% across finished runs.` });
    }
  }

  if (data.topFailingRequirements.length > 0) {
    const top = data.topFailingRequirements[0];
    insights.push({
      icon: AlertCircle,
      text: `"${top.text.slice(0, 80)}${top.text.length > 80 ? "…" : ""}" in ${top.projectName} has failed ${top.failureCount} time${top.failureCount === 1 ? "" : "s"} — worth a look.`,
    });
  }

  if (data.totalRunsLast8Weeks === 0 && data.totalProjects > 0) {
    insights.push({ icon: AlertCircle, text: "No runs have executed in the last 8 weeks. Kick off a run to start building history." });
  }

  if (data.totalProjects === 0) {
    insights.push({ icon: Sparkles, text: "Create your first project to start describing requirements in plain English." });
  }

  if (insights.length === 0) {
    insights.push({ icon: Sparkles, text: "Everything looks steady — no notable shifts in pass rate or failures right now." });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Sparkles className="h-4 w-4 text-primary" />
          Insights
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {insights.map((insight, idx) => {
          const Icon = insight.icon;
          return (
            <div key={idx} className="flex items-start gap-2.5 text-sm">
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <p className="text-foreground/90">{insight.text}</p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
