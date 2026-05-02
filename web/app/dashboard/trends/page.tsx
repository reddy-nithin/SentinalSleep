import { getTrends } from "@/lib/data";
import { TrendSparkline } from "@/components/charts/TrendSparkline";
import { palette } from "@/lib/colors";

export default function TrendsPage() {
  const t = getTrends();

  const kpis = [
    { label: "Total Sessions", value: t.total_sessions, color: "text-info" },
    { label: "Interventions", value: t.total_interventions, color: "text-amber" },
    {
      label: "Effectiveness",
      value: `${t.effective_rate_percent.toFixed(0)}%`,
      color: "text-mint",
    },
  ];

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trends</h1>
        <p className="text-sm text-text-dim mt-1">Last 14 nights · {t.dates[0]} → {t.dates[t.dates.length - 1]}</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4">
        {kpis.map(({ label, value, color }) => (
          <div key={label} className="ss-card p-6">
            <p className="ss-kpi-label">{label}</p>
            <p className={`ss-kpi-number mt-3 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Sparkline charts */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="ss-card p-6">
          <h2 className="ss-section-label mb-1">Disturbances / Night</h2>
          <p className="text-xs text-text-dim mb-4">Interventions + escalations per session</p>
          <TrendSparkline
            data={t.disturbances_per_night}
            color={palette.danger}
            label="Disturbances"
          />
          <div className="flex justify-between mt-2 font-mono text-xs text-text-dim">
            <span>{t.dates[0].slice(5)}</span>
            <span>{t.dates[t.dates.length - 1].slice(5)}</span>
          </div>
        </div>

        <div className="ss-card p-6">
          <h2 className="ss-section-label mb-1">Effectiveness %</h2>
          <p className="text-xs text-text-dim mb-4">Percentage of interventions marked effective</p>
          <TrendSparkline
            data={t.effectiveness_by_night}
            color={palette.mint}
            label="Effectiveness"
          />
          <div className="flex justify-between mt-2 font-mono text-xs text-text-dim">
            <span>{t.dates[0].slice(5)}</span>
            <span>{t.dates[t.dates.length - 1].slice(5)}</span>
          </div>
        </div>
      </div>

      <p className="text-xs text-text-dim italic">
        Note: Series synthesized from 14-session aggregate for v1. Live per-session data available with ≥14 recorded nights.
      </p>
    </div>
  );
}
