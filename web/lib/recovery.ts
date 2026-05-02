import type { SessionEvent, Intervention } from "./data";

export function computeRecoveryScore(
  events: SessionEvent[],
  interventions: Intervention[]
): number {
  const nightmareEvents = events.filter(
    (e) => e.state === "intervening" || e.state === "escalating"
  ).length;
  const escalations = events.filter((e) => e.state === "escalating").length;
  const awakeChunks = events.filter((e) => e.state === "awake").length;
  const awakeMinutes = (awakeChunks * 2) / 60;

  const total = interventions.length;
  const effective = interventions.filter((i) => i.effective === true).length;
  const effectiveRate = total > 0 ? effective / total : 1;

  let score = 100;
  score -= Math.min(nightmareEvents * 3, 30);
  score -= escalations * 5;
  score -= Math.min(awakeMinutes * 2, 20);
  score += effectiveRate * 10 - 5;

  return Math.max(0, Math.min(100, Math.round(score)));
}

export function recoveryLabel(score: number): { label: string; pillClass: string } {
  if (score >= 75) return { label: "Optimal", pillClass: "ss-pill-green" };
  if (score >= 55) return { label: "Good", pillClass: "ss-pill-green" };
  if (score >= 40) return { label: "Fair", pillClass: "ss-pill-amber" };
  return { label: "Strained", pillClass: "ss-pill-red" };
}

export function computeKpis(events: SessionEvent[], interventions: Intervention[]) {
  const disturbances = events.filter(
    (e) => e.state === "intervening" || e.state === "escalating"
  ).length;
  const awakeChunks = events.filter((e) => e.state === "awake").length;
  const awakeMinutes = Math.round((awakeChunks * 2) / 60);
  const total = interventions.length;
  const effective = interventions.filter((i) => i.effective === true).length;
  const effectivenessPct = total > 0 ? Math.round((effective / total) * 100) : 100;
  return { disturbances, awakeMinutes, effectivenessPct, totalInterventions: total };
}
