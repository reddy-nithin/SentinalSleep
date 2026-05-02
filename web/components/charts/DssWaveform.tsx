"use client";

import { useMemo, useState } from "react";
import { palette } from "@/lib/colors";

interface DataPoint {
  t: number;
  dss: number;
  valence?: number | null;
  arousal?: number | null;
  dominance?: number | null;
  state: string;
}

interface Marker {
  t: number;
}

interface DssWaveformProps {
  data: DataPoint[];
  interventions?: Marker[];
  threshold?: number;
  showOverlays?: boolean;
  progress?: number;
  height?: number;
}

const W = 800;
const H_MAIN = 220;
const PAD = { t: 16, b: 30, l: 44, r: 16 };

function scaleX(t: number, maxT: number) {
  return PAD.l + ((t / maxT) * (W - PAD.l - PAD.r));
}
function scaleY(v: number, min: number, max: number) {
  return PAD.t + (1 - (v - min) / (max - min)) * (H_MAIN - PAD.t - PAD.b);
}

function buildPath(pts: Array<{ x: number; y: number }>, close?: { baseY: number }): string {
  if (pts.length < 2) return "";
  let d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  if (close) {
    d += ` L${pts[pts.length - 1].x.toFixed(1)},${close.baseY} L${pts[0].x.toFixed(1)},${close.baseY} Z`;
  }
  return d;
}

export function DssWaveform({
  data,
  interventions = [],
  threshold = 0.4,
  showOverlays = false,
  progress = 1,
  height = H_MAIN,
}: DssWaveformProps) {
  const [hoverX, setHoverX] = useState<number | null>(null);

  const { dssArea, dssLine, thresholdY, overlayPaths, markers, maxT, xTicks, yTicks, clipW } =
    useMemo(() => {
      if (data.length < 2)
        return { dssArea: "", dssLine: "", thresholdY: 0, overlayPaths: {}, markers: [], maxT: 1, xTicks: [], yTicks: [], clipW: W };

      const maxT = data[data.length - 1].t;
      const clipW = PAD.l + (progress * (W - PAD.l - PAD.r));
      const visible = data.filter((d) => d.t <= maxT * progress);
      const baseY = scaleY(0, 0, 1);

      const dssPts = visible.map((d) => ({ x: scaleX(d.t, maxT), y: scaleY(d.dss, 0, 1) }));
      const dssArea = buildPath(dssPts, { baseY });
      const dssLine = buildPath(dssPts);
      const thresholdY = scaleY(threshold, 0, 1);

      const overlayPaths: Record<string, string> = {};
      if (showOverlays) {
        const valPts = visible.filter((d) => d.valence != null).map((d) => ({ x: scaleX(d.t, maxT), y: scaleY(d.valence!, -1, 1.5) }));
        const aroPts = visible.filter((d) => d.arousal != null).map((d) => ({ x: scaleX(d.t, maxT), y: scaleY(d.arousal!, -1, 1.5) }));
        const domPts = visible.filter((d) => d.dominance != null).map((d) => ({ x: scaleX(d.t, maxT), y: scaleY(d.dominance!, -1, 1.5) }));
        if (valPts.length >= 2) overlayPaths.valence = buildPath(valPts);
        if (aroPts.length >= 2) overlayPaths.arousal = buildPath(aroPts);
        if (domPts.length >= 2) overlayPaths.dominance = buildPath(domPts);
      }

      const markers = interventions
        .filter((m) => m.t <= maxT * progress)
        .map((m) => {
          const x = scaleX(m.t, maxT);
          const pt = data.find((d) => Math.abs(d.t - m.t) < 120);
          const y = pt ? scaleY(pt.dss, 0, 1) : height / 2;
          return { x, y };
        });

      // X-axis ticks: every hour
      const xTicks = [];
      for (let t = 0; t <= maxT; t += 3600) {
        const h = Math.floor(t / 3600);
        xTicks.push({ x: scaleX(t, maxT), label: `${h}h` });
      }

      // Y-axis ticks
      const yTicks = [0, 0.2, 0.4, 0.6, 0.8, 1.0].map((v) => ({
        y: scaleY(v, 0, 1),
        label: v.toFixed(1),
      }));

      return { dssArea, dssLine, thresholdY, overlayPaths, markers, maxT, xTicks, yTicks, clipW };
    }, [data, interventions, threshold, showOverlays, progress, height]);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H_MAIN}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          setHoverX(e.clientX - rect.left);
        }}
        onMouseLeave={() => setHoverX(null)}
      >
        <defs>
          <linearGradient id="dssGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={palette.danger} stopOpacity="0.35" />
            <stop offset="100%" stopColor={palette.danger} stopOpacity="0.02" />
          </linearGradient>
          <clipPath id="progressClip">
            <rect x="0" y="0" width={clipW} height={H_MAIN} />
          </clipPath>
        </defs>

        {/* Grid lines */}
        {yTicks.map(({ y, label }) => (
          <g key={label}>
            <line x1={PAD.l} y1={y} x2={W - PAD.r} y2={y} stroke={palette.border} strokeWidth="0.5" />
            <text x={PAD.l - 6} y={y + 4} textAnchor="end" fontSize="9" fill={palette.textDim} fontFamily="JetBrains Mono">
              {label}
            </text>
          </g>
        ))}

        {/* X-axis ticks */}
        {xTicks.map(({ x, label }) => (
          <g key={label}>
            <line x1={x} y1={H_MAIN - PAD.b} x2={x} y2={H_MAIN - PAD.b + 4} stroke={palette.border} strokeWidth="0.8" />
            <text x={x} y={H_MAIN - 8} textAnchor="middle" fontSize="9" fill={palette.textDim} fontFamily="JetBrains Mono">
              {label}
            </text>
          </g>
        ))}

        {/* DSS area + line */}
        {dssArea && <path d={dssArea} fill="url(#dssGrad)" clipPath="url(#progressClip)" />}
        {dssLine && (
          <path d={dssLine} fill="none" stroke={palette.danger} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" clipPath="url(#progressClip)" />
        )}

        {/* Threshold line */}
        {thresholdY > 0 && (
          <g>
            <line x1={PAD.l} y1={thresholdY} x2={W - PAD.r} y2={thresholdY} stroke={palette.amber} strokeWidth="1" strokeDasharray="5,4" />
            <text x={W - PAD.r + 2} y={thresholdY + 4} fontSize="9" fill={palette.amber} fontFamily="JetBrains Mono">
              {threshold}
            </text>
          </g>
        )}

        {/* Overlays */}
        {showOverlays && overlayPaths.valence && (
          <path d={overlayPaths.valence} fill="none" stroke={palette.info} strokeWidth="1.5" strokeDasharray="4,3" opacity="0.8" clipPath="url(#progressClip)" />
        )}
        {showOverlays && overlayPaths.arousal && (
          <path d={overlayPaths.arousal} fill="none" stroke={palette.amber} strokeWidth="1.5" strokeDasharray="4,3" opacity="0.8" clipPath="url(#progressClip)" />
        )}
        {showOverlays && overlayPaths.dominance && (
          <path d={overlayPaths.dominance} fill="none" stroke={palette.violet} strokeWidth="1.5" strokeDasharray="4,3" opacity="0.8" clipPath="url(#progressClip)" />
        )}

        {/* Intervention markers */}
        {markers.map(({ x, y }, i) => (
          <g key={i}>
            <polygon
              points={`${x},${y - 12} ${x - 6},${y - 20} ${x + 6},${y - 20}`}
              fill={palette.mint}
              opacity="0.95"
            />
            <line x1={x} y1={y - 12} x2={x} y2={y} stroke={palette.mint} strokeWidth="1" strokeDasharray="2,2" />
          </g>
        ))}

        {/* Hover cursor */}
        {hoverX && (
          <line x1={hoverX} y1={PAD.t} x2={hoverX} y2={H_MAIN - PAD.b} stroke={palette.borderBright} strokeWidth="1" />
        )}
      </svg>

      {/* Overlay legend */}
      {showOverlays && (
        <div className="flex gap-4 mt-2 text-xs">
          {[
            { label: "Valence", color: palette.info },
            { label: "Arousal", color: palette.amber },
            { label: "Dominance", color: palette.violet },
          ].map(({ label, color }) => (
            <span key={label} className="flex items-center gap-1.5 text-text-dim">
              <svg width="16" height="8"><line x1="0" y1="4" x2="16" y2="4" stroke={color} strokeWidth="1.5" strokeDasharray="4,2" /></svg>
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
