"use client";

import { useMemo } from "react";
import { palette } from "@/lib/colors";

interface TrendSparklineProps {
  data: number[];
  color?: string;
  label: string;
  unit?: string;
  height?: number;
}

export function TrendSparkline({
  data,
  color = palette.mint,
  label,
  unit = "",
  height = 72,
}: TrendSparklineProps) {
  const width = 280;
  const pad = { t: 8, b: 8, l: 4, r: 4 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;

  const { points, areaPath, linePath } = useMemo(() => {
    if (data.length < 2) return { points: [], areaPath: "", linePath: "" };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const pts = data.map((v, i) => ({
      x: pad.l + (i / (data.length - 1)) * innerW,
      y: pad.t + (1 - (v - min) / range) * innerH,
    }));

    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const area =
      line +
      ` L${pts[pts.length - 1].x.toFixed(1)},${(pad.t + innerH).toFixed(1)} L${pad.l},${(pad.t + innerH).toFixed(1)} Z`;

    return { points: pts, areaPath: area, linePath: line };
  }, [data]);

  if (data.length < 2) return null;

  const id = `sg-${label.replace(/\s/g, "")}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {areaPath && <path d={areaPath} fill={`url(#${id})`} />}
      {linePath && <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
      {points.length > 0 && (
        <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="3" fill={color} />
      )}
    </svg>
  );
}
