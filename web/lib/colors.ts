export const palette = {
  bg: "#0B0F14",
  surface: "#141A21",
  surfaceAlt: "#1C242D",
  border: "#222D38",
  borderBright: "#2D3D4D",
  text: "#E6EDF3",
  textDim: "#8B98A5",
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
} as const;

export const stateColors: Record<string, string> = {
  listening: "#3D8B6E",
  flagged: "#FFB020",
  intervening: "#FF4D6D",
  escalating: "#FF2D55",
  resolved: "#A78BFA",
  awake: "#5AB1FF",
};

export const stateLabels: Record<string, string> = {
  listening: "Listening",
  flagged: "Flagged",
  intervening: "Intervening",
  escalating: "Escalating",
  resolved: "Resolved",
  awake: "Awake",
};

export function scoreToColor(score: number): string {
  if (score >= 70) return palette.mint;
  if (score >= 50) return palette.amber;
  return palette.danger;
}

export function scoreToBgClass(score: number | null): string {
  if (score === null) return "bg-surface-alt border-border";
  if (score >= 70) return "bg-mint/15 border-mint/30";
  if (score >= 50) return "bg-amber/15 border-amber/30";
  return "bg-danger/15 border-danger/30";
}
