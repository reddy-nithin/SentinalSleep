"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";

interface Night {
  date: string;
  score: number | null;
}

interface RecoveryHeatmapProps {
  nights: Night[];
  className?: string;
}

const DOW = ["S", "M", "T", "W", "T", "F", "S"];

function cellStyle(score: number | null): string {
  if (score === null) return "bg-surface-alt border-border text-text-dim";
  if (score >= 70) return "bg-mint/15 border-mint/30 text-mint";
  if (score >= 50) return "bg-amber/15 border-amber/30 text-amber";
  return "bg-danger/15 border-danger/30 text-danger";
}

export function RecoveryHeatmap({ nights, className }: RecoveryHeatmapProps) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  // Pad to start on Sunday
  const firstDate = nights.length > 0 ? new Date(nights[0].date) : new Date();
  const startDow = firstDate.getDay();
  const padded: (Night | null)[] = [
    ...Array(startDow).fill(null),
    ...nights,
  ];

  return (
    <div className={cn("overflow-x-auto", className)}>
      <div className="inline-grid gap-2" style={{ gridTemplateColumns: "repeat(7, 36px)" }}>
        {DOW.map((d, i) => (
          <div key={i} className="text-center text-[0.65rem] font-bold text-text-dim py-1">
            {d}
          </div>
        ))}
        {padded.map((night, i) =>
          night === null ? (
            <div key={i} className="w-9 h-9 rounded-md bg-surface-alt border border-border" />
          ) : (
            <div
              key={i}
              className={cn(
                "w-9 h-9 flex items-center justify-center rounded-md border cursor-default transition-transform hover:scale-110",
                cellStyle(night.score)
              )}
              onMouseEnter={() =>
                setTooltip(night.date + (night.score !== null ? `\nScore: ${night.score}` : ""))
              }
              onMouseLeave={() => setTooltip(null)}
              title={tooltip ?? undefined}
            >
              {night.score !== null && (
                <span className="font-mono text-[0.55rem] font-semibold">{night.score}</span>
              )}
            </div>
          )
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-5 mt-4 justify-end">
        {[
          { label: "Optimal", cls: "bg-mint/20 border-mint/40" },
          { label: "Fair", cls: "bg-amber/20 border-amber/40" },
          { label: "Strained", cls: "bg-danger/20 border-danger/40" },
        ].map(({ label, cls }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={cn("w-3 h-3 rounded border", cls)} />
            <span className="text-[0.62rem] text-text-dim">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
