"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, CornerDownLeft, FileText, PlayCircle, Sparkles, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSendChatMessage } from "@/lib/queries";
import type { ChatSource } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

export function ChatSheet({
  open,
  projectId,
  onOpenChange,
}: {
  open: boolean;
  projectId: string | null;
  onOpenChange: (open: boolean) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const sendMessage = useSendChatMessage();

  async function handleSend() {
    const text = input.trim();
    if (!text || !projectId || sendMessage.isPending) return;

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await sendMessage.mutateAsync({
        project_id: projectId,
        message: text,
        conversation_id: conversationId,
      });
      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        { id: response.conversation_id + "-" + prev.length, role: "assistant", content: response.answer, sources: response.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: err instanceof Error ? `Something went wrong: ${err.message}` : "Something went wrong answering that.",
        },
      ]);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b border-border px-5 py-4">
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Ask Stryker
          </SheetTitle>
          <SheetDescription>
            Grounded in this project&apos;s knowledge base and past run history.
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 px-5">
          <div className="flex flex-col gap-4 py-4">
            {messages.length === 0 && (
              <div className="mt-10 flex flex-col items-center gap-2 text-center text-sm text-muted-foreground">
                <Bot className="h-8 w-8 text-muted-foreground/60" />
                <p>Ask about why a run failed, what a requirement covers, or anything in your knowledge base.</p>
              </div>
            )}
            <AnimatePresence initial={false}>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn("flex gap-2.5", message.role === "user" && "flex-row-reverse")}
                >
                  <div
                    className={cn(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                      message.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground",
                    )}
                  >
                    {message.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                  </div>
                  <div
                    className={cn(
                      "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                      message.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground",
                    )}
                  >
                    <div className="prose prose-sm prose-invert max-w-none [&_p]:my-1.5 [&_pre]:bg-black/30 [&_pre]:p-2 [&_pre]:rounded-md">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2.5 border-t border-white/10 pt-2">
                        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Sources</p>
                        <ul className="space-y-1">
                          {message.sources.map((source, idx) => (
                            <li key={idx} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                              {source.kind === "run" ? (
                                <PlayCircle className="mt-0.5 h-3 w-3 shrink-0" />
                              ) : (
                                <FileText className="mt-0.5 h-3 w-3 shrink-0" />
                              )}
                              <span className="line-clamp-2">{source.snippet}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            {sendMessage.isPending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Bot className="h-3.5 w-3.5 animate-pulse" /> Thinking…
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t border-border p-3">
          <div className="flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask about a failing requirement, a past run, or your knowledge base…"
              className="min-h-[44px] flex-1 resize-none"
              disabled={!projectId}
            />
            <Button size="icon" onClick={handleSend} disabled={!input.trim() || !projectId || sendMessage.isPending}>
              <CornerDownLeft className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
