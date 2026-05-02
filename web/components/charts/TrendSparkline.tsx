"use client";

import { useMemo, useState } from "react";
import { palette } from "@/lib/colors";

interface TrendSparklineProps {
  data: number[];
  color?: string;
  label: string;
  unit?: string;
  height?: number;
  dates?: string[];
  showYLabels?: boolean;
  showBestWorst?: boolean;
  baseline?: number;
}

export function TrendSparkline({
  data,
  color = palette.mint,
  label,
  unit = "",
  height = 80,
  dates,
  showYLabels = false,
  showBestWorst = false,
  baseline,
}: TrendSparklineProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const width = 280;
  const yLabelW = showYLabels ? 28 : 0;
  const pad = { t: 8, b: 8, l: 4 + yLabelW, r: 4 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;

  const { points, areaPath, linePath, minVal, maxVal, avgVal, bestIdx, worstIdx } = useMemo(() => {
    if (data.length < 2) {
      return { points: [], areaPath: "", linePath: "", minVal: 0, maxVal: 0, avgVal: 0, bestIdx: -1, worstIdx: -1 };
    }
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const avg = data.reduce((a, b) => a + b, 0) / data.length;

    const pts = data.map((v, i) => ({
      x: pad.l + (i / (data.length - 1)) * innerW,
      y: pad.t + (1 - (v - min) / range) * innerH,
    }));

    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const area =
      line +
      ` L${pts[pts.length - 1].x.toFixed(1)},${(pad.t + innerH).toFixed(1)} L${pad.l},${(pad.t + innerH).toFixed(1)} Z`;

    const maxIdx = data.indexOf(max);
    const minIdx = data.indexOf(min);

    return {
      points: pts,
      areaPath: area,
      linePath: line,
      minVal: min,
      maxVal: max,
      avgVal: avg,
      bestIdx: maxIdx,
      worstIdx: minIdx,
    };
  }, [data]);

  if (data.length < 2) return null;

  const id = `sg-${label.replace(/\s/g, "")}`;

  const baselineY =
    baseline !== undefined
      ? pad.t + (1 - (baseline - minVal) / (maxVal - minVal || 1)) * innerH
      : null;

  const tooltipItem = hovered !== null ? data[hovered] : null;
  const tooltipDate = hovered !== null && dates ? dates[hovered] : null;
  const tooltipX = hovered !== null ? points[hovered].x : 0;
  const tooltipY = hovered !== null ? points[hovered].y : 0;
  const tooltipRight = tooltipX > width * 0.6;

  return (
    <div className="relative">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        onMouseLeave={() => setHovered(null)}
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.22" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Y-axis labels */}
        {showYLabels && (
          <>
            <text x={yLabelW - 2} y={pad.t + 4} textAnchor="end" fontSize="9" fill={palette.textDim}>
              {maxVal.toFixed(0)}{unit}
            </text>
            <text x={yLabelW - 2} y={pad.t + innerH} textAnchor="end" fontSize="9" fill={palette.textDim}>
              {minVal.toFixed(0)}{unit}
            </text>
          </>
        )}

        {/* Baseline */}
        {baselineY !== null && (
          <line
            x1={pad.l}
            y1={baselineY}
            x2={pad.l + innerW}
            y2={baselineY}
            stroke={palette.textDim}
            strokeWidth="1"
            strokeDasharray="3,3"
            opacity="0.4"
          />
        )}

        {/* Area + line */}
        {areaPath && <path d={areaPath} fill={`url(#${id})`} />}
        {linePath && (
          <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        )}

        {/* Best / worst annotations */}
        {showBestWorst && points.length > 0 && bestIdx >= 0 && (
          <>
            <circle cx={points[bestIdx].x} cy={points[bestIdx].y} r="4" fill={palette.mint} opacity="0.9" />
            <circle cx={points[worstIdx].x} cy={points[worstIdx].y} r="4" fill={palette.danger} opacity="0.9" />
          </>
        )}

        {/* Latest dot */}
        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r="3"
            fill={color}
          />
        )}

        {/* Hover crosshair + dot */}
        {hovered !== null && points[hovered] && (
          <>
            <line
              x1={points[hovered].x}
              y1={pad.t}
              x2={points[hovered].x}
              y2={pad.t + innerH}
              stroke={color}
              strokeWidth="1"
              strokeDasharray="3,3"
              opacity="0.5"
            />
            <circle cx={points[hovered].x} cy={points[hovered].y} r="4" fill={color} />
          </>
        )}

        {/* Invisible hover hit-areas */}
        {points.map((pt, i) => {
          const slotW = innerW / (data.length - 1);
          return (
            <rect
              key={i}
              x={pt.x - slotW / 2}
              y={pad.t}
              width={slotW}
              height={innerH}
              fill="transparent"
              onMouseEnter={() => setHovered(i)}
            />
          );
        })}
      </svg>

      {/* Tooltip */}
      {hovered !== null && tooltipItem !== null && (
        <div
          className="pointer-events-none absolute bg-surface border border-border-bright rounded-lg px-2.5 py-1.5 text-xs shadow-lg z-10"
          style={{
            top: `${(tooltipY / height) * 100}%`,
            ...(tooltipRight
              ? { right: `${((width - tooltipX) / width) * 100 + 2}%` }
              : { left: `${(tooltipX / width) * 100 + 2}%` }),
            transform: "translateY(-50%)",
          }}
        >
          {tooltipDate && (
            <div className="text-text-dim font-mono text-[10px] mb-0.5">
              {tooltipDate.slice(5)}
            </div>
          )}
          <div className="font-semibold font-mono" style={{ color }}>
            {tooltipItem.toFixed(1)}{unit}
          </div>
        </div>
      )}
    </div>
  );
}
