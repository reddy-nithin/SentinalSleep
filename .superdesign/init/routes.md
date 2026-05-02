# SentinelSleep Web App Routes

## App Router Structure (Next.js 15)

```
app/
├── (marketing)/
│   └── page.tsx              → "/"   Landing page
├── dashboard/
│   ├── layout.tsx            → "/dashboard/*"  Dashboard shell with sidebar
│   ├── page.tsx              → "/dashboard"    Overview (default)
│   ├── night/
│   │   └── [sessionId]/
│   │       └── page.tsx      → "/dashboard/night/:id"  Night Detail
│   ├── interventions/
│   │   └── page.tsx          → "/dashboard/interventions"
│   └── trends/
│       └── page.tsx          → "/dashboard/trends"
└── style-guide/
    └── page.tsx              → "/style-guide"  Component showcase (dev only)
```

## Page Descriptions

| Route | Purpose | Key components |
|-------|---------|----------------|
| `/` | Marketing landing — story, problem, how-it-works, dashboard preview | Hero, HowItWorks, ScreenshotCarousel, Footer |
| `/dashboard` | Morning recovery overview — aurora ring, KPIs, stage bar, 30-day heatmap | AuroraRing, KpiStrip, StageBar, RecoveryHeatmap |
| `/dashboard/night/:id` | Night detail — DSS waveform, emotion overlays, state ribbon, replay | DssWaveform, StateRibbon, ReplayController |
| `/dashboard/interventions` | Intervention cards — pre/post DSS, effectiveness, audio player | InterventionCard grid |
| `/dashboard/trends` | 7-day aggregates + 14-day sparklines | KpiTile × 3, TrendSparkline × 2 |
