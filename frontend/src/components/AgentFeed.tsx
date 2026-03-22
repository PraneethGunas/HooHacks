"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { cn, formatDuration, truncate } from "@/lib/utils";
import type { LightningPaymentEvent, PipelineState, ThinkingStep } from "@/types/pipeline";

/* ═══════════════════════════════════════════════════════════════════════════
   AgentFeed — "Spotlight + Timeline" layout
   Left rail: vertical agent timeline
   Main area: full-width thinking stream for the focused agent
   ═══════════════════════════════════════════════════════════════════════════ */

interface AgentFeedProps {
  state: PipelineState;
  onViewReport: () => void;
}

// ─── Agent identifiers used throughout ────────────────────────────────────
type AgentId = "classifier" | "analyst" | "lightning" | "Labor" | "Housing" | "Consumer" | "Business" | "synthesis";

const AGENT_ORDER: AgentId[] = ["classifier", "analyst", "lightning", "Labor", "Housing", "Consumer", "Business", "synthesis"];

/** Only actual agents shown in the left rail (Lightning is a payment layer, shown separately) */
const RAIL_AGENTS: AgentId[] = ["classifier", "analyst", "Labor", "Housing", "Consumer", "Business", "synthesis"];

const AGENT_META: Record<AgentId, { label: string; icon: string; color: string; description: string }> = {
  classifier:  { label: "Classifier",  icon: "C", color: "sky",    description: "Parsing policy type & parameters" },
  analyst:     { label: "Analyst",     icon: "A", color: "blue",   description: "5-phase data gathering & briefing" },
  lightning:   { label: "Lightning",   icon: "⚡", color: "amber",  description: "L402 premium data payments" },
  Labor:       { label: "Labor",       icon: "L", color: "emerald", description: "Employment, wages & workforce" },
  Housing:     { label: "Housing",     icon: "H", color: "purple", description: "Housing demand, rents & mobility" },
  Consumer:    { label: "Consumer",    icon: "Co", color: "pink",   description: "Prices, purchasing power & spending" },
  Business:    { label: "Business",    icon: "B", color: "orange", description: "Margins, closures & automation" },
  synthesis:   { label: "Synthesis",   icon: "S", color: "rose",   description: "5-phase aggregation & report" },
};

const SYNTHESIS_PHASES = ["Consistency Audit", "Net Household Impact", "Winners & Losers", "Narrative & Timeline", "Analytics Payload"];

// ─── Helpers ──────────────────────────────────────────────────────────────

function getAgentStatus(id: AgentId, state: PipelineState): "pending" | "running" | "complete" {
  switch (id) {
    case "classifier":
      return state.classifier ? "complete" : (state.classifierThinkingSteps.length > 0 || state.status === "running") ? "running" : "pending";
    case "analyst":
      return state.analystComplete ? "complete" : (state.status === "running" && !!state.classifier) ? "running" : "pending";
    case "lightning":
      if (state.lightningPayments.length === 0) {
        // Show running after analyst completes and before sectors start
        if (state.analystComplete && !Object.values(state.sectorAgents).some(a => a.status !== "pending")) return "running";
        return "pending";
      }
      return state.lightningPayments.every(p => p.status === "paid" || p.status === "failed") ? "complete" : "running";
    case "synthesis":
      return state.synthesis ? "complete" : (state.synthesisPhase ? "running" : "pending");
    default: {
      const sa = state.sectorAgents[id];
      return sa?.status ?? "pending";
    }
  }
}

function getActiveAgent(state: PipelineState): AgentId {
  // Stage 0: Classifier running
  if (!state.classifier && state.status === "running") return "classifier";

  // Stage 1: Analyst running
  if (!state.analystComplete && state.classifier && state.status === "running") return "analyst";

  // Stage 3: Synthesis (check before sectors so it wins once synthesis starts)
  if ((state.synthesisPhase || state.synthesisThinkingSteps.length > 0) && !state.synthesis) return "synthesis";

  // Stage 2: Sector agents — pick the one with most recent thinking step
  const sectorIds = ["Labor", "Housing", "Consumer", "Business"] as AgentId[];
  const runningAgents = sectorIds.filter(id => state.sectorAgents[id]?.status === "running");
  if (runningAgents.length > 0) {
    let best = runningAgents[0];
    let bestTs = 0;
    for (const id of runningAgents) {
      const steps = state.sectorAgents[id]?.thinkingSteps ?? [];
      const lastTs = steps.length > 0 ? steps[steps.length - 1].timestamp : 0;
      if (lastTs > bestTs) { best = id; bestTs = lastTs; }
    }
    return best;
  }

  // Lightning: show when payments exist and sectors haven't started yet, or actively paying
  if (state.lightningPayments.length > 0) {
    const sectorsStarted = sectorIds.some(id => state.sectorAgents[id]?.status !== "pending");
    if (!sectorsStarted || state.lightningPayments.some(p => p.status === "paying")) return "lightning";
  }

  // Fallback: show most recently completed stage
  if (state.analystComplete) return "analyst";
  if (state.classifier) return "classifier";
  return "classifier";
}

/** Build a unified thinking stream for any agent */
interface StreamEntry {
  id: string;
  type: "phase" | "tool" | "result" | "reasoning" | "info" | "payment" | "complete";
  content: string;
  detail?: string;
  timestamp: number;
}

function buildStream(agentId: AgentId, state: PipelineState): StreamEntry[] {
  const entries: StreamEntry[] = [];

  switch (agentId) {
    case "classifier": {
      // Show live thinking steps if available
      if (state.classifierThinkingSteps.length > 0) {
        for (const step of state.classifierThinkingSteps) {
          entries.push({
            id: `cls-ts-${step.id}`,
            type: step.stepType === "phase_start" ? "phase"
              : step.stepType === "tool_call" ? "tool"
              : step.stepType === "tool_result" ? "result"
              : step.stepType === "phase_complete" ? "complete"
              : "reasoning",
            content: step.content,
            detail: step.tool,
            timestamp: step.timestamp,
          });
        }
      }
      // Append classifier result data once complete
      if (state.classifier) {
        entries.push({ id: "cls-type", type: "info", content: `Policy type: ${state.classifier.task_type}`, timestamp: Date.now() });
        const params = state.classifier.policy_params;
        if (params) {
          Object.entries(params).forEach(([k, v]) => {
            if (v) entries.push({ id: `cls-p-${k}`, type: "result", content: `${k}: ${v}`, timestamp: Date.now() });
          });
        }
      }
      break;
    }

    case "analyst": {
      // Prefer rich thinking steps if available, fall back to basic tool calls
      if (state.analystThinkingSteps.length > 0) {
        for (const step of state.analystThinkingSteps) {
          entries.push({
            id: `an-ts-${step.id}`,
            type: step.stepType === "phase_start" ? "phase"
              : step.stepType === "tool_call" ? "tool"
              : step.stepType === "tool_result" ? "result"
              : step.stepType === "phase_complete" ? "complete"
              : "reasoning",
            content: step.content,
            detail: step.tool,
            timestamp: step.timestamp,
          });
        }
      } else {
        for (let i = 0; i < state.analystToolCalls.length; i++) {
          const tc = state.analystToolCalls[i];
          entries.push({
            id: `an-tc-${i}`,
            type: "tool",
            content: tc.tool,
            detail: tc.query,
            timestamp: Date.now(),
          });
        }
      }
      if (state.analystComplete) {
        const ac = state.analystComplete as any;
        entries.push({
          id: "an-done",
          type: "complete",
          content: `Briefing assembled — ${ac.tool_calls_made ?? ac.tools_called ?? state.analystToolCalls.length} tool calls, ${ac.sources_found ?? state.analystToolCalls.length} sources`,
          timestamp: Date.now(),
        });
      }
      break;
    }

    case "lightning": {
      for (let i = 0; i < state.lightningPayments.length; i++) {
        const p = state.lightningPayments[i];
        entries.push({
          id: `ln-${i}-${p.status}`,
          type: "payment",
          content: p.service,
          detail: p.status === "paying"
            ? `Paying invoice... ${p.invoice_amount_sats} sats`
            : p.status === "paid"
              ? `Paid ${p.invoice_amount_sats} sats (${Math.round(p.duration_ms)}ms)`
              : `Failed: ${(p as any).error ?? "unknown"}`,
          timestamp: Date.now(),
        });
      }
      break;
    }

    case "synthesis": {
      // Prefer rich thinking steps if available
      if (state.synthesisThinkingSteps.length > 0) {
        for (const step of state.synthesisThinkingSteps) {
          entries.push({
            id: `syn-ts-${step.id}`,
            type: step.stepType === "phase_start" ? "phase"
              : step.stepType === "tool_call" ? "tool"
              : step.stepType === "tool_result" ? "result"
              : step.stepType === "phase_complete" ? "complete"
              : "reasoning",
            content: step.content,
            detail: step.tool,
            timestamp: step.timestamp,
          });
        }
      } else if (state.synthesisPhase) {
        // Fallback to phase-only events
        for (let i = 1; i <= state.synthesisPhase.phase; i++) {
          const isComplete = i < state.synthesisPhase.phase || (i === state.synthesisPhase.phase && state.synthesisPhase.status === "complete");
          entries.push({
            id: `syn-ph-${i}-${isComplete ? "done" : "run"}`,
            type: isComplete ? "complete" : "phase",
            content: `Phase ${i}: ${SYNTHESIS_PHASES[i - 1] ?? "Processing"}`,
            detail: isComplete ? "Complete" : "Running...",
            timestamp: Date.now(),
          });
        }
      }
      if (state.synthesis) {
        entries.push({ id: "syn-done", type: "complete", content: "Synthesis report assembled", timestamp: Date.now() });
      }
      break;
    }

    default: {
      // Sector agents
      const sa = state.sectorAgents[agentId];
      if (!sa) break;
      for (const step of sa.thinkingSteps) {
        entries.push({
          id: `${agentId}-ts-${step.id}`,
          type: step.stepType === "phase_start" ? "phase"
            : step.stepType === "tool_call" ? "tool"
            : step.stepType === "tool_result" ? "result"
            : step.stepType === "phase_complete" ? "complete"
            : "reasoning",
          content: step.content,
          detail: step.tool,
          timestamp: step.timestamp,
        });
      }
      // If no thinking steps but has tool calls, show those
      if (sa.thinkingSteps.length === 0 && sa.toolCalls.length > 0) {
        for (let i = 0; i < sa.toolCalls.length; i++) {
          const tc = sa.toolCalls[i];
          entries.push({
            id: `${agentId}-tc-${i}`,
            type: "tool",
            content: tc.tool,
            detail: tc.query,
            timestamp: Date.now(),
          });
        }
      }
      if (sa.status === "complete" && sa.thinkingSteps.length === 0) {
        entries.push({ id: `${agentId}-done`, type: "complete", content: `${agentId} analysis complete`, timestamp: Date.now() });
      }
      break;
    }
  }

  return entries;
}

// ─── Timeline Rail ────────────────────────────────────────────────────────

function TimelineNode({
  id,
  status,
  focused,
  onClick,
  isLast,
}: {
  id: AgentId;
  status: "pending" | "running" | "complete";
  focused: boolean;
  onClick: () => void;
  isLast: boolean;
}) {
  const meta = AGENT_META[id];
  const colorMap: Record<string, { dot: string; ring: string; text: string; bg: string }> = {
    sky:     { dot: "bg-sky-400",     ring: "ring-sky-400/40",     text: "text-sky-300",     bg: "bg-sky-500/10" },
    blue:    { dot: "bg-blue-400",    ring: "ring-blue-400/40",    text: "text-blue-300",    bg: "bg-blue-500/10" },
    amber:   { dot: "bg-amber-400",   ring: "ring-amber-400/40",   text: "text-amber-300",   bg: "bg-amber-500/10" },
    emerald: { dot: "bg-emerald-400", ring: "ring-emerald-400/40", text: "text-emerald-300", bg: "bg-emerald-500/10" },
    purple:  { dot: "bg-purple-400",  ring: "ring-purple-400/40",  text: "text-purple-300",  bg: "bg-purple-500/10" },
    pink:    { dot: "bg-pink-400",    ring: "ring-pink-400/40",    text: "text-pink-300",    bg: "bg-pink-500/10" },
    orange:  { dot: "bg-orange-400",  ring: "ring-orange-400/40",  text: "text-orange-300",  bg: "bg-orange-500/10" },
    rose:    { dot: "bg-rose-400",    ring: "ring-rose-400/40",    text: "text-rose-300",    bg: "bg-rose-500/10" },
  };
  const c = colorMap[meta.color] ?? colorMap.blue;

  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex items-center gap-3 w-full text-left px-4 py-3.5 rounded-xl transition-all duration-200",
        focused ? `${c.bg} border border-white/10` : "hover:bg-white/3 border border-transparent",
      )}
    >
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-6.75 top-12 -bottom-2 w-px bg-white/8" />
      )}

      {/* Dot */}
      <div className={cn(
        "relative shrink-0 h-7 w-7 rounded-full grid place-items-center text-[11px] font-bold transition-all",
        status === "complete" ? `${c.dot} text-black` : "",
        status === "running" ? `${c.dot} text-black animate-pulse ring-2 ${c.ring}` : "",
        status === "pending" ? "bg-white/10 text-white/30" : "",
      )}>
        {status === "complete" ? "✓" : meta.icon}
      </div>

      {/* Label */}
      <span className={cn(
        "text-[14px] font-medium",
        focused ? c.text : status === "pending" ? "text-white/30" : "text-white/70",
      )}>
        {meta.label}
      </span>
    </button>
  );
}

/** Compact Lightning payment badge — sits between Analyst and Sector agents in the rail */
function LightningBadge({
  state,
  focused,
  onClick,
}: {
  state: PipelineState;
  focused: boolean;
  onClick: () => void;
}) {
  const payments = state.lightningPayments;
  const paid = payments.filter(p => p.status === "paid");
  const paying = payments.some(p => p.status === "paying");
  const totalSats = paid.reduce((s, p) => s + p.invoice_amount_sats, 0);
  const lnStatus = getAgentStatus("lightning", state);

  if (lnStatus === "pending" && payments.length === 0) return null;

  return (
    <button
      onClick={onClick}
      className={cn(
        "relative w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-left",
        focused
          ? "bg-amber-500/10 border border-amber-400/20"
          : "hover:bg-white/3 border border-transparent",
      )}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0">
        <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill={paying ? "#F59E0B" : paid.length > 0 ? "#F59E0B" : "#6B7280"} />
      </svg>
      <div className="flex-1 min-w-0">
        <span className={cn("text-[13px] font-medium", paying ? "text-amber-300" : paid.length > 0 ? "text-amber-300/70" : "text-white/35")}>
          L402
        </span>
        {payments.length > 0 && (
          <span className="ml-2 text-[11px] text-amber-300/40 tabular-nums">
            {totalSats} sats
          </span>
        )}
      </div>
      {paying && <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />}
    </button>
  );
}

function TimelineRail({
  state,
  focusedAgent,
  onSelect,
}: {
  state: PipelineState;
  focusedAgent: AgentId;
  onSelect: (id: AgentId) => void;
}) {
  const elapsed = formatDuration(state.elapsedMs);

  return (
    <div className="flex flex-col h-full w-55 shrink-0 border-r border-white/8">
      {/* Header — minimal */}
      <div className="px-4 py-4 border-b border-white/8 flex items-center justify-between">
        <span className="text-[13px] font-semibold text-white/50">Agents</span>
        <div className="flex items-center gap-2">
          {state.status === "running" && <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />}
          <span className="text-[13px] text-white/40 tabular-nums">{elapsed}</span>
        </div>
      </div>

      {/* Agent nodes + Lightning badge */}
      <div className="flex-1 overflow-y-auto py-2 no-scrollbar">
        {RAIL_AGENTS.map((id, i) => {
          const status = getAgentStatus(id, state);

          return (
            <div key={id}>
              <TimelineNode
                id={id}
                status={status}
                focused={focusedAgent === id}
                onClick={() => onSelect(id)}
                isLast={i === RAIL_AGENTS.length - 1}
              />
              {/* Insert Lightning badge after Analyst */}
              {id === "analyst" && (
                <LightningBadge
                  state={state}
                  focused={focusedAgent === "lightning"}
                  onClick={() => onSelect("lightning")}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Spotlight Stream ─────────────────────────────────────────────────────

function StreamIcon({ type }: { type: StreamEntry["type"] }) {
  switch (type) {
    case "phase":    return <span className="text-purple-400 text-sm">▸</span>;
    case "tool":     return <span className="text-sky-400 text-sm">⚙</span>;
    case "result":   return <span className="text-green-400/70 text-sm">↳</span>;
    case "reasoning": return <span className="text-amber-400 text-sm animate-pulse">●</span>;
    case "payment":  return <span className="text-amber-400 text-sm">⚡</span>;
    case "complete": return <span className="text-green-400 text-sm">✔</span>;
    case "info":     return <span className="text-white/40 text-sm">›</span>;
    default:         return <span className="text-white/30 text-sm">·</span>;
  }
}

/** Human-readable descriptions for known tools */
const TOOL_INFO: Record<string, { label: string; source: string; color: string }> = {
  fred_search:            { label: "Search economic data series",       source: "FRED",             color: "sky" },
  fred_get_series:        { label: "Pull time-series data",            source: "FRED",             color: "sky" },
  bls_get_data:           { label: "Employment & wage data",           source: "BLS",              color: "sky" },
  census_query:           { label: "Demographic / housing data",       source: "Census Bureau",    color: "sky" },
  census_housing_query:   { label: "Housing burden data",              source: "Census Bureau",    color: "sky" },
  bea_get_data:           { label: "Economic accounts data",           source: "BEA",              color: "sky" },
  search_academic_papers: { label: "Academic paper search",            source: "Semantic Scholar",  color: "violet" },
  search_openalex:        { label: "Broad academic search",            source: "OpenAlex",         color: "violet" },
  search_cbo_reports:     { label: "Congressional budget analysis",    source: "CBO",              color: "violet" },
  fetch_document_text:    { label: "Fetching full document text",      source: "Web",              color: "blue" },
  web_search_news:        { label: "News & current context",          source: "Tavily",           color: "blue" },
  calculate_elasticity:   { label: "Computing price elasticity",       source: "Compute",          color: "emerald" },
  run_scenario_analysis:  { label: "Running scenario projections",     source: "Compute",          color: "emerald" },
  market_competition_scan:{ label: "Market competition analysis",      source: "Compute",          color: "emerald" },
  sec_10k_scan:           { label: "SEC 10-K filing analysis",         source: "SEC",              color: "orange" },
  llm_chat:               { label: "LLM reasoning",                   source: "LLM",              color: "amber" },
  llm_classify:           { label: "LLM classification",              source: "LLM",              color: "amber" },
  google_adk:             { label: "Policy classification",            source: "Google ADK",       color: "amber" },
  keyword_match:          { label: "Keyword scenario matching",        source: "Local",            color: "white" },
};

const SOURCE_COLORS: Record<string, { badge: string; border: string; bg: string }> = {
  sky:     { badge: "bg-sky-500/20 text-sky-300 border-sky-500/30",         border: "border-sky-500/25",    bg: "bg-sky-500/[0.05]" },
  violet:  { badge: "bg-violet-500/20 text-violet-300 border-violet-500/30", border: "border-violet-500/25", bg: "bg-violet-500/[0.05]" },
  blue:    { badge: "bg-blue-500/20 text-blue-300 border-blue-500/30",       border: "border-blue-500/25",   bg: "bg-blue-500/[0.05]" },
  emerald: { badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", border: "border-emerald-500/25", bg: "bg-emerald-500/[0.05]" },
  orange:  { badge: "bg-orange-500/20 text-orange-300 border-orange-500/30", border: "border-orange-500/25", bg: "bg-orange-500/[0.05]" },
  amber:   { badge: "bg-amber-500/20 text-amber-300 border-amber-500/30",   border: "border-amber-500/25",  bg: "bg-amber-500/[0.05]" },
  white:   { badge: "bg-white/10 text-white/60 border-white/20",            border: "border-white/10",      bg: "bg-white/2" },
};

/** Parse tool args from content string */
function parseToolCall(content: string): { name: string; args: Record<string, string> | string | null } {
  // Handle "Calling tool_name(k=v, k=v)" format
  const callingMatch = content.match(/^Calling\s+(\w+)\((.+)\)$/);
  if (callingMatch) {
    const pairs: Record<string, string> = {};
    callingMatch[2].split(/,\s*/).forEach(pair => {
      const eq = pair.indexOf("=");
      if (eq > 0) pairs[pair.slice(0, eq).trim()] = pair.slice(eq + 1).trim();
      else pairs[pair.trim()] = "";
    });
    return { name: callingMatch[1], args: Object.keys(pairs).length > 0 ? pairs : null };
  }
  // Handle "tool_name({json})" or "tool_name(args)" format
  const parenIdx = content.indexOf("(");
  if (parenIdx > 0) {
    const name = content.slice(0, parenIdx).trim();
    const rawArgs = content.slice(parenIdx + 1, -1).trim();
    // Try JSON parse
    try {
      const parsed = JSON.parse(rawArgs);
      if (typeof parsed === "object" && parsed !== null) {
        const pairs: Record<string, string> = {};
        for (const [k, v] of Object.entries(parsed)) {
          pairs[k] = typeof v === "string" ? v : JSON.stringify(v);
        }
        return { name, args: pairs };
      }
    } catch { /* not JSON */ }
    // Try key=value format
    if (rawArgs.includes("=")) {
      const pairs: Record<string, string> = {};
      rawArgs.split(/,\s*/).forEach(pair => {
        const eq = pair.indexOf("=");
        if (eq > 0) pairs[pair.slice(0, eq).trim()] = pair.slice(eq + 1).trim();
      });
      return { name, args: Object.keys(pairs).length > 0 ? pairs : rawArgs };
    }
    return { name, args: rawArgs || null };
  }
  return { name: content, args: null };
}

/** Tool call card — visually distinct with source badge + structured args */
function ToolCallCard({ entry, isLatest }: { entry: StreamEntry; isLatest: boolean }) {
  const parsed = parseToolCall(entry.content);
  const toolKey = entry.detail || parsed.name;
  const info = TOOL_INFO[toolKey];
  const sc = SOURCE_COLORS[info?.color ?? "white"] ?? SOURCE_COLORS.white;

  return (
    <div className={cn(
      "mx-6 my-2 rounded-xl border transition-all duration-300 spotlight-entry overflow-hidden",
      isLatest ? `${sc.border} ${sc.bg} shadow-sm` : "border-white/6 bg-white/2",
    )}>
      {/* Header row: source badge + tool name + pulse */}
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="text-sky-400/70 text-sm">⚙</span>
        {info && (
          <span className={cn("text-[10px] font-semibold uppercase tracking-wider rounded px-2 py-0.5 border", sc.badge)}>
            {info.source}
          </span>
        )}
        <span className="text-[14px] font-semibold text-white/80" style={{ fontFamily: "var(--font-mono), monospace" }}>
          {toolKey}
        </span>
        {isLatest && <span className="ml-auto h-2 w-2 rounded-full bg-sky-400 animate-pulse" />}
      </div>

      {/* Human-readable description */}
      {info && (
        <div className="px-4 -mt-1 pb-1">
          <span className="text-[13px] text-white/35">{info.label}</span>
        </div>
      )}

      {/* Structured arguments */}
      {parsed.args && (
        <div className="px-4 pb-3 pt-1">
          {typeof parsed.args === "object" ? (
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {Object.entries(parsed.args).map(([k, v]) => (
                <div key={k} className="flex items-baseline gap-1.5 text-[13px]" style={{ fontFamily: "var(--font-mono), monospace" }}>
                  <span className="text-white/25">{k}:</span>
                  <span className="text-white/50">{truncate(String(v), 60)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[13px] text-white/40 leading-relaxed" style={{ fontFamily: "var(--font-mono), monospace" }}>
              {truncate(parsed.args, 120)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Tool result card — paired with tool call above it */
function ToolResultCard({ entry }: { entry: StreamEntry }) {
  // Parse "tool_name → result" format
  const arrowIdx = entry.content.indexOf(" → ");
  const resultText = arrowIdx > 0 ? entry.content.slice(arrowIdx + 3) : entry.content;
  const toolKey = arrowIdx > 0 ? entry.content.slice(0, arrowIdx) : entry.detail;
  const info = toolKey ? TOOL_INFO[toolKey] : null;
  const sc = SOURCE_COLORS[info?.color ?? "white"] ?? SOURCE_COLORS.white;

  return (
    <div className={cn("mx-6 -mt-0.5 mb-2 rounded-b-xl border border-t-0 spotlight-entry", "border-white/6 bg-white/1.5")}>
      <div className="flex items-start gap-3 px-4 py-2.5">
        <span className="text-green-400/60 text-sm mt-0.5">✓</span>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] text-white/45 leading-relaxed" style={{ fontFamily: "var(--font-mono), monospace" }}>
            {truncate(resultText, 200)}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Lightning payment card — with "Agent autonomously paid" annotation */
function PaymentCard({ entry, isLatest }: { entry: StreamEntry; isLatest: boolean }) {
  const isPaying = entry.detail?.startsWith("Paying");
  const isPaid = entry.detail?.startsWith("Paid");
  // Extract sats amount from detail string
  const satsMatch = entry.detail?.match(/(\d+)\s*sats/);
  const satsAmount = satsMatch ? parseInt(satsMatch[1], 10) : 0;
  const usdEstimate = satsAmount > 0 ? (satsAmount * 0.0003).toFixed(4) : null;

  return (
    <div className={cn(
      "mx-6 my-2 rounded-xl border transition-all duration-300 spotlight-entry overflow-hidden",
      isPaying
        ? "border-amber-500/30 bg-amber-500/6"
        : isPaid
          ? "border-green-500/20 bg-green-500/4"
          : "border-red-500/20 bg-red-500/4",
    )}>
      <div className="flex items-center gap-3 px-4 py-3">
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0">
          <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill={isPaying ? "#F59E0B" : isPaid ? "#4ADE80" : "#F87171"} />
        </svg>
        <span className={cn(
          "text-[14px] font-semibold tracking-wide",
          isPaying ? "text-amber-300" : isPaid ? "text-green-300" : "text-red-300",
        )} style={{ fontFamily: "var(--font-mono), monospace" }}>
          {entry.content}
        </span>
        {isPaying && <span className="ml-auto h-2 w-2 rounded-full bg-amber-400 animate-pulse" />}
        {isPaid && <span className="ml-auto text-green-400 text-sm">✔</span>}
      </div>
      {entry.detail && (
        <div className="px-4 pb-2.5 -mt-0.5">
          <div className={cn(
            "text-[13px] leading-relaxed",
            isPaying ? "text-amber-300/50" : isPaid ? "text-green-300/40" : "text-red-300/50",
          )} style={{ fontFamily: "var(--font-mono), monospace" }}>
            {entry.detail}
          </div>
        </div>
      )}
      {/* Autonomous payment annotation */}
      {isPaid && satsAmount > 0 && (
        <div className="px-4 pb-3 -mt-0.5">
          <div className="text-[12px] text-green-300/50 leading-relaxed italic">
            Agent autonomously paid {satsAmount} sats{usdEstimate ? ` (~$${usdEstimate})` : ""} for premium data via L402
          </div>
        </div>
      )}
    </div>
  );
}

function SpotlightEntry({ entry, isLatest }: { entry: StreamEntry; isLatest: boolean }) {
  // Tool calls, results, and payments get card treatment
  if (entry.type === "tool") return <ToolCallCard entry={entry} isLatest={isLatest} />;
  if (entry.type === "result") return <ToolResultCard entry={entry} />;
  if (entry.type === "payment") return <PaymentCard entry={entry} isLatest={isLatest} />;

  return (
    <div className={cn(
      "flex gap-4 py-3 px-6 transition-colors duration-500 spotlight-entry",
      isLatest && "bg-white/3",
      entry.type === "phase" && "mt-4 first:mt-0",
    )}>
      <span className="shrink-0 mt-1.5 w-5 text-center">
        <StreamIcon type={entry.type} />
      </span>
      <div className="flex-1 min-w-0">
        <div className={cn(
          "text-[15px] leading-relaxed",
          entry.type === "phase" ? "text-purple-300 font-semibold text-[16px]" :
          entry.type === "reasoning" ? "text-white/70" :
          entry.type === "complete" ? "text-green-300/90 font-medium" :
          "text-white/60",
        )}>
          {entry.content}
        </div>
        {entry.detail && (
          <div className="text-[13px] mt-1 text-white/30" style={{ fontFamily: "var(--font-mono), monospace" }}>
            {entry.detail}
          </div>
        )}
      </div>
    </div>
  );
}

function EmptySpotlight({ agentId, status }: { agentId: AgentId; status: "pending" | "running" | "complete" }) {
  const meta = AGENT_META[agentId];
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-12">
      <div className="text-4xl mb-4 opacity-15">{meta.icon}</div>
      <div className="text-white/30 text-lg font-medium mb-2">{meta.label}</div>
      <div className="text-white/15 text-base max-w-sm leading-relaxed">
        {status === "pending"
          ? `Waiting for upstream agents...`
          : status === "running"
            ? "Processing — events will appear here..."
            : meta.description}
      </div>
    </div>
  );
}

function SpotlightPanel({
  agentId,
  state,
  onViewReport,
}: {
  agentId: AgentId;
  state: PipelineState;
  onViewReport: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(0);
  const meta = AGENT_META[agentId];
  const status = getAgentStatus(agentId, state);
  const stream = useMemo(() => buildStream(agentId, state), [agentId, state]);

  // Auto-scroll on new entries
  useEffect(() => {
    if (stream.length > prevLengthRef.current && scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
    prevLengthRef.current = stream.length;
  }, [stream.length]);

  const colorMap: Record<string, string> = {
    sky: "border-sky-500/30", blue: "border-blue-500/30", amber: "border-amber-500/30",
    emerald: "border-emerald-500/30", purple: "border-purple-500/30", pink: "border-pink-500/30",
    orange: "border-orange-500/30", rose: "border-rose-500/30",
  };
  const textColorMap: Record<string, string> = {
    sky: "text-sky-300", blue: "text-blue-300", amber: "text-amber-300",
    emerald: "text-emerald-300", purple: "text-purple-300", pink: "text-pink-300",
    orange: "text-orange-300", rose: "text-rose-300",
  };

  const borderColor = colorMap[meta.color] ?? "border-white/10";
  const textColor = textColorMap[meta.color] ?? "text-white/70";

  // Sector agent metadata
  const sectorData = (["Labor", "Housing", "Consumer", "Business"] as const).includes(agentId as any)
    ? state.sectorAgents[agentId]
    : null;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Spotlight header */}
      <div className={cn("shrink-0 border-b px-6 py-5", borderColor)}>
        <div className="flex items-center gap-4">
          <div className={cn("text-2xl font-semibold", textColor)}>{meta.label}</div>
          <span className={cn(
            "inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-medium border",
            status === "complete" ? "border-green-500/30 text-green-400 bg-green-500/10" :
            status === "running" ? `${borderColor} ${textColor} bg-white/3` :
            "border-white/10 text-white/30 bg-white/2",
          )}>
            {status === "running" && <span className="h-2 w-2 rounded-full bg-current animate-pulse" />}
            {status}
          </span>
          {sectorData?.agentMode && (
            <span className={cn(
              "rounded-full px-3 py-1 text-[11px] font-medium border",
              sectorData.agentMode === "agentic"
                ? "border-purple-400/30 bg-purple-500/15 text-purple-300"
                : "border-white/10 bg-white/5 text-white/40",
            )}>
              {sectorData.agentMode === "agentic" ? "Multi-phase" : "Single-shot"}
            </span>
          )}
          <span className="ml-auto text-[13px] text-white/25 tabular-nums">
            {stream.length} events
          </span>
        </div>
        <div className="text-[14px] text-white/35 mt-2">{meta.description}</div>

        {/* Synthesis phase bar */}
        {agentId === "synthesis" && state.synthesisPhase && (
          <div className="mt-3 flex gap-1.5">
            {SYNTHESIS_PHASES.map((step, i) => (
              <div
                key={step}
                className={cn(
                  "group relative flex-1 h-2 rounded-full transition-colors duration-300",
                  i + 1 < state.synthesisPhase!.phase ? "bg-rose-400/80" :
                  i + 1 === state.synthesisPhase!.phase
                    ? state.synthesisPhase!.status === "complete" ? "bg-rose-400/80" : "bg-rose-400/50 animate-pulse"
                    : "bg-white/10",
                )}
              >
                <div className="pointer-events-none absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black/95 px-2 py-0.5 text-[9px] text-white/70 opacity-0 transition-opacity group-hover:opacity-100 z-10">
                  {step}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Sector agent phase bar */}
        {sectorData?.agentMode === "agentic" && sectorData.currentPhase && (
          <div className="mt-3 flex gap-1.5">
            {Array.from({ length: 5 }, (_, i) => {
              const phaseNum = parseInt(sectorData.currentPhase ?? "0", 10);
              return (
                <div
                  key={i}
                  className={cn(
                    "flex-1 h-2 rounded-full transition-colors duration-300",
                    i + 1 < phaseNum ? "bg-purple-400/80" :
                    i + 1 === phaseNum
                      ? sectorData.status === "complete" ? "bg-purple-400/80" : "bg-purple-400/50 animate-pulse"
                      : "bg-white/10",
                  )}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Stream area */}
      {stream.length === 0 ? (
        <EmptySpotlight agentId={agentId} status={status} />
      ) : (
        <div ref={scrollRef} className="flex-1 overflow-y-auto py-4 no-scrollbar">
          {stream.map((entry, i) => (
            <SpotlightEntry key={entry.id} entry={entry} isLatest={i === stream.length - 1 && status === "running"} />
          ))}

          {/* Cursor when agent is running */}
          {status === "running" && (
            <div className="flex gap-4 py-3 px-6">
              <span className="shrink-0 mt-1.5 w-5 text-center">
                <span className={cn("inline-block h-2.5 w-2.5 rounded-full animate-pulse", `bg-${meta.color}-400`)} />
              </span>
              <span className="text-[15px] text-white/25 italic">thinking...</span>
            </div>
          )}
        </div>
      )}

      {/* Lightning payment summary bar */}
      {agentId === "lightning" && state.lightningPayments.length > 0 && (
        <div className="shrink-0 border-t border-amber-500/20 bg-amber-950/10 px-6 py-3">
          <div className="flex items-center gap-4 text-[13px]">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0">
              <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="#F59E0B" />
            </svg>
            <span className="text-amber-200/80 font-medium">
              {state.lightningPayments.filter(p => p.status === "paid").length} paid
            </span>
            <span className="text-amber-300/50">
              {state.lightningPayments.filter(p => p.status === "paid").reduce((s, p) => s + p.invoice_amount_sats, 0)} sats total
            </span>
            {state.lightningPayments.some(p => p.status === "paying") && (
              <span className="flex items-center gap-1.5 text-amber-400 ml-auto">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                paying...
              </span>
            )}
          </div>
        </div>
      )}

      {/* View report CTA */}
      {state.synthesis && (
        <div className="shrink-0 border-t border-white/8 px-6 py-4">
          <button
            onClick={onViewReport}
            className="w-full rounded-xl border border-amber-400/30 bg-amber-500/90 px-4 py-3 text-base font-medium text-black transition hover:brightness-95"
          >
            View Full Report
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Export ───────────────────────────────────────────────────────────

export default function AgentFeed({ state, onViewReport }: AgentFeedProps) {
  const [pinnedAgent, setPinnedAgent] = useState<AgentId | null>(null);
  const autoAgent = getActiveAgent(state);
  const focusedAgent = pinnedAgent ?? autoAgent;

  // Auto-unpin when pipeline moves to a new stage
  const prevAutoRef = useRef(autoAgent);
  useEffect(() => {
    if (autoAgent !== prevAutoRef.current) {
      // If the user pinned and the pipeline moved on, auto-unpin
      if (pinnedAgent && getAgentStatus(pinnedAgent, state) === "complete") {
        setPinnedAgent(null);
      }
      prevAutoRef.current = autoAgent;
    }
  }, [autoAgent, pinnedAgent, state]);

  const handleSelect = useCallback((id: AgentId) => {
    setPinnedAgent(id === autoAgent ? null : id);
  }, [autoAgent]);

  return (
    <section className="h-[calc(100vh-56px)] flex">
      <TimelineRail
        state={state}
        focusedAgent={focusedAgent}
        onSelect={handleSelect}
      />
      <SpotlightPanel
        agentId={focusedAgent}
        state={state}
        onViewReport={onViewReport}
      />
    </section>
  );
}
