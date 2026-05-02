# SentinelSleep Design Tokens

## Stack
Next.js 15 App Router + TypeScript + Tailwind CSS v4 + shadcn/ui + Visx charts + Framer Motion. Dark mode only. Inter + JetBrains Mono fonts via next/font/google.

## Tailwind Config (tailwind.config.ts)

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0F14",
        surface: "#141A21",
        "surface-alt": "#1C242D",
        border: "#222D38",
        text: "#E6EDF3",
        "text-dim": "#8B98A5",
        mint: "#00E5A0",
        amber: "#FFB020",
        danger: "#FF4D6D",
        info: "#5AB1FF",
        violet: "#A78BFA",
        aurora: {
          teal: "#0FD3B5",
          mint: "#00E5A0",
          violet: "#A78BFA",
          glow: "#7CFFD3",
        },
        "warm-dawn": "#F4B393",
        state: {
          listening: "#3D8B6E",
          flagged: "#FFB020",
          intervening: "#FF4D6D",
          escalating: "#FF2D55",
          resolved: "#A78BFA",
          awake: "#5AB1FF",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        card: "12px",
        "card-lg": "16px",
        pill: "20px",
      },
      backdropBlur: {
        card: "12px",
      },
    },
  },
};

export default config;
```

## globals.css

```css
@import "tailwindcss";

:root {
  --bg: #0B0F14;
  --surface: #141A21;
  --surface-alt: #1C242D;
  --border: #222D38;
  --text: #E6EDF3;
  --text-dim: #8B98A5;
  --mint: #00E5A0;
  --amber: #FFB020;
  --danger: #FF4D6D;
  --info: #5AB1FF;
  --violet: #A78BFA;
  --aurora-teal: #0FD3B5;
  --aurora-mint: #00E5A0;
  --aurora-violet: #A78BFA;
  --aurora-glow: #7CFFD3;
}

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: "Inter", system-ui, sans-serif;
}

/* Card base */
.ss-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

/* KPI numbers */
.ss-kpi-number {
  font-size: 2.4rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
}

/* Small labels */
.ss-kpi-label {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-dim);
}

/* Pills */
.ss-pill { padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }
.ss-pill-green { background: rgba(0,229,160,0.15); color: var(--mint); }
.ss-pill-red { background: rgba(255,77,109,0.15); color: var(--danger); }
.ss-pill-amber { background: rgba(255,176,32,0.15); color: var(--amber); }
.ss-pill-dim { background: rgba(139,152,165,0.15); color: var(--text-dim); }
.ss-pill-violet { background: rgba(167,139,250,0.15); color: var(--violet); }
```

## Design Principles

- **Surfaces**: 1px `border` outline on all cards, 12–16px radius, subtle backdrop-blur where cards overlay aurora glow
- **Motion**: Framer Motion — 60ms stagger between dashboard cards, KPI count-ups on mount, aurora ring conic gradient rotates at 0.05 turn/s (18s/turn), pulsing outer halo 4s loop (opacity 0.4→0.7→0.4)
- **Typography hierarchy**:
  - Hero display: Inter 800, -0.04em, gradient fill (teal→violet) for score numbers
  - Section headers: Inter 700, 0.02em, `text` color
  - Labels: Inter 600, 0.08em, uppercase, `text-dim`
  - Mono: JetBrains Mono for all timestamps, DSS values, clip names
- **Color semantics**:
  - `mint` (#00E5A0) — good/recovered/effective
  - `amber` (#FFB020) — warning/flagged
  - `danger` (#FF4D6D) — distress/intervening
  - `violet` (#A78BFA) — resolved/completed
  - `info` (#5AB1FF) — awake/neutral info
- **State colors** (for StateRibbon and legend):
  - listening: #3D8B6E (dark green)
  - flagged: #FFB020 (amber)
  - intervening: #FF4D6D (danger red)
  - escalating: #FF2D55 (deeper red)
  - resolved: #A78BFA (violet)
  - awake: #5AB1FF (info blue)
- **Aurora gradient**: conic gradient from `aurora-teal` → `aurora-mint` → `aurora-violet` → `aurora-mint` → `aurora-teal`, rotating
- **Glass surfaces on landing**: background with very subtle `aurora-teal/5` glow behind hero card
