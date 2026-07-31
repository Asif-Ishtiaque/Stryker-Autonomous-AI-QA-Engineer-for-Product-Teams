"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Download, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useGenerateReports, useReports } from "@/lib/queries";
import { reportsApi, ApiError } from "@/lib/api-client";
import { ReportFormat } from "@/lib/types";

const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: "Markdown",
  json: "JSON",
  pdf: "PDF",
  jira: "Jira ticket",
};

export function ReportMenu({ projectId, runId }: { projectId: string; runId: string }) {
  const { data: reports } = useReports(projectId, runId);
  const generateReports = useGenerateReports(projectId, runId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selected, setSelected] = useState<ReportFormat[]>([ReportFormat.MARKDOWN]);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  function toggleFormat(format: ReportFormat) {
    setSelected((prev) => (prev.includes(format) ? prev.filter((f) => f !== format) : [...prev, format]));
  }

  async function handleGenerate() {
    if (selected.length === 0) {
      toast.error("Pick at least one format.");
      return;
    }
    try {
      await generateReports.mutateAsync({ formats: selected });
      toast.success("Report generated");
      setDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to generate report.");
    }
  }

  async function handleDownload(reportId: string) {
    setDownloadingId(reportId);
    try {
      const { url } = await reportsApi.url(projectId, runId, reportId);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to get download link.");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            <FileText className="h-3.5 w-3.5" />
            Reports
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onSelect={() => setDialogOpen(true)}>Generate report…</DropdownMenuItem>
          {reports && reports.length > 0 && (
            <>
              <DropdownMenuSeparator />
              {reports.map((report) => (
                <DropdownMenuItem key={report.id} onSelect={() => handleDownload(report.id)} disabled={downloadingId === report.id}>
                  {downloadingId === report.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                  Download {FORMAT_LABELS[report.format]}
                </DropdownMenuItem>
              ))}
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Generate report</DialogTitle>
            <DialogDescription>Choose which formats to export for this run.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            {Object.values(ReportFormat).map((format) => (
              <label key={format} className="flex items-center gap-2.5 rounded-md border border-border p-2.5 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(format)}
                  onChange={() => toggleFormat(format)}
                  className="h-4 w-4 accent-primary"
                />
                {FORMAT_LABELS[format]}
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleGenerate} disabled={generateReports.isPending}>
              {generateReports.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
