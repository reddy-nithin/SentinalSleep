import { getSessions, getNightData } from "@/lib/data";
import { computeRecoveryScore, computeKpis } from "@/lib/recovery";
import { formatDate, formatDuration } from "@/lib/time";
import { AuroraRing } from "@/components/brand/AuroraRing";
import { KpiTile } from "@/components/dashboard/KpiTile";
import { SessionPicker } from "@/components/dashboard/SessionPicker";
import { StateRibbon } from "@/components/charts/StateRibbon";
import { buildSegments } from "@/lib/segments";
import { RecoveryHeatmap } from "@/components/charts/RecoveryHeatmap";

function buildHeatmapData(sessions: ReturnType<typeof getSessions>) {
  // Generate 30-day window with known sessions filled in
  const nights = [];
  const today = new Date("2026-05-02");
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    // Fake scores based on seeded data for demo
    const seed = (d.getDate() * 13 + d.getMonth() * 7) % 100;
    const score = sessions.find((s) => s.started_at.startsWith(dateStr))
      ? 82
      : seed > 60
      ? Math.round(55 + seed * 0.35)
      : seed > 30
      ? Math.round(35 + seed * 0.5)
      : null;
    nights.push({ date: dateStr, score });
  }
  return nights;
}

export default function OverviewPage() {
  const sessions = getSessions();
  const { events, interventions, session } = getNightData(1);

  const score = computeRecoveryScore(events, interventions);
  const { disturbances, awakeMinutes, effectivenessPct, totalInterventions } = computeKpis(events, interventions);

  const sessionDuration = session.ended_at
    ? Math.round((new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 1000)
    : 0;

  const segments = buildSegments(events, session.started_at);
  const totalDuration = segments.reduce((s, seg) => Math.max(s, seg.endT), 0);

  const heatmapNights = buildHeatmapData(sessions);

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Good Morning</h1>
          <p className="text-sm text-text-dim mt-1">
            {formatDate(session.started_at)} · Last session: {formatDuration(sessionDuration)}
          </p>
        </div>
        <SessionPicker sessions={sessions} currentId={session.id} />
      </div>

      {/* Hero row: ring + KPIs */}
      <div className="grid lg:grid-cols-[auto_1fr] gap-6 items-center">
        <div className="ss-card p-8 flex items-center justify-center relative overflow-hidden">
          <AuroraRing
            score={score}
            disturbances={disturbances}
            awakeMinutes={awakeMinutes}
            effectivenessPct={effectivenessPct}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <KpiTile
            label="Disturbances"
            value={disturbances}
            accentClass="text-danger"
            delta={{ text: "1 from last night", positive: true }}
          />
          <KpiTile
            label="Awake Time"
            value={awakeMinutes}
            suffix="m"
            accentClass="text-amber"
          />
          <KpiTile
            label="Interventions"
            value={totalInterventions}
            accentClass="text-mint"
          />
          <KpiTile
            label="Effectiveness"
            value={effectivenessPct}
            suffix="%"
            accentClass="text-mint"
          />
        </div>
      </div>

      {/* Stage bar */}
      <div className="ss-card p-6">
        <div className="flex justify-between items-center mb-5">
          <h2 className="ss-section-label">Sleep Architecture</h2>
          <span className="font-mono text-xs text-text-dim">{formatDate(session.started_at)}</span>
        </div>
        <StateRibbon segments={segments} totalDuration={totalDuration} />
      </div>

      {/* Recovery heatmap */}
      <div className="ss-card p-6">
        <h2 className="ss-section-label mb-5">30-Day Recovery</h2>
        <RecoveryHeatmap nights={heatmapNights} />
      </div>
    </div>
  );
}
