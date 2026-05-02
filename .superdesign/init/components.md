# SentinelSleep UI Components

This is a brand-new project. Components listed below are the planned primitives to be built.

## AuroraRing (signature component)

Pure SVG, 280×280px, animated aurora recovery ring.

```tsx
// components/brand/AuroraRing.tsx
"use client";
import { motion } from "framer-motion";

interface AuroraRingProps {
  score: number; // 0-100
  disturbances: number;
  awakeMinutes: number;
  effectivenessPct: number;
}

// Ring: strokeDasharray fills score/100 of circumference (r=110, stroke=22)
// Foreground stroke uses SVG linearGradient (teal→mint→violet)
// Outer halo: 4px stroke, blur 12px, opacity pulses 0.4→0.7→0.4 over 4s
// Center: score number (Inter 800, gradient fill), "RECOVERY" label (0.72rem, uppercase, text-dim)
// Below ring: 3 micro-pills (Disturbances · Awake · Effective%)
```

## KpiTile

Dark card with 2.4rem stat, uppercase label, optional delta pill.

```tsx
// components/dashboard/KpiTile.tsx
interface KpiTileProps {
  value: string | number;
  label: string;
  delta?: { value: string; positive: boolean };
  accent?: "mint" | "amber" | "danger" | "info" | "violet";
}
```

## DssWaveform

Visx AreaClosed chart — DSS curve, threshold line, markers, optional overlays.

```tsx
// components/charts/DssWaveform.tsx
interface DssWaveformProps {
  data: Array<{ t: number; dss: number; valence?: number; arousal?: number; dominance?: number; state: string; }>;
  interventions: Array<{ t: number }>; // triangle markers
  threshold?: number; // default 0.4
  showOverlays?: boolean; // valence/arousal/dominance toggle
  progress?: number; // 0-1 for replay animation (clips data at progress * maxT)
}
// Colors: DSS fill #FF4D6D→transparent, threshold rule dashed #FFB020
// Overlays: valence #5AB1FF dotted, arousal #FFB020 dotted, dominance #A78BFA dotted
// Intervention markers: ▼ triangle at DSS curve y, mint color
```

## StateRibbon

Stacked horizontal timeline of sleep states.

```tsx
// components/charts/StateRibbon.tsx
interface StateRibbonProps {
  segments: Array<{ state: string; startT: number; endT: number; }>;
  totalDuration: number;
  progress?: number; // 0-1 for replay clip
}
// State colors map to palette.state.*
// Each segment: rounded ends, tooltip on hover showing "State HH:MM:SS → HH:MM:SS"
```

## InterventionCard

```tsx
// components/dashboard/InterventionCard.tsx
interface InterventionCardProps {
  timestamp: string;       // "Jan 01 — HH:MM:SS"
  preDss: number;
  postDss: number;
  effective: boolean | null; // null = pending
  clipName: string;
  audioUrl?: string;
}
// DSS delta: "0.72 → 0.31" with colored arrow (green if improved, red if worsened)
// Effectiveness pill: ss-pill-green "Effective" | ss-pill-red "Ineffective" | ss-pill-dim "Pending"
// Audio: native <audio> element with simple controls
```

## RecoveryHeatmap

30-day calendar grid, 7 columns, color-coded by score.

```tsx
// components/charts/RecoveryHeatmap.tsx
interface RecoveryHeatmapProps {
  nights: Array<{ date: string; score: number | null }>;
}
// Cell: 32×32px, border-radius 6px
// Color: score≥70 → mint/20, score≥50 → amber/20, score<50 → danger/20, null → surface-alt
// Hover: tooltip "YYYY-MM-DD\nScore: XX"
```

## TrendSparkline

```tsx
// components/charts/TrendSparkline.tsx
interface TrendSparklineProps {
  data: Array<{ day: string; value: number }>;
  color: string; // mint or danger
  label: string;
}
```
