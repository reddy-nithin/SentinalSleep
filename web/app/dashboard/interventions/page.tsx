import { getRecentInterventions } from "@/lib/data";
import { InterventionCard } from "@/components/dashboard/InterventionCard";
import { Zap } from "lucide-react";

export default function InterventionsPage() {
  const interventions = getRecentInterventions();
  const effective = interventions.filter((i) => i.effective === true).length;
  const pct = interventions.length > 0 ? Math.round((effective / interventions.length) * 100) : 0;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1280px]">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interventions</h1>
          <p className="text-sm text-text-dim mt-1">
            Last session · {interventions.length} total · {pct}% effective
          </p>
        </div>
        <div className="flex gap-2">
          <span className="ss-pill ss-pill-green">{effective} Effective</span>
          <span className="ss-pill ss-pill-dim">{interventions.length - effective} Other</span>
        </div>
      </div>

      {interventions.length === 0 ? (
        <div className="ss-card p-12 flex flex-col items-center gap-4 text-center">
          <Zap className="w-10 h-10 text-text-dim" />
          <p className="text-text-dim">No interventions recorded for this session.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {interventions.map((inv) => (
            <InterventionCard
              key={inv.id}
              startedAt={inv.started_at}
              preDss={inv.pre_dss}
              postDss={inv.post_dss}
              effective={inv.effective}
              clipName={inv.clip_path}
              audioUrl={inv.clip_path ? `/audio/${inv.clip_path}` : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
