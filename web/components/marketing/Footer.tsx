import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-text-dim">
        <div className="flex items-center gap-2">
          <span className="font-bold text-text">
            Sentinel<span className="text-mint">Sleep</span>
          </span>
          <span>·</span>
          <span>Research prototype. Built at UMKC.</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 justify-center">
          <a
            href="https://github.com/reddy-nithin"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text transition-colors"
          >
            GitHub
          </a>
          <span>·</span>
          <span>Research-a-thon 2026 · 1st Place AI/DS Track</span>
          <span>·</span>
          <span className="ss-pill ss-pill-dim">Not a medical device</span>
        </div>
      </div>
    </footer>
  );
}
