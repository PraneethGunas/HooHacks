"use client";

import LightningRow from "@/components/LightningRow";
import { cn, formatDuration, titleCase, truncate } from "@/lib/utils";
import type { AgentChallenge, PipelineState } from "@/types/pipeline";

interface AgentFeedProps {
  state: PipelineState;
  onViewReport: () => void;
}

const AGENT_PROCESSES: Record<string, string[]> = {
  Labor: ["Pull labor market baselines", "Estimate wage pass-through", "Check employment elasticity", "Draft labor report"],
  Consumer: ["Collect spending panels", "Model demand response", "Estimate inflation pass-through", "Draft consumer report"],
  Business: ["Scan margin exposure", "Model cost absorption", "Estimate hiring adjustment", "Draft business report"],
  Housing: ["Load rent burden data", "Model housing supply links", "Estimate affordability shift", "Draft housing report"],
};

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
  debate,
}: {
  letter: string;
  status: "pending" | "running" | "complete";
  debate?: boolean;
}) {
  return (
    <div
      className={cn(
        "h-7 w-7 rounded-full grid place-items-center text-[11px] border border-white/10",
        debate && "bg-red-900/40 text-red-400",
        !debate && status === "complete" && "bg-green-900/40 text-green-400",
        !debate && status === "running" && "bg-amber-900/40 text-amber-400 animate-pulse",
        !debate && status === "pending" && "bg-white/5 text-white/30",
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
  debate,
}: {
  name: string;
  status: "pending" | "running" | "complete";
  description: string;
  toolCall?: string;
  debate?: boolean;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3 enter-card">
      <Avatar letter={name[0] ?? "?"} status={status} debate={debate} />
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

function SectorCard({
  name,
  status,
  detail,
  toolCallsCount,
  index,
}: {
  name: string;
  status: "pending" | "running" | "complete";
  detail: string;
  toolCallsCount: number;
  index: number;
}) {
  const processes = AGENT_PROCESSES[name] ?? ["Gather evidence", "Run model checks", "Draft report", "Finalize output"];
  const activeStep =
    status === "pending"
      ? -1
      : status === "complete"
        ? processes.length - 1
        : Math.min(toolCallsCount, processes.length - 1);
  const progressPercent =
    status === "pending"
      ? 8
      : status === "complete"
        ? 100
        : Math.min(90, 26 + activeStep * 18 + Math.min(18, toolCallsCount * 4));

  return (
    <div
      className={cn(
        "rounded-xl border border-white/10 glass-card p-3 enter-card",
        status === "complete" && "border-green-500/30",
        status === "running" && "border-amber-500/30 bg-amber-950/10",
      )}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center justify-between">
        <div className="text-sm text-white/85">{name}</div>
        <span className="text-[10px] text-white/45">{status}</span>
      </div>
      <div className="mt-1 min-h-8 text-xs text-white/55">{truncate(detail, 72)}</div>

      <div className="mt-2 text-[11px] text-white/60">
        {status === "running" ? (
          <span className="text-amber-300">Processing: {processes[Math.max(0, activeStep)]}</span>
        ) : status === "complete" ? (
          <span className="text-green-300">Completed: {processes[processes.length - 1]}</span>
        ) : (
          <span className="text-white/45">Waiting to start</span>
        )}
      </div>

      <div className={cn("mt-2 h-[4px] w-full rounded bg-white/10 overflow-hidden progress-track", status === "running" && "progress-running")}>
        <div
          className={cn(
            "h-full rounded transition-[width] duration-500",
            status === "complete" ? "bg-green-400/80" : status === "running" ? "bg-amber-400/80" : "bg-white/20",
          )}
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
}

function challengeText(challenge: AgentChallenge) {
  return [challenge.target_claim.claim, ...challenge.counter_evidence].join(" · ");
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

  const stage3Status: "pending" | "running" | "complete" = state.challenges.length > 0
    ? "complete"
    : allSectorsComplete && state.status === "running"
      ? "running"
      : "pending";

  const stage3bStatus: "pending" | "running" | "complete" =
    state.rebuttals.length > 0 && state.rebuttals.length >= Math.max(1, state.challenges.length)
      ? "complete"
      : state.challenges.length > 0
        ? "running"
        : "pending";

  const stage4Status: "pending" | "running" | "complete" = state.synthesis
    ? "complete"
    : state.status === "running" && state.rebuttals.length > 0
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

        {state.lightningPayments.map((payment, index) => (
          <LightningRow key={`${payment.payment_hash}-${index}`} payment={payment} />
        ))}

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
              />
            );
          })}
        </div>

        <StageLabel status={stage3Status}>Stage 3 - Debate</StageLabel>
        {state.challenges.length === 0 && (
          <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs text-white/45">No challenges yet.</div>
        )}

        <div className="space-y-2">
          {state.challenges.map((challenge, index) => {
            const rebuttal = state.rebuttals.find(
              (item) =>
                item.challenge.target_agent === challenge.target_agent &&
                item.challenge.target_claim.claim === challenge.target_claim.claim,
            );

            return (
              <article
                key={`${challenge.target_agent}-${challenge.target_claim.claim}-${index}`}
                className="debate-enter rounded-lg border border-red-500/25 border-l-2 bg-red-950/10 p-3"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-center gap-2 text-sm text-red-200">
                  <Avatar letter="!" status="running" debate />
                  <span>Debate → {challenge.target_agent}</span>
                  <span className="text-[11px] italic text-red-300/70">{challenge.challenge_type}</span>
                </div>
                <p className="mt-2 text-xs text-red-100/75">{truncate(challengeText(challenge), 200)}</p>

                {rebuttal && (
                  <div className="mt-2 flex items-start gap-2 border-t border-red-500/20 pt-2 text-xs text-white/70">
                    <span
                      className={cn(
                        "rounded-full border px-2 py-0.5 text-[10px]",
                        rebuttal.response === "concede" && "border-red-500/30 bg-red-900/40 text-red-300",
                        rebuttal.response === "defend" && "border-blue-500/30 bg-blue-900/40 text-blue-300",
                        rebuttal.response === "revise" && "border-green-500/30 bg-green-900/40 text-green-300",
                      )}
                    >
                      {rebuttal.response}
                    </span>
                    <div>{rebuttal.revised_claim?.claim ?? rebuttal.original_claim.claim}</div>
                  </div>
                )}
              </article>
            );
          })}
        </div>

        <StageLabel status={stage3bStatus}>Stage 3b - Agent revisions</StageLabel>
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs text-white/65">
          {state.rebuttals.length === 0 ? "No revisions submitted yet." : `${state.rebuttals.length} revision responses posted.`}
        </div>

        <StageLabel status={stage4Status}>Stage 4 - Synthesis</StageLabel>
        <AgentRow
          name="Synthesis agent"
          status={state.synthesis ? "complete" : state.status === "running" ? "running" : "pending"}
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
