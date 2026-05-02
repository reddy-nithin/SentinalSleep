"use client";

import { useEffect, useState } from "react";
import { DssWaveform } from "@/components/charts/DssWaveform";
import { StateRibbon } from "@/components/charts/StateRibbon";
import { buildSegments } from "@/lib/segments";
import { ReplayController } from "@/components/dashboard/ReplayController";
import { formatDate, formatDuration } from "@/lib/time";
import type { NightData } from "@/lib/data";

interface Props {
  params: { sessionId: string };
}

export default function NightDetailPage({ params }: Props) {
  const [data, setData] = useState<NightData | null>(null);
  const [progress, setProgress] = useState(1);
  const [showOverlays, setShowOverlays] = useState(false);

  useEffect(() => {
    fetch(`/api/night/${params.sessionId}`)
      .then((r) => r.json())
      .then(setData);
  }, [params.sessionId]);

  if (!data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-text-dim text-sm">Loading night data…</div>
      </div>
    );
  }

  const { session, timeseries, events, interventions } = data;

  const sessionStart = new Date(session.started_at).getTime();
  const sessionDuration = session.ended_at
    ? Math.round((new Date(session.ended_at).getTime() - sessionStart) / 1000)
    : 26400;

  const waveformData = timeseries.map((pt) => ({
    t: (new Date(pt.timestamp).getTime() - sessionStart) / 1000,
    dss: pt.dss,
    valence: pt.valence,
    arousal: pt.arousal,
    dominance: pt.dominance,
    state: pt.state,
  }));

  const markers = interventions.map((inv) => ({
    t: (new Date(inv.started_at).getTime() - sessionStart) / 1000,
  }));

  const segments = buildSegments(events, session.started_at);
  const totalDuration = segments.reduce((s, seg) => Math.max(s, seg.endT), 0) || sessionDuration;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Night Detail</h1>
          <p className="text-sm text-text-dim mt-1">
            {formatDate(session.started_at)} · {formatDuration(sessionDuration)} ·{" "}
            {interventions.length} intervention{interventions.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setShowOverlays((v) => !v)}
            className={`ss-pill cursor-pointer transition-colors ${showOverlays ? "ss-pill-info" : "ss-pill-dim"}`}
          >
            {showOverlays ? "Hide" : "Show"} Emotion Overlays
          </button>
        </div>
      </div>

      {/* Replay controller */}
      <div className="ss-card px-5 py-4">
        <ReplayController onProgress={setProgress} />
      </div>

      {/* DSS Waveform */}
      <div className="ss-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="ss-section-label">Distress Signal Score</h2>
          <div className="flex items-center gap-3 text-xs text-text-dim font-mono">
            <span className="flex items-center gap-1.5">
              <svg width="16" height="8"><path d="M0,4 L16,4" stroke="#FF4D6D" strokeWidth="2" /></svg>
              DSS
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="16" height="8"><line x1="0" y1="4" x2="16" y2="4" stroke="#FFB020" strokeWidth="1" strokeDasharray="4,2" /></svg>
              Threshold 0.4
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="12" height="10"><polygon points="6,0 0,10 12,10" fill="#00E5A0" /></svg>
              Intervention
            </span>
          </div>
        </div>
        <DssWaveform
          data={waveformData}
          interventions={markers}
          showOverlays={showOverlays}
          progress={progress}
          height={240}
        />
      </div>

      {/* State ribbon */}
      <div className="ss-card p-6">
        <h2 className="ss-section-label mb-4">Sleep Architecture</h2>
        <StateRibbon segments={segments} totalDuration={totalDuration} progress={progress} />
      </div>
    </div>
  );
}
