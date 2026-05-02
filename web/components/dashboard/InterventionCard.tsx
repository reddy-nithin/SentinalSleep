"use client";

import { useRef } from "react";
import { Play, Pause, Music } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { formatInterventionCard } from "@/lib/time";

interface InterventionCardProps {
  startedAt: string;
  preDss: number;
  postDss: number | null;
  effective: boolean | null;
  clipName: string | null;
  audioUrl?: string;
  className?: string;
}

export function InterventionCard({
  startedAt,
  preDss,
  postDss,
  effective,
  clipName,
  audioUrl,
  className,
}: InterventionCardProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const delta = postDss !== null ? postDss - preDss : null;
  const improved = delta !== null && delta < 0;

  function togglePlay() {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      audioRef.current.play();
      setPlaying(true);
    }
  }

  return (
    <div className={cn("ss-card p-5 flex flex-col gap-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs text-text-dim">{formatInterventionCard(startedAt)}</span>
        {effective === true && <span className="ss-pill ss-pill-green">Effective</span>}
        {effective === false && <span className="ss-pill ss-pill-red">Ineffective</span>}
        {effective === null && <span className="ss-pill ss-pill-dim">Pending</span>}
      </div>

      {/* DSS delta */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm font-semibold text-danger">{preDss.toFixed(2)}</span>
        <span className={cn("text-lg font-bold", improved ? "text-mint" : "text-danger")}>
          {improved ? "↘" : "→"}
        </span>
        {postDss !== null ? (
          <span className={cn("font-mono text-sm font-semibold", improved ? "text-mint" : "text-danger")}>
            {postDss.toFixed(2)}
          </span>
        ) : (
          <span className="font-mono text-sm text-text-dim">—</span>
        )}
        {delta !== null && (
          <span className={cn("ss-pill text-[11px] ml-auto", improved ? "ss-pill-green" : "ss-pill-red")}>
            {improved ? "" : "+"}
            {delta.toFixed(2)} DSS
          </span>
        )}
      </div>

      {/* Clip + player */}
      {clipName && (
        <div className="flex items-center gap-3 bg-surface-alt rounded-lg px-3 py-2">
          <Music className="w-4 h-4 text-text-dim flex-shrink-0" />
          <span className="font-mono text-xs text-text-dim truncate flex-1">{clipName}</span>
          {audioUrl ? (
            <button
              onClick={togglePlay}
              className="flex-shrink-0 w-7 h-7 rounded-full bg-mint/15 hover:bg-mint/25 flex items-center justify-center text-mint transition-colors"
            >
              {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
          ) : null}
          {audioUrl && (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => setPlaying(false)}
              className="hidden"
            />
          )}
        </div>
      )}
    </div>
  );
}
