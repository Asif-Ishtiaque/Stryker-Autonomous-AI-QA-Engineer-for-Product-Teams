"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { ChatSheet } from "./chat-sheet";

interface ChatContextValue {
  isOpen: boolean;
  projectId: string | null;
  openChat: (projectId: string) => void;
  closeChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);

  const value = useMemo<ChatContextValue>(
    () => ({
      isOpen,
      projectId,
      openChat: (id: string) => {
        setProjectId(id);
        setIsOpen(true);
      },
      closeChat: () => setIsOpen(false),
    }),
    [isOpen, projectId],
  );

  return (
    <ChatContext.Provider value={value}>
      {children}
      <ChatSheet
        open={isOpen}
        projectId={projectId}
        onOpenChange={(open) => setIsOpen(open)}
      />
    </ChatContext.Provider>
  );
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within a ChatProvider");
  return ctx;
}
