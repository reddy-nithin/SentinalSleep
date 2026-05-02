import Link from "next/link";
import { LayoutDashboard, Moon, Zap, TrendingUp } from "lucide-react";
import { getSessions, getTrends } from "@/lib/data";
import { DashboardTransition } from "./DashboardTransition";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/night/1", label: "Night Detail", icon: Moon },
  { href: "/dashboard/interventions", label: "Interventions", icon: Zap },
  { href: "/dashboard/trends", label: "Trends", icon: TrendingUp },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const trends = getTrends();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col w-60 border-r border-border bg-surface flex-shrink-0">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Link href="/" className="flex items-center gap-2">
            <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
              <path d="M11 2a9 9 0 1 0 9 9A9 9 0 0 0 11 2zm0 16a7 7 0 1 1 4.5-12.3A5 5 0 0 0 11 10a5 5 0 0 0 3.5 4.8A7 7 0 0 1 11 18z" fill="url(#sn)" />
              <defs>
                <linearGradient id="sn" x1="2" y1="2" x2="20" y2="20">
                  <stop stopColor="#0FD3B5" />
                  <stop offset="1" stopColor="#A78BFA" />
                </linearGradient>
              </defs>
            </svg>
            <span className="font-bold text-sm tracking-tight">
              <span className="text-text">Sentinel</span>
              <span className="text-mint">Sleep</span>
            </span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-text-dim hover:text-text hover:bg-surface-alt transition-colors"
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          ))}
        </nav>

        {/* 7-day footer stats */}
        <div className="p-4 border-t border-border space-y-3">
          <p className="ss-section-label text-[0.65rem]">7-day summary</p>
          <div className="space-y-2">
            {[
              { label: "Sessions", value: trends.total_sessions },
              { label: "Interventions", value: trends.total_interventions },
              { label: "Effectiveness", value: `${trends.effective_rate_percent.toFixed(0)}%`, className: "text-mint" },
            ].map(({ label, value, className }) => (
              <div key={label} className="flex justify-between items-center">
                <span className="text-xs text-text-dim">{label}</span>
                <span className={`text-xs font-semibold font-mono ${className ?? "text-text"}`}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0">
        <DashboardTransition>{children}</DashboardTransition>
      </main>
    </div>
  );
}
