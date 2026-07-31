"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { KeyRound, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { NewCredentialDialog } from "@/components/new-credential-dialog";
import { useCredentials, useDeleteCredential } from "@/lib/queries";
import type { CredentialOut } from "@/lib/types";

const FIELD_LABELS: { key: keyof CredentialOut; label: string }[] = [
  { key: "has_username", label: "Username" },
  { key: "has_password", label: "Password" },
  { key: "has_api_token", label: "API token" },
  { key: "has_bearer_token", label: "Bearer token" },
  { key: "has_cookies", label: "Cookies" },
  { key: "has_headers", label: "Headers" },
];

export default function CredentialsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { data: credentials, isLoading } = useCredentials(projectId);
  const deleteCredential = useDeleteCredential(projectId);
  const [open, setOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<CredentialOut | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Credentials"
        description="Encrypted credential profiles Stryker can use to authenticate as a real user during a run. Secrets are never shown again once saved."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" />
            New credential
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : !credentials || credentials.length === 0 ? (
        <EmptyState
          icon={KeyRound}
          title="No credential profiles yet"
          description="Create one if your requirements need Stryker to log in as a specific user."
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" />
              New credential
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {credentials.map((credential) => (
            <Card key={credential.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium">{credential.label}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {FIELD_LABELS.filter((f) => credential[f.key]).map((f) => (
                      <Badge key={f.key} variant="secondary" className="text-[11px]">
                        {f.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setPendingDelete(credential)}>
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <NewCredentialDialog projectId={projectId} open={open} onOpenChange={setOpen} />

      <Dialog open={!!pendingDelete} onOpenChange={(o) => !o && setPendingDelete(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete &quot;{pendingDelete?.label}&quot;?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Any requirement using this credential profile will run unauthenticated afterward.
          </p>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (pendingDelete) deleteCredential.mutate(pendingDelete.id);
                setPendingDelete(null);
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
