"use client";

import { useState } from "react";
import AgentFeed from "@/components/AgentFeed";
import QueryInput from "@/components/QueryInput";
import ResultsPanel from "@/components/ResultsPanel";
import { cn } from "@/lib/utils";
import { usePipeline } from "@/hooks/usePipeline";

type Screen = "query" | "pipeline" | "results";

function BoltIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="#F59E0B" />
    </svg>
  );
}

export default function AppShell() {
  const [screen, setScreen] = useState<Screen>("query");
  const { state, startPipeline, startMockPipeline } = usePipeline();

  const handleSubmit = (query: string) => {
    startPipeline(query);
    setScreen("pipeline");
  };

  const handleMockSubmit = (query: string) => {
    startMockPipeline(query);
    setScreen("pipeline");
  };

  return (
    <main className="min-h-screen text-foreground">
      {screen !== "query" && (
        <nav className="sticky top-0 z-30 border-b border-white/10 bg-[#0a0c0f]/95 backdrop-blur px-4 sm:px-6 py-3 flex items-center gap-3">
          <BoltIcon />
          <span className="text-sm tracking-tight" style={{ fontFamily: "var(--font-wordmark), serif" }}>
            Policy<span className="logo-pulse-word">Pulse</span>
          </span>

          <div className="ml-auto flex items-center gap-1.5 rounded-full border border-white/10 bg-white/3 p-1 text-xs">
            <button
              onClick={() => setScreen("query")}
              className={cn(
                "rounded-full px-3 py-1 text-white/60 transition",
                "hover:text-white/80",
              )}
            >
              Query
            </button>
            <button
              onClick={() => setScreen("pipeline")}
              className={cn(
                "rounded-full px-3 py-1 text-white/60 transition",
                screen === "pipeline" && "bg-white/10 text-white/95",
              )}
            >
              Pipeline
            </button>
            <button
              onClick={() => setScreen("results")}
              disabled={!state.synthesis}
              className={cn(
                "rounded-full px-3 py-1 transition",
                screen === "results" && "bg-white/10 text-white/95",
                state.synthesis ? "text-white/60 hover:text-white/80" : "text-white/20 cursor-not-allowed",
              )}
            >
              Results
            </button>
          </div>
        </nav>
      )}

      <div className={cn(
        "transition-all duration-500",
        screen === "query" ? "opacity-100 scale-100" : "opacity-0 scale-95 absolute inset-0 pointer-events-none",
      )}>
        {screen === "query" && <QueryInput onSubmit={handleSubmit} onMockSubmit={handleMockSubmit} />}
      </div>
      <div className={cn(
        "transition-all duration-500",
        screen === "pipeline" ? "opacity-100 translate-x-0" : screen === "results" ? "opacity-0 -translate-x-4 absolute inset-0 pointer-events-none" : "opacity-0 translate-x-4 absolute inset-0 pointer-events-none",
      )}>
        {(screen === "pipeline" || state.status === "running") && <AgentFeed state={state} onViewReport={() => setScreen("results")} />}
      </div>
      <div className={cn(
        "transition-all duration-500",
        screen === "results" ? "opacity-100 translate-x-0" : "opacity-0 translate-x-4 absolute inset-0 pointer-events-none",
      )}>
        {screen === "results" && state.synthesis && <ResultsPanel report={state.synthesis} />}
      </div>
    </main>
  );
}
