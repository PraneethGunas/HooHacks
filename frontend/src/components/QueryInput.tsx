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
  const [query, setQuery] = useState("");
  const canRun = query.trim().length > 0;

  const submit = () => {
    if (!canRun) {
      return;
    }
    onSubmit(query.trim());
  };

  return (
    <section className="min-h-screen w-full grid place-items-center px-4 py-10 sm:px-8 sm:py-12">
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
          PolicyPulse is a multi-agent economic policy simulator that evaluates real-world policy ideas using staged analysis.
          It runs a live pipeline and returns a structured impact report with explainable reasoning and visual flows.
        </p>

        <div className="mt-10 text-sm font-medium text-[var(--accent-gold)]/90">Write a policy prompt to start the simulation.</div>

        <div className="mt-5 rounded-lg border border-white/10 bg-black/20 p-3 text-left">
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
            "mt-5 mx-auto flex w-full max-w-md items-center justify-center gap-2 rounded-lg bg-[#F0EEE8] px-4 py-2.5 text-md text-[#0A0C0F] transition",
            canRun ? "hover:brightness-95" : "cursor-not-allowed opacity-40",
          )}
        >
          <BoltIcon />
          Run analysis
        </button>
      </div>
    </section>
  );
}
