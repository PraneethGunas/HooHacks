"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  onMockSubmit?: (query: string) => void;
}

function BoltIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
      <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="currentColor" />
    </svg>
  );
}

const EXAMPLE_QUERIES = [
  "How will a 25% tariff on Chinese electronics affect small businesses?",
  "What happens if the federal minimum wage goes to $20/hr?",
  "How will the new H1B visa restrictions affect tech workers?",
  "What if student loan interest rates are capped at 3%?",
];

export default function QueryInput({ onSubmit, onMockSubmit }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const trimmed = query.trim();
  const canRun = trimmed.length >= 10;

  const submit = () => {
    if (!canRun) return;
    onSubmit(trimmed);
  };

  return (
    <section className="relative min-h-screen w-full grid place-items-center px-4 py-10 sm:px-8 sm:py-12">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[8%] bottom-[8%] h-44 w-44 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(168,85,247,0.16) 0%, rgba(168,85,247,0.06) 45%, rgba(168,85,247,0) 75%)",
          filter: "blur(10px)",
        }}
      />
      <div className="pointer-events-none absolute left-6 top-8 hidden rounded-full border border-[var(--fun-cyan)]/40 bg-[var(--fun-cyan)]/10 px-3 py-1 text-xs text-[var(--fun-cyan)] md:block">
        Simulation Mode
      </div>
      <div className="pointer-events-none absolute right-6 top-8 hidden rounded-full border border-[var(--fun-pink)]/35 bg-[var(--fun-pink)]/10 px-3 py-1 text-xs text-[var(--fun-pink)] md:block">
        7 Agents • &gt;$50B Focus
      </div>
      <div className="mx-auto w-full max-w-3xl enter-card text-center">
        <div className="mb-8 flex items-center justify-center gap-3 text-base font-medium text-white/80">
          <span className="text-[var(--accent-gold)]">
            <BoltIcon size={32} />
          </span>
          <span className="tracking-tight text-[40px] leading-none font-semibold text-[var(--text-primary)]" style={{ fontFamily: "var(--font-wordmark), serif" }}>
            Policy<span className="logo-pulse-word">Pulse</span>
          </span>
        </div>

        {/* Value proposition — one clear line */}
        <p className="text-center text-[18px] leading-relaxed text-white/50 mb-10">
          Describe any policy. AI agents will research its real-world impact.
        </p>

        {/* Input card */}
        <div className="rounded-2xl border border-white/12 glass-card p-4 shadow-[0_8px_30px_rgba(0,0,0,0.28)]">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && canRun) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="What policy do you want to understand?"
            rows={3}
            className="w-full resize-none bg-transparent text-[17px] leading-relaxed font-medium text-[var(--text-primary)] outline-none placeholder:text-white/25"
          />

          {/* Submit row */}
          <div className="flex items-center justify-between mt-2 pt-3 border-t border-white/6">
            <span className="text-[12px] text-white/20">
              {trimmed.length > 0 && `${trimmed.length} chars`}
            </span>
            <div className="flex items-center gap-2">
              {onMockSubmit && (
                <button
                  onClick={() => onMockSubmit(trimmed || EXAMPLE_QUERIES[0])}
                  className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-[14px] font-medium text-white/50 transition hover:border-white/20 hover:text-white/70"
                >
                  Demo
                </button>
              )}
              <button
                onClick={submit}
                disabled={!canRun}
                className={cn(
                  "flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#ffe4a6] via-[#ffd06e] to-[#ffb870] px-5 py-2.5 text-[15px] font-semibold text-[#101319] transition",
                  canRun
                    ? "hover:shadow-[0_4px_12px_rgba(245,158,11,0.4)] hover:brightness-105"
                    : "cursor-not-allowed opacity-30",
                )}
              >
                <BoltIcon size={16} />
                Analyze
              </button>
            </div>
          </div>
        </div>

        {/* Example queries */}
        <div className="mt-8">
          <p className="text-[12px] text-white/25 mb-3 text-center uppercase tracking-wider">Try an example</p>
          <div className="flex flex-col gap-2">
            {EXAMPLE_QUERIES.map((eq) => (
              <button
                key={eq}
                onClick={() => { setQuery(eq); }}
                className="group text-left rounded-xl border border-white/6 bg-white/[0.02] px-4 py-3 text-[14px] text-white/40 transition hover:border-white/15 hover:bg-white/[0.04] hover:text-white/70"
              >
                <span className="text-white/15 group-hover:text-[var(--accent-gold)] transition mr-2">&rarr;</span>
                {eq}
              </button>
            ))}
          </div>
        </div>

        {/* Subtle credibility line */}
        <p className="text-center text-[11px] text-white/15 mt-8">
          Powered by 7 specialized AI agents &middot; Real-time data from FRED, BLS &amp; Census &middot; L402 Lightning micropayments
        </p>
      </div>
    </section>
  );
}
