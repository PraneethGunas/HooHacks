"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onSubmit: (query: string) => void;
}

function BoltIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="currentColor" />
    </svg>
  );
}

export default function QueryInput({ onSubmit }: QueryInputProps) {
  const [query, setQuery] = useState(
    "Implement a 30% corporate tax increase on tech companies with revenue over $50B",
  );
  const canRun = query.trim().length > 0;

  const submit = () => {
    if (!canRun) {
      return;
    }
    onSubmit(query.trim());
  };

  return (
    <section className="relative min-h-screen w-full grid place-items-center px-4 py-10 sm:px-8 sm:py-12">
      <div className="pointer-events-none absolute left-6 top-8 hidden rounded-full border border-[var(--fun-cyan)]/40 bg-[var(--fun-cyan)]/10 px-3 py-1 text-xs text-[var(--fun-cyan)] md:block">
        Simulation Mode
      </div>
      <div className="pointer-events-none absolute right-6 top-8 hidden rounded-full border border-[var(--fun-pink)]/35 bg-[var(--fun-pink)]/10 px-3 py-1 text-xs text-[var(--fun-pink)] md:block">
        7 Agents • &gt;$50B Focus
      </div>
      <div className="mx-auto w-full max-w-3xl enter-card text-center">
        <div className="mb-8 flex items-center justify-center gap-3 text-base font-medium text-white/80">
          <span className="text-[var(--accent-gold)]">
            <BoltIcon />
          </span>
          <span className="tracking-tight text-[40px] leading-none font-semibold text-[var(--text-primary)]" style={{ fontFamily: "var(--font-wordmark), serif" }}>
            PolicyPulse
          </span>
        </div>

        <p className="text-base leading-7 font-medium text-white/80">
          PolicyPulse runs a multi-agent economic simulation: classifier, analyst, parallel sector agents,
          and a 5-phase synthesis engine. Watch the agents reason through impacts in real time.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-2 text-[11px]">
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">Stage 0: Classifier</span>
          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-sky-300">Stage 1-2: Parallel Agent Analysis</span>
          <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-rose-300">Stage 3: Synthesis</span>
        </div>

        <div className="mt-5 rounded-2xl border border-white/15 glass-card p-3 text-left shadow-[0_8px_30px_rgba(0,0,0,0.28)]">
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Describe a policy proposal..."
            className="h-36 w-full resize-none bg-transparent text-base leading-7 font-medium text-[var(--text-primary)] outline-none placeholder:text-white/35"
          />
        </div>

        <button
          onClick={submit}
          disabled={!canRun}
          className={cn(
            "mt-5 mx-auto flex w-full max-w-md items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#ffe4a6] via-[#ffd06e] to-[#ffb870] px-4 py-2.5 text-md text-[#101319] shadow-[0_8px_20px_rgba(245,158,11,0.25)] transition",
            canRun ? "hover:brightness-95" : "cursor-not-allowed opacity-40",
          )}
        >
          <BoltIcon />
          Launch workflow simulation
        </button>
      </div>
    </section>
  );
}
