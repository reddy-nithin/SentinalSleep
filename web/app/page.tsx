import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";
import { Nav } from "@/components/marketing/Nav";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { Footer } from "@/components/marketing/Footer";

const stats = [
  {
    value: "8,000,000",
    label: "Americans experience PTSD-related nightmares each year.",
    icon: "🧠",
    color: "text-danger",
  },
  {
    value: "Drugs have side effects",
    label: "Benzodiazepines and prazosin help some — not all. Image rehearsal therapy requires a therapist.",
    icon: "💊",
    color: "text-amber",
  },
  {
    value: "No one in the bedroom",
    label: "Therapists and partners can't monitor every night. AI can — quietly, without disruption.",
    icon: "🛏",
    color: "text-info",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Nav />

      {/* Hero */}
      <section className="relative flex-1 px-6 pt-20 pb-16 overflow-hidden">
        <div
          className="absolute top-0 right-0 w-[700px] h-[600px] pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse at 70% 20%, rgba(15,211,181,0.12) 0%, rgba(167,139,250,0.06) 40%, transparent 70%)",
          }}
        />

        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
          {/* Copy */}
          <div className="flex flex-col gap-7 max-w-xl">
            <span className="ss-pill ss-pill-dim self-start flex items-center gap-2">
              <Shield className="w-3 h-3" />
              Research Prototype · Not a Medical Device
            </span>

            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight leading-[1.08]">
              Your{" "}
              <span className="text-aurora">AI guardian</span>
              {" "}for PTSD nightmares.
            </h1>

            <p className="text-lg text-text-dim leading-relaxed">
              SentinelSleep listens while you sleep, detects nightmare acoustic signatures, and plays calibrated therapeutic audio — gently interrupting distress without waking you.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-6 py-3 rounded-full bg-mint text-bg font-bold text-sm hover:opacity-90 transition-all hover:scale-[1.02]"
                style={{ boxShadow: "0 0 24px rgba(0,229,160,0.35)" }}
              >
                See Last Night&apos;s Report
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#how-it-works"
                className="flex items-center gap-2 px-6 py-3 rounded-full border border-mint/40 text-mint font-semibold text-sm hover:bg-mint/10 transition-colors"
              >
                How It Works ↓
              </a>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              {["8M Americans affected", "< 3s detection latency", "0 wake-ups in demo sessions"].map((t) => (
                <span key={t} className="ss-pill ss-pill-dim">{t}</span>
              ))}
            </div>
          </div>

          {/* Hero ring card */}
          <div className="flex justify-center lg:justify-end">
            <div
              className="relative p-8 rounded-2xl border border-border flex flex-col items-center gap-6"
              style={{
                background: "rgba(20,26,33,0.85)",
                backdropFilter: "blur(20px)",
                boxShadow: "0 0 80px rgba(15,211,181,0.08), 0 4px 32px rgba(0,0,0,0.4)",
              }}
            >
              <div className="relative w-[240px] h-[240px]">
                <div
                  className="absolute inset-[-32px] rounded-full"
                  style={{
                    background:
                      "conic-gradient(from 0deg, #0FD3B5, #00E5A0, #A78BFA, #00E5A0, #0FD3B5)",
                    filter: "blur(40px)",
                    opacity: 0.15,
                    animation: "spin 18s linear infinite",
                  }}
                />
                <svg width="240" height="240" viewBox="0 0 280 280" className="relative z-10">
                  <defs>
                    <linearGradient id="hg" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#0FD3B5" />
                      <stop offset="50%" stopColor="#00E5A0" />
                      <stop offset="100%" stopColor="#A78BFA" />
                    </linearGradient>
                  </defs>
                  <circle cx="140" cy="140" r="110" fill="none" stroke="#222D38" strokeWidth="22" />
                  <circle
                    cx="140" cy="140" r="110" fill="none"
                    stroke="url(#hg)" strokeWidth="22" strokeLinecap="round"
                    strokeDasharray="691.15" strokeDashoffset="124.4"
                    transform="rotate(-90 140 140)"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span
                    className="text-aurora font-extrabold leading-none"
                    style={{ fontSize: "2.8rem", letterSpacing: "-0.04em" }}
                  >
                    82
                  </span>
                  <span className="ss-kpi-label mt-1">Recovery Score</span>
                  <span className="ss-pill ss-pill-green mt-2">Optimal</span>
                </div>
              </div>

              <div className="flex gap-2 flex-wrap justify-center">
                <span className="ss-pill ss-pill-red">3 Disturbances</span>
                <span className="ss-pill ss-pill-amber">12m Awake</span>
                <span className="ss-pill ss-pill-green">85% Effective</span>
              </div>

              <p className="font-mono text-xs text-text-dim text-center">
                May 1, 2026 · 7h 23m · 2 interventions
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="bg-surface py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-center text-2xl md:text-3xl font-bold mb-12 tracking-tight">
            Why this matters
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {stats.map((s) => (
              <div key={s.icon} className="ss-card p-7 flex flex-col gap-3">
                <div className="text-3xl">{s.icon}</div>
                <div className={`text-xl md:text-2xl font-bold tracking-tight leading-tight ${s.color}`}>
                  {s.value}
                </div>
                <p className="text-sm text-text-dim leading-relaxed">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div id="how-it-works">
        <HowItWorks />
      </div>

      <Footer />

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
