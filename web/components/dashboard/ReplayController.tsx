"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
import { cn } from "@/lib/cn";

interface ReplayControllerProps {
  onProgress: (progress: number) => void;
  duration?: number;
  className?: string;
}

export function ReplayController({
  onProgress,
  duration = 20,
  className,
}: ReplayControllerProps) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (playing) {
      const startOffset = progress * duration * 1000;
      startRef.current = Date.now() - startOffset;

      const tick = () => {
        const elapsed = Date.now() - startRef.current!;
        const p = Math.min(elapsed / (duration * 1000), 1);
        setProgress(p);
        onProgress(p);
        if (p < 1) {
          rafRef.current = requestAnimationFrame(tick);
        } else {
          setPlaying(false);
        }
      };
      rafRef.current = requestAnimationFrame(tick);
    } else {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    }
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [playing]);

  function reset() {
    setPlaying(false);
    setProgress(0);
    onProgress(0);
  }

  const pct = Math.round(progress * 100);

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <button
        onClick={() => setPlaying((p) => !p)}
        className="flex items-center gap-2 px-4 py-2 rounded-full bg-mint/15 hover:bg-mint/25 text-mint text-sm font-semibold transition-colors"
      >
        {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        {playing ? "Pause" : progress > 0 ? "Resume" : "Replay Night"}
      </button>

      {progress > 0 && (
        <button
          onClick={reset}
          className="p-2 rounded-full bg-surface-alt hover:bg-border text-text-dim hover:text-text transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Progress bar */}
      <div className="flex-1 h-1.5 bg-surface-alt rounded-full overflow-hidden">
        <div
          className="h-full bg-mint rounded-full transition-none"
          style={{ width: `${pct}%` }}
        />
      </div>

      <span className="font-mono text-xs text-text-dim w-8 text-right">{pct}%</span>
    </div>
  );
}
