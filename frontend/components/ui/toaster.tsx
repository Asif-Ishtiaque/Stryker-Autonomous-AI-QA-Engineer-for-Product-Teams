"use client";

import * as React from "react";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      position="bottom-right"
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "group toast bg-card text-card-foreground border border-border shadow-lg rounded-lg",
          description: "text-muted-foreground",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-muted text-muted-foreground",
          closeButton: "bg-card border-border text-muted-foreground",
          title: "text-card-foreground font-medium",
          success: "!bg-success !text-success-foreground !border-success/20",
          error: "!bg-destructive !text-destructive-foreground !border-destructive/20",
          warning: "!bg-warning !text-warning-foreground !border-warning/20",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
