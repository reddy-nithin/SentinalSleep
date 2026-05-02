"use client";

import { motion, useReducedMotion } from "framer-motion";
import { KpiTile } from "@/components/dashboard/KpiTile";
import { TrendSparkline } from "@/components/charts/TrendSparkline";
import { StateBreakdown } from "@/components/charts/StateBreakdown";
import { palette } from "@/lib/colors";
import type { TrendData } from "@/lib/data";

const EASE: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.38, delay: i * 0.07, ease: EASE },
  }),
};

const METRIC_DEFS = [
  {
    term: "Disturbances / Night",
    def: "Interventions + escalations per recorded session. Lower is better — target ≤ 1 per night.",
  },
  {
    term: "Effectiveness %",
    def: "Percentage of interventions where DSS dropped ≥ 0.20 within 60 s of the audio cue ending.",
  },
  {
    term: "Sleep State Mix",
    def: "Minutes per night in each state: listening (baseline calm), flagged (DSS > 0.4), and actively intervening.",
  },
];

export function TrendsClient({ t }: { t: TrendData }) {
  const shouldReduceMotion = useReducedMotion();

  const avgDisturbances =
    t.disturbances_per_night.reduce((a, b) => a + b, 0) / t.disturbances_per_night.length;
  const avgEffectiveness =
    t.effectiveness_by_night.reduce((a, b) => a + b, 0) / t.effectiveness_by_night.length;

  const hidden = shouldReduceMotion ? {} : "hidden";
  const visible = shouldReduceMotion ? {} : "visible";

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      {/* Header */}
      <motion.div custom={0} initial={hidden} animate={visible} variants={fadeUp}>
        <h1 className="text-2xl font-bold tracking-tight">Trends</h1>
        <p className="text-sm text-text-dim mt-1">
          Last {t.total_sessions} nights · {t.dates[0]} → {t.dates[t.dates.length - 1]}
        </p>
      </motion.div>

      {/* KPI row with count-up */}
      <motion.div
        custom={1}
        initial={hidden}
        animate={visible}
        variants={fadeUp}
        className="grid grid-cols-3 gap-4"
      >
        <KpiTile value={t.total_sessions} label="Total Sessions" accentClass="text-info" />
        <KpiTile value={t.total_interventions} label="Interventions" accentClass="text-amber" />
        <KpiTile
          value={Math.round(t.effective_rate_percent)}
          label="Effectiveness"
          accentClass="text-mint"
          suffix="%"
        />
      </motion.div>

      {/* Definitions strip */}
      <motion.dl
        custom={2}
        initial={hidden}
        animate={visible}
        variants={fadeUp}
        className="ss-card p-4 grid sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-border"
      >
        {METRIC_DEFS.map(({ term, def }) => (
          <div key={term} className="py-3 sm:py-0 sm:px-4 first:pt-0 sm:first:pl-0 last:pb-0 sm:last:pr-0">
            <dt className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-1">
              {term}
            </dt>
            <dd className="text-xs text-text-dim leading-relaxed">{def}</dd>
          </div>
        ))}
      </motion.dl>

      {/* Sparklines */}
      <motion.div
        custom={3}
        initial={hidden}
        animate={visible}
        variants={fadeUp}
        className="grid md:grid-cols-2 gap-4"
      >
        <div className="ss-card p-6">
          <h2 className="ss-section-label mb-1">Disturbances / Night</h2>
          <p className="text-xs text-text-dim mb-4">Interventions + escalations per session</p>
          <TrendSparkline
            data={t.disturbances_per_night}
            color={palette.danger}
            label="Disturbances"
            dates={t.dates}
            showYLabels
            showBestWorst
            baseline={avgDisturbances}
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
            unit="%"
            dates={t.dates}
            showYLabels
            showBestWorst
            baseline={avgEffectiveness}
          />
          <div className="flex justify-between mt-2 font-mono text-xs text-text-dim">
            <span>{t.dates[0].slice(5)}</span>
            <span>{t.dates[t.dates.length - 1].slice(5)}</span>
          </div>
        </div>
      </motion.div>

      {/* State breakdown chart */}
      {t.state_minutes_per_night && (
        <motion.div
          custom={4}
          initial={hidden}
          animate={visible}
          variants={fadeUp}
          className="ss-card p-6"
        >
          <h2 className="ss-section-label mb-1">Sleep State Mix</h2>
          <p className="text-xs text-text-dim mb-4">Minutes per night in each state</p>
          <StateBreakdown dates={t.dates} minutes={t.state_minutes_per_night} />
        </motion.div>
      )}

      <motion.p
        custom={5}
        initial={hidden}
        animate={visible}
        variants={fadeUp}
        className="text-xs text-text-dim italic"
      >
        Note: Series synthesized from {t.total_sessions}-session aggregate for v1. Live per-session
        data available with ≥14 recorded nights.
      </motion.p>
    </div>
  );
}
