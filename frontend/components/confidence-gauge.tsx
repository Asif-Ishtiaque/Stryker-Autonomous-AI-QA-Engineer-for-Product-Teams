"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function ConfidenceGauge({ score, size = 88 }: { score: number | null | undefined; size?: number }) {
  const radius = size / 2 - 6;
  const circumference = 2 * Math.PI * radius;
  const pct = score != null ? Math.max(0, Math.min(1, score)) : 0;
  const offset = circumference * (1 - pct);

  const color = score == null ? "hsl(var(--muted-foreground))" : pct >= 0.75 ? "hsl(var(--success))" : pct >= 0.5 ? "hsl(var(--warning))" : "hsl(var(--destructive))";

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="hsl(var(--border))" strokeWidth={6} fill="none" />
        {score != null && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={6}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        )}
      </svg>
      <div className={cn("absolute flex flex-col items-center")}>
        <span className="text-lg font-semibold">{score != null ? `${Math.round(pct * 100)}%` : "—"}</span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">confidence</span>
      </div>
    </div>
  );
}
