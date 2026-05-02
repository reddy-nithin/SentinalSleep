"use client";

import Link from "next/link";
import { Moon } from "lucide-react";

export default function NightDetailError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[400px] gap-6 text-center">
      <div className="w-14 h-14 rounded-full bg-surface-alt border border-border flex items-center justify-center">
        <Moon className="w-6 h-6 text-text-dim" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-text mb-2">Session not found</h2>
        <p className="text-sm text-text-dim max-w-xs">
          This session doesn&apos;t exist in the dataset yet. Only recorded sessions can be viewed.
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="px-4 py-2 rounded-full bg-surface-alt hover:bg-border text-sm text-text-dim transition-colors"
        >
          Try again
        </button>
        <Link
          href="/dashboard"
          className="px-4 py-2 rounded-full bg-mint/15 hover:bg-mint/25 text-mint text-sm font-medium transition-colors"
        >
          Back to overview
        </Link>
      </div>
    </div>
  );
}
