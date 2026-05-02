"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { DssWaveform } from "@/components/charts/DssWaveform";
import { StateRibbon } from "@/components/charts/StateRibbon";
import { buildSegments } from "@/lib/segments";
import { ReplayController } from "@/components/dashboard/ReplayController";
import { formatDate, formatDuration } from "@/lib/time";
import type { NightData } from "@/lib/data";

const EASE: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.38, delay: i * 0.07, ease: EASE },
  }),
};

const stateSwatches = [
  { label: "Listening", color: "#3D8B6E" },
  { label: "Flagged", color: "#FFB020" },
  { label: "Intervening", color: "#FF4D6D" },
  { label: "Resolved", color: "#A78BFA" },
  { label: "Awake", color: "#5AB1FF" },
];

export function NightDetailClient({ data }: { data: NightData }) {
  const [progress, setProgress] = useState(1);
  const [showOverlays, setShowOverlays] = useState(false);

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
    <div className="p-6 md:p-8 space-y-5 max-w-[1280px]">
      {/* Header */}
      <motion.div custom={0} initial="hidden" animate="visible" variants={fadeUp}>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-text-dim hover:text-text mb-3 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to overview
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Night Detail</h1>
            <p className="text-sm text-text-dim mt-1">
              {formatDate(session.started_at)} · {formatDuration(sessionDuration)} ·{" "}
              {interventions.length} intervention{interventions.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={() => setShowOverlays((v) => !v)}
            className={`ss-pill cursor-pointer transition-colors ${showOverlays ? "ss-pill-info" : "ss-pill-dim"}`}
          >
            {showOverlays ? "Hide" : "Show"} Emotion Overlays
          </button>
        </div>
      </motion.div>

      {/* Explainer */}
      <motion.div custom={1} initial="hidden" animate="visible" variants={fadeUp}
        className="ss-card p-4 flex gap-3 items-start">
        <div className="w-1.5 h-1.5 rounded-full bg-mint mt-[7px] flex-shrink-0" />
        <p className="text-xs text-text-dim leading-relaxed">
          <span className="text-text font-medium">What you're seeing:</span>{" "}
          The <span className="text-danger font-medium">DSS waveform</span> tracks distress in
          real time (0 = calm · 1 = peak distress). When DSS exceeds{" "}
          <span className="text-amber font-medium">0.4</span> and emotion analysis confirms a
          nightmare, SentinelSleep plays a pre-cached therapeutic audio cue.
          The <span className="text-violet font-medium">state ribbon</span> shows sleep
          architecture across the full night. Hit <span className="text-mint font-medium">Replay Night</span> to
          animate both charts simultaneously.
        </p>
      </motion.div>

      {/* Replay */}
      <motion.div custom={2} initial="hidden" animate="visible" variants={fadeUp}
        className="ss-card px-5 py-4">
        <ReplayController onProgress={setProgress} />
      </motion.div>

      {/* DSS Waveform */}
      <motion.div custom={3} initial="hidden" animate="visible" variants={fadeUp}
        className="ss-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="ss-section-label">Distress Signal Score</h2>
          <div className="flex items-center gap-3 text-xs text-text-dim font-mono flex-wrap">
            <span className="flex items-center gap-1.5">
              <svg width="16" height="8">
                <path d="M0,4 L16,4" stroke="#FF4D6D" strokeWidth="2" />
              </svg>
              DSS
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="16" height="8">
                <line x1="0" y1="4" x2="16" y2="4" stroke="#FFB020" strokeWidth="1" strokeDasharray="4,2" />
              </svg>
              Threshold 0.4
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="12" height="10">
                <polygon points="6,0 0,10 12,10" fill="#00E5A0" />
              </svg>
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
      </motion.div>

      {/* State ribbon */}
      <motion.div custom={4} initial="hidden" animate="visible" variants={fadeUp}
        className="ss-card p-6">
        <h2 className="ss-section-label mb-4">Sleep Architecture</h2>
        <StateRibbon segments={segments} totalDuration={totalDuration} progress={progress} />
        <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4 pt-4 border-t border-border">
          {stateSwatches.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: color }} />
              <span className="text-xs text-text-dim">{label}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
