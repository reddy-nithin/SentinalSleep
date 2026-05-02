"use client";

import { useEffect, useRef } from "react";
import { animate } from "framer-motion";
import { cn } from "@/lib/cn";

interface KpiTileProps {
  value: number | string;
  label: string;
  accentClass?: string;
  delta?: { text: string; positive: boolean };
  suffix?: string;
  animate?: boolean;
  className?: string;
}

export function KpiTile({
  value,
  label,
  accentClass = "text-text",
  delta,
  suffix = "",
  animate: shouldAnimate = true,
  className,
}: KpiTileProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!shouldAnimate || typeof value !== "number") return;
    const ctrl = animate(0, value, {
      duration: 1.2,
      ease: [0.65, 0, 0.35, 1],
      onUpdate: (v) => {
        if (ref.current) {
          ref.current.textContent =
            String(Math.round(v)) + suffix;
        }
      },
    });
    return ctrl.stop;
  }, [value, suffix, shouldAnimate]);

  return (
    <div className={cn("ss-card p-6 flex flex-col justify-between gap-4", className)}>
      <span className="ss-kpi-label">{label}</span>
      <div className="flex items-end justify-between gap-2">
        <span ref={ref} className={cn("ss-kpi-number", accentClass)}>
          {typeof value === "number" ? (shouldAnimate ? "0" + suffix : value + suffix) : value}
        </span>
        {delta && (
          <span
            className={cn(
              "ss-pill mb-1 text-[10px]",
              delta.positive ? "ss-pill-green" : "ss-pill-red"
            )}
          >
            {delta.positive ? "↑" : "↓"} {delta.text}
          </span>
        )}
      </div>
    </div>
  );
}
