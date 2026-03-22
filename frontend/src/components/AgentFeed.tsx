"use client";

import { useEffect, useRef, useState } from "react";
import { cn, formatDuration, titleCase, truncate } from "@/lib/utils";
import type { LightningPaymentEvent, PipelineState, ThinkingStep } from "@/types/pipeline";

interface AgentFeedProps {
  state: PipelineState;
  onViewReport: () => void;
}

// Single-shot agents: 4 generic steps
const SINGLE_SHOT_PROCESSES: Record<string, string[]> = {
  Labor: ["Pull labor market baselines", "Estimate wage pass-through", "Check employment elasticity", "Draft labor report"],
  Business: ["Scan margin exposure", "Model cost absorption", "Estimate hiring adjustment", "Draft business report"],
};

// Agentic agents: 5 real LangGraph phases
const AGENTIC_PROCESSES: Record<string, string[]> = {
  Housing: [
    "Identify transmission pathways",
    "Gather housing market baseline",
    "Estimate impact magnitudes",
    "Distributional & temporal analysis",
    "Build affordability scorecard",
  ],
  Consumer: [
    "Identify price shock entry points",
    "Estimate pass-through rates",
    "Geographic & behavioral analysis",
    "Net purchasing power calculation",
    "Build consumer impact scorecard",
  ],
};

function getProcesses(name: string, agentMode: "agentic" | "single_shot" | null): string[] {
  if (agentMode === "agentic" && AGENTIC_PROCESSES[name]) return AGENTIC_PROCESSES[name];
  if (SINGLE_SHOT_PROCESSES[name]) return SINGLE_SHOT_PROCESSES[name];
  if (AGENTIC_PROCESSES[name]) return AGENTIC_PROCESSES[name];
  return ["Gather evidence", "Run model checks", "Draft report", "Finalize output"];
}

function StageLabel({
  children,
  status,
}: {
  children: string;
  status: "pending" | "running" | "complete";
}) {
  const lightClass =
    status === "complete"
      ? "bg-green-400 shadow-[0_0_10px_rgba(74,222,128,0.7)]"
      : status === "running"
        ? "bg-sky-400 animate-pulse shadow-[0_0_12px_rgba(56,189,248,0.85)]"
        : "bg-amber-400/80 shadow-[0_0_8px_rgba(251,191,36,0.5)]";

  return (
    <div className="text-[10px] font-medium text-white/30 tracking-widest uppercase mb-2 mt-4 flex items-center gap-2">
      <span className={cn("inline-block h-1.5 w-1.5 rounded-full", lightClass)} />
      {children}
    </div>
  );
}

function Avatar({
  letter,
  status,
}: {
  letter: string;
  status: "pending" | "running" | "complete";
}) {
  return (
    <div
      className={cn(
        "h-7 w-7 rounded-full grid place-items-center text-[11px] border border-white/10",
        status === "complete" && "bg-green-900/40 text-green-400",
        status === "running" && "bg-amber-900/40 text-amber-400 animate-pulse",
        status === "pending" && "bg-white/5 text-white/30",
      )}
    >
      {letter}
    </div>
  );
}

function AgentRow({
  name,
  status,
  description,
  toolCall,
}: {
  name: string;
  status: "pending" | "running" | "complete";
  description: string;
  toolCall?: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3 enter-card">
      <Avatar letter={name[0] ?? "?"} status={status} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium">{name}</div>
          <span className="text-[10px] rounded border border-white/10 px-1.5 py-0.5 text-white/60 capitalize">{status}</span>
        </div>
        <div className="text-xs text-white/55">{description}</div>
        {toolCall && (
          <div className="mt-1 text-[11px] text-white/50" style={{ fontFamily: "var(--font-mono), monospace" }}>
            {truncate(toolCall, 80)}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentModeBadge({ mode }: { mode: "agentic" | "single_shot" | null }) {
  if (!mode) return null;
  const isAgentic = mode === "agentic";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-1.5 py-[1px] text-[9px] font-medium leading-tight",
        isAgentic
          ? "border border-purple-400/30 bg-purple-500/15 text-purple-300"
          : "border border-white/10 bg-white/5 text-white/40",
      )}
    >
      <span className={cn("inline-block h-1.5 w-1.5 rounded-full", isAgentic ? "bg-purple-400" : "bg-white/30")} />
      {isAgentic ? "Multi-phase" : "Single-shot"}
    </span>
  );
}

// Icon for each thinking step type
function ThinkingIcon({ type }: { type: ThinkingStep["stepType"] }) {
  switch (type) {
    case "phase_start": return <span className="text-purple-400">▸</span>;
    case "tool_call": return <span className="text-sky-400">⚡</span>;
    case "tool_result": return <span className="text-green-400">✓</span>;
    case "reasoning": return <span className="text-amber-400 animate-pulse">●</span>;
    case "reasoning_chunk": return <span className="text-amber-300">↳</span>;
    case "phase_complete": return <span className="text-green-400">✔</span>;
    default: return <span className="text-white/30">·</span>;
  }
}

function ThinkingFeed({ steps, isRunning }: { steps: ThinkingStep[]; isRunning: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps.length]);

  if (steps.length === 0) return null;

  return (
    <div ref={scrollRef} className="mt-2 max-h-[180px] overflow-y-auto rounded-lg bg-black/30 px-2.5 py-2 no-scrollbar">
      {steps.map((step) => (
        <div
          key={step.id}
          className={cn(
            "flex gap-1.5 py-[2px] text-[11px] leading-relaxed enter-fade",
            step.stepType === "phase_start" && "mt-1 first:mt-0",
          )}
        >
          <span className="mt-px flex-shrink-0 w-3 text-center"><ThinkingIcon type={step.stepType} /></span>
          <span
            className={cn(
              "flex-1 break-words",
              step.stepType === "phase_start" ? "text-purple-300/90 font-medium" :
              step.stepType === "phase_complete" ? "text-green-300/80" :
              step.stepType === "tool_call" ? "text-sky-300/80" :
              step.stepType === "tool_result" ? "text-white/40" :
              step.stepType === "reasoning_chunk" ? "text-white/50 italic" :
              "text-white/55",
            )}
            style={{ fontFamily: step.stepType === "tool_call" || step.stepType === "tool_result" ? "var(--font-mono), monospace" : undefined }}
          >
            {step.content}
          </span>
        </div>
      ))}
      {isRunning && (
        <div className="flex gap-1.5 py-[2px] text-[11px]">
          <span className="mt-px flex-shrink-0 w-3 text-center">
            <span className="inline-block animate-pulse text-purple-400">●</span>
          </span>
          <span className="text-white/30 italic">thinking...</span>
        </div>
      )}
    </div>
  );
}

function SectorCard({
  name,
  status,
  detail,
  toolCallsCount,
  index,
  agentMode,
  currentPhase,
  phaseLabel,
  thinkingSteps,
}: {
  name: string;
  status: "pending" | "running" | "complete";
  detail: string;
  toolCallsCount: number;
  index: number;
  agentMode: "agentic" | "single_shot" | null;
  currentPhase: string | null;
  phaseLabel: string | null;
  thinkingSteps: ThinkingStep[];
}) {
  const [expanded, setExpanded] = useState(true);
  const isAgentic = agentMode === "agentic";
  const processes = getProcesses(name, agentMode);
  const totalSteps = processes.length;

  const activeStep =
    status === "pending"
      ? -1
      : status === "complete"
        ? totalSteps - 1
        : isAgentic && currentPhase
          ? Math.min(parseInt(currentPhase, 10) - 1, totalSteps - 1)
          : Math.min(toolCallsCount, totalSteps - 1);

  const progressPercent =
    status === "pending"
      ? 5
      : status === "complete"
        ? 100
        : isAgentic && currentPhase
          ? Math.min(95, (parseInt(currentPhase, 10) / totalSteps) * 100)
          : Math.min(90, 26 + activeStep * 18 + Math.min(18, toolCallsCount * 4));

  const runningLabel = isAgentic && phaseLabel
    ? phaseLabel
    : processes[Math.max(0, activeStep)];

  const hasThinking = thinkingSteps.length > 0;

  return (
    <div
      className={cn(
        "rounded-xl border glass-card enter-card transition-all duration-300",
        status === "pending" && "border-white/10 p-3",
        status === "complete" && isAgentic && "border-purple-500/30 p-3",
        status === "complete" && !isAgentic && "border-green-500/30 p-3",
        status === "running" && isAgentic && "border-purple-500/40 bg-purple-950/10 p-3",
        status === "running" && !isAgentic && "border-amber-500/30 bg-amber-950/10 p-3",
      )}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-sm text-white/85">{name}</div>
          <AgentModeBadge mode={agentMode} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-white/45">
            {status === "running" && isAgentic && currentPhase
              ? `phase ${currentPhase}/${totalSteps}`
              : status}
          </span>
          {hasThinking && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] text-white/30 hover:text-white/60 transition-colors"
            >
              {expanded ? "▾" : "▸"}
            </button>
          )}
        </div>
      </div>

      {/* Phase step indicators */}
      {isAgentic && status !== "pending" && (
        <div className="mt-2 flex gap-1">
          {processes.map((step, i) => (
            <div
              key={step}
              className={cn(
                "group relative flex-1 h-1.5 rounded-full transition-colors duration-300",
                i <= activeStep
                  ? status === "complete" ? "bg-purple-400/80" : "bg-purple-400/60"
                  : "bg-white/10",
                i === activeStep && status === "running" && "animate-pulse",
              )}
            >
              <div className="pointer-events-none absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black/90 px-1.5 py-0.5 text-[9px] text-white/70 opacity-0 transition-opacity group-hover:opacity-100">
                {step}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Current status label */}
      <div className={cn("text-[11px] text-white/60", isAgentic && status !== "pending" ? "mt-1.5" : "mt-2")}>
        {status === "running" ? (
          <span className={isAgentic ? "text-purple-300" : "text-amber-300"}>
            {isAgentic && currentPhase ? `Phase ${currentPhase}: ` : "Processing: "}
            {runningLabel}
          </span>
        ) : status === "complete" ? (
          <span className={isAgentic ? "text-purple-300" : "text-green-300"}>
            {isAgentic
              ? `All ${totalSteps} phases complete · ${thinkingSteps.filter(s => s.stepType === "tool_call").length} tool calls`
              : `Completed: ${processes[totalSteps - 1]}`}
          </span>
        ) : (
          <span className="text-white/45">Waiting to start</span>
        )}
      </div>

      {/* Thinking feed — the core UI for agentic agents */}
      {isAgentic && expanded && hasThinking && (
        <ThinkingFeed steps={thinkingSteps} isRunning={status === "running"} />
      )}

      {/* Single-shot agents get the smooth progress bar */}
      {!isAgentic && (
        <div className={cn("mt-2 h-[4px] w-full rounded bg-white/10 overflow-hidden progress-track", status === "running" && "progress-running")}>
          <div
            className={cn(
              "h-full rounded transition-[width] duration-500",
              status === "complete" ? "bg-green-400/80" : status === "running" ? "bg-amber-400/80" : "bg-white/20",
            )}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}
    </div>
  );
}

function LightningLog({ payments }: { payments: LightningPaymentEvent["data"][] }) {
  const totalSats = payments
    .filter((p) => p.status === "paid")
    .reduce((sum, p) => sum + p.invoice_amount_sats, 0);

  const paidCount = payments.filter((p) => p.status === "paid").length;
  const isPaying = payments.some((p) => p.status === "paying");

  return (
    <div className="my-3 rounded-xl border border-amber-500/20 bg-amber-950/15 enter-card">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-3 py-2.5">
        <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" className="flex-shrink-0">
          <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="#F59E0B" />
        </svg>
        <span className="text-xs font-medium text-amber-200/90">Lightning L402 Payments</span>
        <span className="ml-auto flex items-center gap-2 text-[10px] text-amber-300/70">
          {isPaying && (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              paying
            </span>
          )}
          {paidCount > 0 && <span>{paidCount} paid · {totalSats} sats</span>}
        </span>
      </div>

      {/* Payment entries */}
      <div className="border-t border-amber-500/10 px-3 py-1.5">
        {payments.map((payment, i) => (
          <div
            key={`${payment.payment_hash}-${i}`}
            className={cn(
              "flex items-center gap-2 py-1.5 text-[11px]",
              i > 0 && "border-t border-amber-500/5",
            )}
          >
            <span className={cn(
              "h-1.5 w-1.5 rounded-full flex-shrink-0",
              payment.status === "paid" && "bg-amber-400",
              payment.status === "paying" && "bg-amber-400 animate-pulse",
              payment.status === "failed" && "bg-red-400",
            )} />
            <span className="flex-1 text-amber-200/70 truncate" style={{ fontFamily: "var(--font-mono), monospace" }}>
              {payment.service}
            </span>
            <span className="text-amber-300/60">{payment.invoice_amount_sats} sats</span>
            {payment.duration_ms > 0 && (
              <span className="text-amber-200/40">{Math.round(payment.duration_ms)}ms</span>
            )}
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[9px] font-medium",
                payment.status === "paid" && "bg-amber-500/20 text-amber-300",
                payment.status === "paying" && "bg-amber-500/10 text-amber-400 animate-pulse",
                payment.status === "failed" && "bg-red-500/20 text-red-300",
              )}
            >
              {payment.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AgentFeed({ state, onViewReport }: AgentFeedProps) {
  const elapsed = formatDuration(state.elapsedMs);

  const classifierSummary = state.classifier
    ? `task_type: ${state.classifier.task_type} · scope: ${state.classifier.policy_params.scope ?? "unknown"}`
    : "waiting for classifier...";

  const analystTool = state.analystToolCalls[state.analystToolCalls.length - 1];
  const analystToolText = analystTool ? `${analystTool.tool}("${analystTool.query}")` : undefined;

  const sectorAgents = Object.entries(state.sectorAgents);
  const allSectorsComplete = sectorAgents.length > 0 && sectorAgents.every(([, data]) => data.status === "complete");
  const anySectorRunning = sectorAgents.some(([, data]) => data.status === "running");

  const stage0Status: "pending" | "running" | "complete" = state.classifier
    ? "complete"
    : state.status === "running"
      ? "running"
      : "pending";

  const stage1Status: "pending" | "running" | "complete" = state.analystComplete
    ? "complete"
    : state.status === "running" && !!state.classifier
      ? "running"
      : "pending";

  const stage2Status: "pending" | "running" | "complete" = allSectorsComplete
    ? "complete"
    : anySectorRunning
      ? "running"
      : "pending";

  const stage3Status: "pending" | "running" | "complete" = state.synthesis
    ? "complete"
    : state.status === "running" && allSectorsComplete
      ? "running"
      : "pending";

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-4 sm:px-6 sm:py-6">
      <header className="sticky top-[56px] z-20 mb-4 flex items-center gap-3 rounded-xl border border-white/10 bg-[var(--bg-surface)]/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm tracking-tight text-white/90 truncate">{state.query || "Policy run"}</h1>
        <span className="hidden rounded-full border border-[var(--fun-cyan)]/40 bg-[var(--fun-cyan)]/10 px-2 py-0.5 text-[10px] text-[var(--fun-cyan)] sm:inline">Workflow Replay</span>
        <span className="ml-auto inline-flex items-center gap-2 text-xs text-white/55">
          <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
          live
        </span>
        <span className="text-xs text-white/45">{elapsed}</span>
      </header>

      <div className="rounded-2xl border border-white/10 bg-[var(--bg-surface)]/80 p-4 shadow-[0_12px_36px_rgba(0,0,0,0.32)]">
        <StageLabel status={stage0Status}>Stage 0 - Classifier</StageLabel>
        <AgentRow
          name="Classifier"
          status={state.classifier ? "complete" : state.status === "running" ? "running" : "pending"}
          description={classifierSummary}
        />

        <StageLabel status={stage1Status}>Stage 1 - Analyst</StageLabel>
        <AgentRow
          name="Analyst agent"
          status={state.analystComplete ? "complete" : state.status === "running" ? "running" : "pending"}
          description={
            state.analystComplete
              ? `${state.analystComplete.tool_calls_made} tool calls · ${state.analystComplete.sources_found} sources`
              : "Collecting baseline evidence and structured context"
          }
          toolCall={analystToolText}
        />

        {state.lightningPayments.length > 0 && (
          <LightningLog payments={state.lightningPayments} />
        )}

        <StageLabel status={stage2Status}>Stage 2 - Sector agents</StageLabel>
        <div className="grid gap-2 sm:grid-cols-2">
          {sectorAgents.map(([agent, data], index) => {
            const lastTool = data.toolCalls[data.toolCalls.length - 1];
            const detail = lastTool
              ? `${lastTool.tool}("${lastTool.query}")`
              : data.status === "complete"
                ? "Report synthesized"
                : data.status === "running"
                  ? "Running analysis"
                  : "Pending";

            return (
              <SectorCard
                key={agent}
                name={agent}
                status={data.status}
                detail={detail}
                toolCallsCount={data.toolCalls.length}
                index={index}
                agentMode={data.agentMode}
                currentPhase={data.currentPhase}
                phaseLabel={data.phaseLabel}
                thinkingSteps={data.thinkingSteps}
              />
            );
          })}
        </div>

        <StageLabel status={stage3Status}>Stage 3 - Synthesis</StageLabel>
        <AgentRow
          name="Synthesis agent"
          status={state.synthesis ? "complete" : state.status === "running" && allSectorsComplete ? "running" : "pending"}
          description={state.synthesis ? "Unified report ready" : "Building final synthesis report"}
        />

        {state.synthesis && (
          <div className="mt-3 flex justify-end">
            <button
              onClick={onViewReport}
              className="rounded-lg border border-amber-400/30 bg-amber-500/90 px-3 py-1.5 text-xs font-medium text-black transition hover:brightness-95"
            >
              View report
            </button>
          </div>
        )}

        {state.error && (
          <div className="mt-3 rounded-lg border border-red-500/30 bg-red-950/30 p-3 text-xs text-red-200">
            {titleCase(state.error)}
          </div>
        )}
      </div>
    </section>
  );
}
