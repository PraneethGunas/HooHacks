"use client";

import SankeyDiagram from "@/components/SankeyDiagram";
import { cn, confidenceOrder, formatDuration } from "@/lib/utils";
import type { CausalClaim, SynthesisReport } from "@/types/pipeline";

interface ResultsPanelProps {
  report: SynthesisReport;
}

function directionLabel(direction: SynthesisReport["impact_dashboard"][number]["direction"]) {
  if (direction === "increase") return "Increase";
  if (direction === "decline") return "Decline";
  if (direction === "distortionary") return "Distortionary";
  return "Mixed";
}

function statusChip(status: SynthesisReport["impact_dashboard"][number]["status"]) {
  if (status === "works") {
    return "border-emerald-500/30 bg-emerald-950/40 text-emerald-300";
  }
  if (status === "doesnt_work") {
    return "border-red-500/35 bg-red-950/40 text-red-300";
  }
  return "border-amber-500/35 bg-amber-950/40 text-amber-300";
}

function statusText(status: SynthesisReport["impact_dashboard"][number]["status"]) {
  if (status === "works") return "Works";
  if (status === "doesnt_work") return "Doesn't work";
  return "Trade-off";
}

function survivedChipClass(value: SynthesisReport["impact_dashboard"][number]["survived_challenge"]) {
  if (value === "yes") return "border-green-500/25 bg-green-900/30 text-green-300";
  if (value === "no") return "border-red-500/25 bg-red-900/30 text-red-300";
  return "border-amber-500/25 bg-amber-900/30 text-amber-300";
}

function survivedLabel(value: SynthesisReport["impact_dashboard"][number]["survived_challenge"]) {
  if (value === "yes") return "Survived challenge";
  if (value === "no") return "Did not survive";
  return "Partially survived";
}

function SectorPill({ sector }: { sector: SynthesisReport["impact_dashboard"][number]["sectors"][number] }) {
  const className =
    sector === "labor"
      ? "border-sky-500/30 bg-sky-950/30 text-sky-300"
      : sector === "housing"
        ? "border-fuchsia-500/30 bg-fuchsia-950/30 text-fuchsia-300"
        : sector === "consumer"
          ? "border-amber-500/30 bg-amber-950/30 text-amber-300"
          : sector === "business"
            ? "border-indigo-500/30 bg-indigo-950/30 text-indigo-300"
            : sector === "fiscal"
              ? "border-emerald-500/30 bg-emerald-950/30 text-emerald-300"
              : "border-white/15 bg-white/5 text-white/70";

  return <span className={cn("rounded-full border px-2 py-0.5 text-[10px]", className)}>{sector}</span>;
}

function ImpactSummaryBars({ report }: { report: SynthesisReport }) {
  const total = Math.max(1, report.impact_dashboard.length);
  const works = report.impact_dashboard.filter((row) => row.status === "works").length;
  const doesntWork = report.impact_dashboard.filter((row) => row.status === "doesnt_work").length;
  const tradeoff = report.impact_dashboard.filter((row) => row.status === "tradeoff").length;

  const bars = [
    { label: "Works", value: works, className: "bg-emerald-400/80" },
    { label: "Doesn't work", value: doesntWork, className: "bg-red-400/80" },
    { label: "Trade-off", value: tradeoff, className: "bg-amber-400/80" },
  ];

  return (
    <div className="w-full rounded-xl border border-white/10 bg-white/[0.03] p-3">
      <div className="mb-2 text-xs text-white/70">Signal split across dashboard rows</div>
      <div className="space-y-2">
        {bars.map((bar) => {
          const pct = Math.round((bar.value / total) * 100);
          return (
            <div key={bar.label}>
              <div className="mb-1 flex items-center justify-between text-[11px] text-white/65">
                <span>{bar.label}</span>
                <span>
                  {bar.value} / {total} ({pct}%)
                </span>
              </div>
              <div className="h-2 rounded bg-white/10">
                <div className={cn("h-full rounded transition-[width] duration-700", bar.className)} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConfidencePill({ confidence }: { confidence: CausalClaim["confidence"] }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 text-[10px]",
        confidence === "EMPIRICAL" && "bg-green-900/40 text-green-400 border-green-500/20",
        confidence === "THEORETICAL" && "bg-blue-900/40 text-blue-400 border-blue-500/20",
        confidence === "SPECULATIVE" && "bg-amber-900/40 text-amber-400 border-amber-500/20",
      )}
    >
      {confidence.toLowerCase()}
    </span>
  );
}

function FallbackFlowChart() {
  const rows = [
    { label: "Policy floor adjustment", value: 94, color: "bg-amber-500/70" },
    { label: "Labor wage transmission", value: 84, color: "bg-blue-500/70" },
    { label: "Consumer spend uplift", value: 68, color: "bg-teal-500/70" },
    { label: "Margin compression", value: 49, color: "bg-red-500/60" },
    { label: "Net macro impact", value: 61, color: "bg-green-500/70" },
  ];

  return (
    <div className="rounded-xl border border-white/10 bg-[var(--bg-surface)] p-4">
      <div className="mb-3 text-sm text-white/80">Sankey data unavailable - pipeline may still be computing.</div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex items-center justify-between text-[11px] text-white/65">
              <span>{row.label}</span>
              <span>{row.value}</span>
            </div>
            <div className="h-2 rounded bg-white/10">
              <div className={cn("h-full rounded", row.color)} style={{ width: `${row.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function sourceStyle(source: string) {
  const premium = /(premium|lightning|paywall|l2|pro)/i.test(source);
  if (premium) {
    return {
      className: "border-amber-500/30 bg-amber-950/40 text-amber-300",
      label: `⚡ ${source}`,
    };
  }

  return {
    className: "border-teal-500/20 bg-teal-950/30 text-teal-300",
    label: source,
  };
}

export default function ResultsPanel({ report }: ResultsPanelProps) {
  const claims = [...report.unified_impact.key_claims].sort(
    (a, b) => confidenceOrder(a.confidence) - confidenceOrder(b.confidence),
  );

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 sm:py-7 space-y-4">
      <article className="rounded-2xl border border-white/10 glass-card p-4 enter-card shadow-[0_10px_36px_rgba(0,0,0,0.28)]">
        <h2 className="text-xl text-white/95 tracking-tight">{report.policy_summary.title}</h2>

        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-white/70">
            {report.policy_summary.scope}
          </span>
          {report.policy_summary.affected_sectors.map((sector) => (
            <span key={sector} className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-white/70">
              {sector}
            </span>
          ))}
        </div>

        <p className="mt-3 text-sm leading-6 text-white/75">{report.unified_impact.summary}</p>
        <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-[var(--fun-cyan)]/35 bg-[var(--fun-cyan)]/10 px-3 py-1 text-[11px] text-[var(--fun-cyan)]">
          <span className="sparkle-dot h-1.5 w-1.5 rounded-full bg-[var(--fun-cyan)]" />
          Simulation output from 7-agent workflow
        </div>
      </article>

      <section className="grid gap-3 sm:grid-cols-3">
        {report.unified_impact.headline_stats.slice(0, 3).map((stat) => (
          <article key={stat.label} className="rounded-xl border border-white/10 glass-card p-3 enter-card">
            <div className="text-[11px] text-white/50">{stat.label}</div>
            <div className="mt-1 text-[22px] font-medium tracking-tight text-white/95">{stat.value}</div>
            {stat.sub && <div className="text-[10px] text-white/40">{stat.sub}</div>}
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-white/10 bg-[var(--bg-surface)]/90 p-4 enter-card shadow-[0_8px_24px_rgba(0,0,0,0.24)]">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h3 className="text-sm text-white/85">Impact Dashboard</h3>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-white/60">
            Focus: what works, what does not, and by sector
          </span>
        </div>

        <div className="space-y-3">
          <ImpactSummaryBars report={report} />

          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="min-w-full divide-y divide-white/10 text-left">
              <thead className="bg-white/[0.03] text-[11px] uppercase tracking-wide text-white/55">
                <tr>
                  <th className="px-4 py-2.5">Category</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Direction</th>
                  <th className="px-4 py-2.5">Magnitude</th>
                  <th className="px-4 py-2.5">Confidence</th>
                  <th className="px-4 py-2.5">Challenge</th>
                  <th className="px-4 py-2.5">Sectors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-[13px]">
                {report.impact_dashboard.map((row) => (
                  <tr key={row.category} className="bg-transparent align-top">
                    <td className="px-4 py-3 text-white/90">{row.category}</td>
                    <td className="px-4 py-3">
                      <span className={cn("rounded-full border px-2 py-0.5 text-[10px] whitespace-nowrap", statusChip(row.status))}>
                        {statusText(row.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white/70">{directionLabel(row.direction)}</td>
                    <td className="px-4 py-3 text-white/85">{row.magnitude}</td>
                    <td className="px-4 py-3">
                      <ConfidencePill confidence={row.confidence} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("rounded-full border px-2 py-0.5 text-[10px] whitespace-nowrap", survivedChipClass(row.survived_challenge))}>
                        {survivedLabel(row.survived_challenge)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {row.sectors.map((sector) => (
                          <SectorPill key={`${row.category}-${sector}`} sector={sector} />
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-[var(--bg-surface)]/85 p-4 enter-card shadow-[0_8px_24px_rgba(0,0,0,0.24)]">
        <div className="mb-3 text-sm text-white/75">Economic flow map</div>
        {report.sankey_data?.nodes?.length >= 2 ? <SankeyDiagram data={report.sankey_data} /> : <FallbackFlowChart />}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm text-white/75">Key claims</h3>
        {claims.map((claim, index) => (
          <article
            key={`${claim.claim}-${index}`}
            className={cn(
              "rounded-lg border bg-[var(--bg-surface)] p-3 enter-card",
              claim.confidence === "EMPIRICAL" && "border-green-500/30",
              claim.confidence === "THEORETICAL" && "border-blue-500/20",
              claim.confidence === "SPECULATIVE" && "border-amber-500/20 border-dashed",
            )}
          >
            <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px]">
              <ConfidencePill confidence={claim.confidence} />
              {claim.survived_debate && (
                <span className="rounded-full border border-green-500/25 bg-green-900/30 px-2 py-0.5 text-green-300">
                  survived debate
                </span>
              )}
              <span className="text-white/40">model claim</span>
            </div>

            <p className="text-[13px] leading-5 text-white/85">{claim.claim}</p>
            <p className="mt-2 border-l-2 border-white/10 pl-2 text-[11px] text-white/55">{claim.mechanism}</p>

            <div className="mt-2 flex flex-wrap gap-1.5">
              {claim.evidence.map((source) => {
                const style = sourceStyle(source);
                return (
                  <span
                    key={`${claim.claim}-${source}`}
                    className={cn(
                      "rounded-full border px-2 py-0.5 text-[10px]",
                      style.className,
                    )}
                  >
                    {style.label}
                  </span>
                );
              })}
            </div>
          </article>
        ))}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm text-white/75">Active disagreements</h3>
        {report.disagreements.map((item) => (
          <article key={item.topic} className="rounded-lg border border-white/10 bg-[var(--bg-surface)] p-3 enter-card">
            <div className="mb-2 flex items-center gap-2 text-sm text-white/85">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              <span>{item.topic}</span>
            </div>
            <div className="space-y-1">
              {Object.entries(item.positions).map(([agent, text]) => (
                <div key={`${item.topic}-${agent}`} className="text-xs">
                  <span className="text-white/45">{agent}</span>
                  <span className="text-white/65">: {text}</span>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-white/40">unresolved - model-dependent</p>
          </article>
        ))}
      </section>

      <footer className="pt-2 text-[11px] text-white/45">
        {report.metadata.total_tool_calls} tool calls · {report.metadata.total_llm_calls} LLM calls · {formatDuration(report.metadata.duration_ms)} · {report.metadata.lightning_payments.length} ⚡ payments
      </footer>
    </section>
  );
}
