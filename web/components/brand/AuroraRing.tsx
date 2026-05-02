"use client";

import { useEffect, useRef } from "react";
import { motion, useMotionValue, animate } from "framer-motion";
import { cn } from "@/lib/cn";
import { recoveryLabel } from "@/lib/recovery";

interface AuroraRingProps {
  score: number;
  disturbances: number;
  awakeMinutes: number;
  effectivenessPct: number;
  className?: string;
}

const RADIUS = 110;
const STROKE = 22;
const SIZE = 280;
const CENTER = SIZE / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function AuroraRing({
  score,
  disturbances,
  awakeMinutes,
  effectivenessPct,
  className,
}: AuroraRingProps) {
  const { label, pillClass } = recoveryLabel(score);
  const dashOffset = CIRCUMFERENCE * (1 - score / 100);

  const countVal = useMotionValue(0);
  const displayScore = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const ctrl = animate(countVal, score, {
      duration: 1.4,
      ease: [0.65, 0, 0.35, 1],
      onUpdate: (v) => {
        if (displayScore.current) {
          displayScore.current.textContent = String(Math.round(v));
        }
      },
    });
    return ctrl.stop;
  }, [score]);

  return (
    <div className={cn("flex flex-col items-center gap-6", className)}>
      <div className="relative">
        {/* Rotating aurora blur behind ring */}
        <div
          className="absolute inset-[-40px] rounded-full pointer-events-none"
          style={{
            background:
              "conic-gradient(from 0deg, #0FD3B5, #00E5A0, #A78BFA, #00E5A0, #0FD3B5)",
            filter: "blur(48px)",
            opacity: 0.18,
            animation: "spin 18s linear infinite",
          }}
        />

        {/* Halo pulse ring */}
        <motion.div
          className="absolute inset-[-8px] rounded-full pointer-events-none"
          style={{
            border: "4px solid #0FD3B5",
            filter: "blur(10px)",
          }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Main SVG ring */}
        <svg
          width={SIZE}
          height={SIZE}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="relative z-10"
        >
          <defs>
            <linearGradient id="auroraGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0FD3B5" />
              <stop offset="50%" stopColor="#00E5A0" />
              <stop offset="100%" stopColor="#A78BFA" />
            </linearGradient>
            <filter id="ringGlow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background track */}
          <circle
            cx={CENTER}
            cy={CENTER}
            r={RADIUS}
            fill="none"
            stroke="#222D38"
            strokeWidth={STROKE}
          />

          {/* Foreground progress arc */}
          <motion.circle
            cx={CENTER}
            cy={CENTER}
            r={RADIUS}
            fill="none"
            stroke="url(#auroraGrad)"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            transform={`rotate(-90 ${CENTER} ${CENTER})`}
            filter="url(#ringGlow)"
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.4, ease: [0.65, 0, 0.35, 1] }}
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
          <span
            ref={displayScore}
            className="text-aurora font-extrabold leading-none"
            style={{ fontSize: "3.2rem", letterSpacing: "-0.04em" }}
          >
            0
          </span>
          <span className="ss-kpi-label mt-1">Recovery Score</span>
          <span className={cn("ss-pill mt-3", pillClass)}>{label}</span>
        </div>
      </div>

      {/* Micro-pills */}
      <div className="flex flex-wrap justify-center gap-2">
        <span className="ss-pill ss-pill-red">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
            <circle cx="4" cy="4" r="4" />
          </svg>
          {disturbances} Disturbances
        </span>
        <span className="ss-pill ss-pill-amber">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
            <circle cx="4" cy="4" r="4" />
          </svg>
          {awakeMinutes}m Awake
        </span>
        <span className="ss-pill ss-pill-green">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
            <circle cx="4" cy="4" r="4" />
          </svg>
          {effectivenessPct}% Effective
        </span>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

