"use client";

import { motion, useReducedMotion } from "framer-motion";
import { stateColors, stateLabels } from "@/lib/colors";

type StateKey = "listening" | "flagged" | "intervening";

const EASE: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

const KEYS: StateKey[] = ["listening", "flagged", "intervening"];

interface StateBreakdownProps {
  dates: string[];
  minutes: Record<StateKey, number[]>;
  height?: number;
}

export function StateBreakdown({ dates, minutes, height = 120 }: StateBreakdownProps) {
  const shouldReduceMotion = useReducedMotion();
  const totals = dates.map((_, i) =>
    KEYS.reduce((sum, k) => sum + (minutes[k]?.[i] ?? 0), 0)
  );
  const maxTotal = Math.max(...totals, 1);

  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-4">
        {KEYS.map((k) => (
          <div key={k} className="flex items-center gap-1.5">
            <div
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ background: stateColors[k] }}
            />
            <span className="text-xs text-text-dim">{stateLabels[k]}</span>
          </div>
        ))}
      </div>

      <div className="flex items-end gap-0.5" style={{ height }}>
        {dates.map((date, i) => {
          const total = totals[i];
          const heightPct = maxTotal > 0 ? (total / maxTotal) * 100 : 0;
          return (
            <motion.div
              key={date}
              className="flex-1 flex flex-col-reverse overflow-hidden rounded-t-[2px]"
              style={{ height: `${heightPct}%`, transformOrigin: "bottom" }}
              initial={shouldReduceMotion ? false : { scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{
                duration: 0.45,
                delay: i * 0.04,
                ease: EASE,
              }}
            >
              {KEYS.map((k) => {
                const val = minutes[k]?.[i] ?? 0;
                const pct = total > 0 ? (val / total) * 100 : 0;
                return (
                  <div
                    key={k}
                    title={`${stateLabels[k]}: ${val} min`}
                    className="w-full flex-shrink-0"
                    style={{ height: `${pct}%`, background: stateColors[k] }}
                  />
                );
              })}
            </motion.div>
          );
        })}
      </div>

      <div className="flex justify-between mt-1.5 font-mono text-[10px] text-text-dim">
        <span>{dates[0]?.slice(5)}</span>
        <span>{dates[Math.floor(dates.length / 2)]?.slice(5)}</span>
        <span>{dates[dates.length - 1]?.slice(5)}</span>
      </div>
    </div>
  );
}
