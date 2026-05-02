"use client";

import { useRef, useState } from "react";
import { Play, Pause, Music } from "lucide-react";
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

function dssLevel(score: number): { label: string; colorClass: string } {
  if (score <= 0.3) return { label: "Calm", colorClass: "text-mint" };
  if (score <= 0.55) return { label: "Mild", colorClass: "text-amber" };
  return { label: "Severe", colorClass: "text-danger" };
}

function DssScaleBar({ pre, post }: { pre: number; post: number | null }) {
  const pctPre = Math.round(pre * 100);
  const pctPost = post !== null ? Math.round(post * 100) : null;
  return (
    <div className="space-y-1.5">
      <div className="relative h-2.5 rounded-full overflow-hidden flex">
        <div className="flex-1 bg-mint/30" />
        <div className="flex-1 bg-amber/30" />
        <div className="flex-[1.8] bg-danger/30" />
        {/* After marker */}
        {pctPost !== null && (
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-mint rounded-full shadow-[0_0_4px_1px_rgba(0,229,160,0.5)]"
            style={{ left: `${pctPost}%` }}
          />
        )}
        {/* Before marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-danger rounded-full shadow-[0_0_4px_1px_rgba(255,77,109,0.5)]"
          style={{ left: `${pctPre}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-text-dim font-mono">
        <span>0.0 Calm</span>
        <span className="text-amber">0.4 Flagged</span>
        <span className="text-danger">0.7 Severe</span>
        <span>1.0</span>
      </div>
    </div>
  );
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
  const [audioError, setAudioError] = useState(false);

  const delta = postDss !== null ? postDss - preDss : null;
  const improved = delta !== null && delta < 0;
  const preLvl = dssLevel(preDss);
  const postLvl = postDss !== null ? dssLevel(postDss) : null;

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

      {/* DSS scale bar */}
      <DssScaleBar pre={preDss} post={postDss} />

      {/* DSS numbers */}
      <div className="flex items-center gap-3">
        <div className="text-center">
          <div className="font-mono text-sm font-semibold text-danger">{preDss.toFixed(2)}</div>
          <div className={cn("text-[10px] font-medium mt-0.5", preLvl.colorClass)}>{preLvl.label}</div>
        </div>
        <span className={cn("text-lg font-bold flex-1 text-center", improved ? "text-mint" : "text-danger")}>
          {improved ? "↘" : "→"}
        </span>
        {postDss !== null && postLvl ? (
          <div className="text-center">
            <div className={cn("font-mono text-sm font-semibold", improved ? "text-mint" : "text-danger")}>
              {postDss.toFixed(2)}
            </div>
            <div className={cn("text-[10px] font-medium mt-0.5", postLvl.colorClass)}>{postLvl.label}</div>
          </div>
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
          {audioUrl && !audioError && (
            <button
              onClick={togglePlay}
              className="flex-shrink-0 w-7 h-7 rounded-full bg-mint/15 hover:bg-mint/25 flex items-center justify-center text-mint transition-colors"
            >
              {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
          )}
          {audioUrl && audioError && (
            <span className="text-[10px] text-text-dim">No audio</span>
          )}
          {audioUrl && (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => setPlaying(false)}
              onError={() => setAudioError(true)}
              className="hidden"
            />
          )}
        </div>
      )}
    </div>
  );
}
