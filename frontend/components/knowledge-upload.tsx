"use client";

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { Loader2, UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUploadKnowledge } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

const ACCEPTED_EXTENSIONS = [".md", ".markdown", ".pdf", ".docx", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".sql", ".json", ".yaml", ".yml"];

export function KnowledgeUpload({ projectId }: { projectId: string }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadKnowledge(projectId);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      for (const file of Array.from(files)) {
        try {
          await upload.mutateAsync(file);
          toast.success(`${file.name} uploaded — indexing in the background`);
        } catch (err) {
          toast.error(err instanceof ApiError ? `${file.name}: ${err.message}` : `Failed to upload ${file.name}`);
        }
      }
    },
    [upload],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border py-10 text-center transition-colors",
        isDragging ? "border-primary bg-primary/5" : "hover:border-primary/40 hover:bg-secondary/20",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_EXTENSIONS.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {upload.isPending ? (
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      ) : (
        <UploadCloud className="h-6 w-6 text-muted-foreground" />
      )}
      <p className="text-sm font-medium">Drag files here, or click to browse</p>
      <p className="text-xs text-muted-foreground">Markdown, PDF, Word, CSV, images, SQL, OpenAPI/Swagger specs</p>
    </div>
  );
}
