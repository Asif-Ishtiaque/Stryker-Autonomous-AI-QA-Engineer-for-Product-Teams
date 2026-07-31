"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { BookOpen, Loader2, Search, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/status-badge";
import { KnowledgeUpload } from "@/components/knowledge-upload";
import { useDeleteKnowledge, useKnowledgeSearch, useKnowledgeSources } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { SemanticSearchResult } from "@/lib/types";

export default function KnowledgePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { data: sources, isLoading } = useKnowledgeSources(projectId);
  const deleteSource = useDeleteKnowledge(projectId);
  const search = useKnowledgeSearch(projectId);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SemanticSearchResult[] | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const data = await search.mutateAsync({ query: query.trim(), top_k: 8 });
      setResults(data);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Search failed.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge"
        description="Upload docs, specs, and screenshots so Stryker's AI understands your product before it tests it."
      />

      <KnowledgeUpload projectId={projectId} />

      <Card>
        <CardContent className="p-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Semantic search — e.g. 'how does refund eligibility work?'"
              className="flex-1"
            />
            <Button type="submit" disabled={search.isPending || !query.trim()}>
              {search.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </Button>
          </form>

          {results && (
            <div className="mt-4 space-y-3">
              {results.length === 0 ? (
                <p className="text-sm text-muted-foreground">No matches found.</p>
              ) : (
                results.map((result, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="rounded-lg border border-border p-3"
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">{result.source_filename}</span>
                      <span className="text-xs text-muted-foreground">{(result.score * 100).toFixed(0)}% match</span>
                    </div>
                    <p className="text-sm leading-relaxed">{result.chunk_text}</p>
                  </motion.div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : !sources || sources.length === 0 ? (
        <EmptyState icon={BookOpen} title="No knowledge sources yet" description="Uploaded files will appear here once indexing starts." />
      ) : (
        <div className="space-y-2">
          {sources.map((source) => (
            <div key={source.id} className="flex items-center justify-between rounded-lg border border-border p-3">
              <div className="flex items-center gap-3">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{source.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {source.source_type} · {source.chunk_count} chunk{source.chunk_count === 1 ? "" : "s"}
                    {source.error_message ? ` · ${source.error_message}` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={source.status} />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => deleteSource.mutate(source.id)}
                  disabled={deleteSource.isPending}
                >
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
