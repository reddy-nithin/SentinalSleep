import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function Nav() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border backdrop-blur-md bg-bg/80">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          {/* Moon icon */}
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M11 2a9 9 0 1 0 9 9A9 9 0 0 0 11 2zm0 16a7 7 0 1 1 4.5-12.3A5 5 0 0 0 11 10a5 5 0 0 0 3.5 4.8A7 7 0 0 1 11 18z" fill="url(#nm)" />
            <defs>
              <linearGradient id="nm" x1="2" y1="2" x2="20" y2="20">
                <stop stopColor="#0FD3B5" />
                <stop offset="1" stopColor="#A78BFA" />
              </linearGradient>
            </defs>
          </svg>
          <span className="font-bold text-lg tracking-tight">
            <span className="text-text">Sentinel</span>
            <span className="text-mint">Sleep</span>
          </span>
        </Link>

        <Link
          href="/dashboard"
          className="flex items-center gap-2 px-4 py-2 rounded-full border border-mint/50 text-mint text-sm font-semibold hover:bg-mint/10 transition-colors"
        >
          View Dashboard
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </nav>
  );
}
