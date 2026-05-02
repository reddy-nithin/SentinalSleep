"use client";

import { useState } from "react";
import { stateColors, stateLabels } from "@/lib/colors";
import { formatSeconds, formatDuration } from "@/lib/time";
import { cn } from "@/lib/cn";
import type { Segment } from "@/lib/segments";

interface StateRibbonProps {
  segments: Segment[];
  totalDuration: number;
  progress?: number;
  className?: string;
}

export function StateRibbon({ segments, totalDuration, progress = 1, className }: StateRibbonProps) {
  const [tooltip, setTooltip] = useState<{ text: string; x: number } | null>(null);
  const clippedDuration = totalDuration * progress;

  const visible = segments
    .filter((s) => s.startT < clippedDuration)
    .map((s) => ({ ...s, endT: Math.min(s.endT, clippedDuration) }));

  return (
    <div className={cn("space-y-3", className)}>
      {/* Bar */}
      <div className="relative h-10 flex rounded-lg overflow-hidden">
        {visible.map((seg, i) => {
          const width = ((seg.endT - seg.startT) / totalDuration) * 100;
          const color = stateColors[seg.state] ?? "#8B98A5";
          return (
            <div
              key={i}
              style={{ width: `${width}%`, background: color }}
              className="h-full cursor-pointer transition-opacity hover:opacity-90"
              onMouseEnter={(e) => {
                const rect = e.currentTarget.closest(".relative")!.getBoundingClientRect();
                const x = e.clientX - rect.left;
                setTooltip({
                  text: `${stateLabels[seg.state] ?? seg.state}\n${formatSeconds(seg.startT)} → ${formatSeconds(seg.endT)}`,
                  x,
                });
              }}
              onMouseLeave={() => setTooltip(null)}
            />
          );
        })}

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute bottom-12 pointer-events-none z-50 bg-surface-alt border border-border rounded-lg px-3 py-2 text-xs font-mono text-text whitespace-pre"
            style={{ left: Math.min(tooltip.x - 60, 300) }}
          >
            {tooltip.text}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {segments.map((seg) => {
          const duration = seg.endT - seg.startT;
          const color = stateColors[seg.state] ?? "#8B98A5";
          return (
            <div key={seg.state} className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                <span className="text-[0.65rem] font-semibold uppercase tracking-wider text-text-dim">
                  {stateLabels[seg.state] ?? seg.state}
                </span>
              </div>
              <span className="font-mono text-xs pl-3.5 text-text">{formatDuration(duration)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
