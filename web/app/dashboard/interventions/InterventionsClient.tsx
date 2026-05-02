"use client";

import { motion } from "framer-motion";
import { Zap, Info } from "lucide-react";
import { useState } from "react";
import { InterventionCard } from "@/components/dashboard/InterventionCard";
import type { Intervention } from "@/lib/data";

const EASE: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.36, delay: i * 0.07, ease: EASE },
  }),
};

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.32, ease: EASE } },
};

function ExplainerCard() {
  const [open, setOpen] = useState(false);
  return (
    <div className="ss-card p-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-between w-full text-left gap-2"
      >
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-info flex-shrink-0" />
          <span className="text-sm font-medium text-text">How interventions work</span>
        </div>
        <span className="text-xs text-text-dim">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="mt-4 space-y-3 border-t border-border pt-4">
          <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
            <div>
              <dt className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-1">
                DSS — Distress Signal Score
              </dt>
              <dd className="text-text-dim leading-relaxed text-xs">
                A composite 0–1 score. MIT AudioSet detects distress sounds; wav2vec2 adds
                valence/arousal from your voice. Higher = more distress. Threshold for intervention
                is <span className="text-amber font-medium">0.4</span>; above{" "}
                <span className="text-danger font-medium">0.7</span> is severe.
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-1">
                What &quot;Effective&quot; means
              </dt>
              <dd className="text-text-dim leading-relaxed text-xs">
                An intervention is marked{" "}
                <span className="text-mint font-medium">Effective</span> when DSS drops by ≥ 0.20
                within 60s of the audio cue ending.{" "}
                <span className="text-text-dim">Pending</span> means data is still being collected.
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-1">
                The audio cue
              </dt>
              <dd className="text-text-dim leading-relaxed text-xs">
                A pre-generated therapeutic clip (nature sounds, binaural beats) played at −20 dBFS
                through a bedside speaker — quiet enough not to wake you, but enough to shift brain
                state.
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-1">
                Reading the bar
              </dt>
              <dd className="text-text-dim leading-relaxed text-xs">
                Each card shows a{" "}
                <span className="text-danger font-medium">red marker</span> (DSS before) and a{" "}
                <span className="text-mint font-medium">green marker</span> (DSS after) on the 0–1
                scale. The further left the green marker, the better the outcome.
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

interface GroupSectionProps {
  title: string;
  dotColor: string;
  titleColor: string;
  items: Intervention[];
  custom: number;
}

function GroupSection({ title, dotColor, titleColor, items, custom }: GroupSectionProps) {
  return (
    <motion.section custom={custom} initial="hidden" animate="visible" variants={fadeUp}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full" style={{ background: dotColor }} />
        <h2
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: dotColor }}
        >
          {title} — {items.length}
        </h2>
      </div>
      <motion.div
        className="grid md:grid-cols-2 gap-4"
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
      >
        {items.map((inv) => (
          <motion.div key={inv.id} variants={cardVariants}>
            <InterventionCard
              startedAt={inv.started_at}
              preDss={inv.pre_dss}
              postDss={inv.post_dss}
              effective={inv.effective}
              clipName={inv.clip_path}
              audioUrl={inv.clip_path ? `/audio/${inv.clip_path}` : undefined}
            />
          </motion.div>
        ))}
      </motion.div>
    </motion.section>
  );
}

export function InterventionsClient({ interventions }: { interventions: Intervention[] }) {
  const effective = interventions.filter((i) => i.effective === true);
  const ineffective = interventions.filter((i) => i.effective === false);
  const pending = interventions.filter((i) => i.effective === null);
  const effectivePct =
    interventions.length > 0 ? Math.round((effective.length / interventions.length) * 100) : 0;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      {/* Header */}
      <motion.div
        custom={0}
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        className="flex items-end justify-between flex-wrap gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interventions</h1>
          <p className="text-sm text-text-dim mt-1">
            Last session · {interventions.length} total · {effectivePct}% effective
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <span className="ss-pill ss-pill-green">{effective.length} Effective</span>
          {ineffective.length > 0 && (
            <span className="ss-pill ss-pill-red">{ineffective.length} Ineffective</span>
          )}
          {pending.length > 0 && (
            <span className="ss-pill ss-pill-dim">{pending.length} Pending</span>
          )}
        </div>
      </motion.div>

      {/* Explainer */}
      <motion.div custom={1} initial="hidden" animate="visible" variants={fadeUp}>
        <ExplainerCard />
      </motion.div>

      {interventions.length === 0 ? (
        <motion.div
          custom={2}
          initial="hidden"
          animate="visible"
          variants={fadeUp}
          className="ss-card p-12 flex flex-col items-center gap-4 text-center"
        >
          <Zap className="w-10 h-10 text-text-dim" />
          <p className="text-text-dim">No interventions recorded for this session.</p>
        </motion.div>
      ) : (
        <div className="space-y-6">
          {effective.length > 0 && (
            <GroupSection
              title="Effective"
              dotColor="#00E5A0"
              titleColor="#00E5A0"
              items={effective}
              custom={2}
            />
          )}
          {ineffective.length > 0 && (
            <GroupSection
              title="Ineffective"
              dotColor="#FF4D6D"
              titleColor="#FF4D6D"
              items={ineffective}
              custom={3}
            />
          )}
          {pending.length > 0 && (
            <GroupSection
              title="Pending"
              dotColor="#8B98A5"
              titleColor="#8B98A5"
              items={pending}
              custom={4}
            />
          )}
        </div>
      )}
    </div>
  );
}
