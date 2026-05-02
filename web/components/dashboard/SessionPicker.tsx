"use client";

import { useRouter } from "next/navigation";
import { ChevronDown } from "lucide-react";
import type { Session } from "@/lib/data";
import { formatDate } from "@/lib/time";

interface SessionPickerProps {
  sessions: Session[];
  currentId: number;
}

export function SessionPicker({ sessions, currentId }: SessionPickerProps) {
  const router = useRouter();

  return (
    <div className="relative">
      <select
        value={currentId}
        onChange={(e) => router.push(`/dashboard/night/${e.target.value}`)}
        className="appearance-none bg-surface border border-border rounded-lg px-4 py-2 pr-8 text-sm font-medium text-text hover:border-border-bright transition-colors cursor-pointer focus:outline-none focus:border-mint"
      >
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {formatDate(s.started_at)} (#{s.id})
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim pointer-events-none" />
    </div>
  );
}
