import { cn } from "@/lib/cn";

const steps = [
  {
    num: "01",
    title: "Detection",
    subtitle: "MIT AST model classifies 2-second audio chunks across 527 AudioSet classes.",
    badge: "DSS > 0.4 → escalate",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M3 12h18M3 6h18M3 18h18" opacity=".3" />
        <path d="M7 12l2-4 2 8 2-6 2 4" />
      </svg>
    ),
  },
  {
    num: "02",
    title: "Verification",
    subtitle: "wav2vec2 returns valence, arousal, and dominance. Nightmare = low V + high A + low D, sustained ≥15s.",
    badge: "< 3s latency",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5.6 5.6l1.4 1.4M16.9 16.9l1.5 1.5M5.6 18.4l1.4-1.4M16.9 7.1l1.5-1.5" />
      </svg>
    ),
  },
  {
    num: "03",
    title: "Intervention",
    subtitle: "Pre-cached MusicGen + AudioLDM2 therapeutic audio plays at −20 dBFS, mixed with ambient sound for 60 seconds.",
    badge: "100% cache hit rate",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M9 18V5l12-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="18" cy="16" r="3" />
      </svg>
    ),
  },
  {
    num: "04",
    title: "Resolution",
    subtitle: "If distress resolves, system returns to listening. If it persists, a progressive wake protocol activates.",
    badge: "Morning report ready",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5M2 12l10 5 10-5" opacity=".5" />
      </svg>
    ),
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="ss-pill ss-pill-dim mb-4 inline-block">How it works</span>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Four layers of protection</h2>
          <p className="text-text-dim mt-4 max-w-xl mx-auto">
            From audio detection to therapeutic response in under 3 seconds — running fully offline on your device.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {steps.map((step, i) => (
            <div key={step.num} className="relative">
              {/* Connector line */}
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-10 left-full w-5 border-t-2 border-dashed border-border z-10" />
              )}

              <div className="ss-card p-6 h-full flex flex-col gap-4">
                {/* Step badge + icon */}
                <div className="flex items-center justify-between">
                  <span className="w-7 h-7 rounded-full bg-mint/15 text-mint text-xs font-bold flex items-center justify-center">
                    {step.num}
                  </span>
                  <span className="text-text-dim">{step.icon}</span>
                </div>

                <div className="flex flex-col gap-2 flex-1">
                  <h3 className="font-bold text-base">{step.title}</h3>
                  <p className="text-sm text-text-dim leading-relaxed flex-1">{step.subtitle}</p>
                </div>

                <span className="ss-pill ss-pill-green self-start text-[11px]">{step.badge}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
