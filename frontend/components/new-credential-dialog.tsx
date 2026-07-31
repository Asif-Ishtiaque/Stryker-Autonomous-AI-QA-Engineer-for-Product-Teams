"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateCredential } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

export function NewCredentialDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createCredential = useCreateCredential(projectId);
  const [label, setLabel] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [bearerToken, setBearerToken] = useState("");
  const [cookiesJson, setCookiesJson] = useState("");
  const [headersJson, setHeadersJson] = useState("");

  function reset() {
    setLabel("");
    setUsername("");
    setPassword("");
    setApiToken("");
    setBearerToken("");
    setCookiesJson("");
    setHeadersJson("");
  }

  function parseJsonObject(raw: string, fieldName: string): Record<string, string> | undefined {
    if (!raw.trim()) return undefined;
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("must be a JSON object");
      }
      return parsed as Record<string, string>;
    } catch {
      throw new Error(`${fieldName} must be valid JSON, e.g. {"key": "value"}`);
    }
  }

  async function handleSubmit() {
    if (!label.trim()) {
      toast.error("Give this credential profile a label.");
      return;
    }
    let cookies: Record<string, string> | undefined;
    let headers: Record<string, string> | undefined;
    try {
      cookies = parseJsonObject(cookiesJson, "Cookies");
      headers = parseJsonObject(headersJson, "Headers");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Invalid JSON.");
      return;
    }

    try {
      await createCredential.mutateAsync({
        label: label.trim(),
        username: username.trim() || undefined,
        password: password || undefined,
        api_token: apiToken.trim() || undefined,
        bearer_token: bearerToken.trim() || undefined,
        cookies,
        headers,
      });
      toast.success("Credential profile created");
      reset();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to create credential profile.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New credential profile</DialogTitle>
          <DialogDescription>
            Stored encrypted. Stryker never returns decrypted secrets back to the UI once saved.
          </DialogDescription>
        </DialogHeader>

        <div className="grid max-h-[60vh] gap-4 overflow-y-auto py-2 pr-1">
          <div className="grid gap-1.5">
            <Label htmlFor="cred-label">Label</Label>
            <Input id="cred-label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Admin account" autoFocus />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="cred-username">Username</Label>
              <Input id="cred-username" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="cred-password">Password</Label>
              <Input id="cred-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="cred-api-token">API token</Label>
              <Input id="cred-api-token" type="password" value={apiToken} onChange={(e) => setApiToken(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="cred-bearer-token">Bearer token</Label>
              <Input id="cred-bearer-token" type="password" value={bearerToken} onChange={(e) => setBearerToken(e.target.value)} />
            </div>
          </div>

          <details className="group rounded-md border border-border p-3">
            <summary className="cursor-pointer text-sm font-medium text-muted-foreground">Advanced: cookies &amp; headers (JSON)</summary>
            <div className="mt-3 grid gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="cred-cookies">Cookies</Label>
                <Textarea
                  id="cred-cookies"
                  value={cookiesJson}
                  onChange={(e) => setCookiesJson(e.target.value)}
                  placeholder='{"session_id": "abc123"}'
                  className="min-h-[70px] font-mono text-xs"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cred-headers">Headers</Label>
                <Textarea
                  id="cred-headers"
                  value={headersJson}
                  onChange={(e) => setHeadersJson(e.target.value)}
                  placeholder='{"X-Tenant-Id": "42"}'
                  className="min-h-[70px] font-mono text-xs"
                />
              </div>
            </div>
          </details>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createCredential.isPending}>
            {createCredential.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save profile
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
