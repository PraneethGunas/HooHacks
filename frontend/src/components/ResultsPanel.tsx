"use client";

import React, { useState } from "react";
import type { SynthesisReport, Confidence, HeadlineMetric, WaterfallStep, ImpactMatrixCell, CategoryBreakdown, TimelinePhase, WinnerLoserProfile, GeographicRegion } from "@/types/pipeline";
import { cn, formatDuration, titleCase } from "@/lib/utils";

interface ResultsPanelProps {
  report: SynthesisReport;
}

// Helper: map confidence to color
function confidenceColor(conf: Confidence | string): string {
  const normalized = (conf || "").toUpperCase();
  if (normalized === "EMPIRICAL") return "text-green-400";
  if (normalized === "THEORETICAL") return "text-blue-400";
  return "text-amber-400";
}

function confidenceBg(conf: Confidence | string): string {
  const normalized = (conf || "").toUpperCase();
  if (normalized === "EMPIRICAL") return "bg-green-500/20 border-green-500/30";
  if (normalized === "THEORETICAL") return "bg-blue-500/20 border-blue-500/30";
  return "bg-amber-500/20 border-amber-500/30";
}

function confidenceTextColor(conf: Confidence | string): string {
  const normalized = (conf || "").toUpperCase();
  if (normalized === "EMPIRICAL") return "text-green-300";
  if (normalized === "THEORETICAL") return "text-blue-300";
  return "text-amber-300";
}

// Map headline verdict confidence
function verdictColor(conf: Confidence | string): string {
  const normalized = (conf || "").toUpperCase();
  if (normalized === "HIGH" || normalized === "EMPIRICAL") return "bg-green-500/20 border-green-500/40 text-green-300";
  if (normalized === "MEDIUM" || normalized === "THEORETICAL") return "bg-amber-500/20 border-amber-500/40 text-amber-300";
  return "bg-red-500/20 border-red-500/40 text-red-300";
}

// 1. HERO BANNER
function HeroBanner({ report }: { report: SynthesisReport }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-gradient-to-r from-white/5 to-white/[0.02] p-8 mb-8 enter-card">
      <div className="space-y-4">
        <h1 className="text-4xl font-bold text-white">{report.policy.title}</h1>
        <p className="text-lg text-white/70">{report.policy.one_liner}</p>

        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          <div className={cn(
            "rounded-lg border px-4 py-2 font-semibold",
            verdictColor(report.headline.confidence)
          )}>
            {report.headline.verdict}
          </div>
          <p className="text-white/60 flex-1">{report.headline.bottom_line}</p>
        </div>
      </div>
    </section>
  );
}

// 2. HEADLINE METRICS
function HeadlineMetrics({ metrics }: { metrics: HeadlineMetric[] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.1s" }}>
      <h2 className="text-2xl font-bold text-white mb-6">Key Metrics</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
        {metrics.map((metric, idx) => (
          <div
            key={metric.id}
            className="rounded-xl border border-white/10 bg-white/[0.03] p-4 hover:border-white/20 transition-colors"
            style={{ animationDelay: `${0.15 + idx * 0.05}s` }}
          >
            <div className="text-3xl mb-2">{metric.icon}</div>
            <div className="text-sm text-white/60 mb-2">{metric.label}</div>
            <div className="text-2xl font-bold text-white">{metric.value}</div>
            {metric.range && (
              <div className="text-xs text-white/50 mt-1">
                {metric.range.low} → {metric.range.high}
              </div>
            )}
            <div className="flex items-center gap-2 mt-3">
              <span className={metric.direction === "positive" ? "text-green-400" : metric.direction === "negative" ? "text-red-400" : "text-gray-400"}>
                {metric.direction === "positive" ? "↑" : metric.direction === "negative" ? "↓" : "→"}
              </span>
              <span className={cn("text-xs px-2 py-1 rounded border", confidenceBg(metric.confidence), confidenceTextColor(metric.confidence))}>
                {String(metric.confidence).toLowerCase()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// 3. WATERFALL CHART (pure CSS horizontal bars)
function WaterfallChart({ waterfall }: { waterfall: SynthesisReport["waterfall"] }) {
  const maxValue = Math.max(...waterfall.steps.map(s => Math.abs(s.value)), 1);

  const getBarColor = (type: WaterfallStep["type"]) => {
    if (type === "inflow") return "bg-green-500/80";
    if (type === "outflow") return "bg-red-500/80";
    if (type === "net") return "bg-blue-500/80";
    return "bg-gray-500/50";
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.2s" }}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">{waterfall.title}</h2>
        <p className="text-white/60 mt-1">{waterfall.subtitle}</p>
        <p className="text-sm text-white/50 mt-2">Profile: {waterfall.household_profile}</p>
      </div>

      <div className="space-y-6">
        {waterfall.steps.map((step, idx) => {
          const barWidth = Math.abs(step.value) / maxValue * 100;
          const isNegative = step.value < 0;

          return (
            <div key={idx} className="space-y-2" style={{ animationDelay: `${0.25 + idx * 0.08}s` }}>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-semibold text-white">{step.label}</div>
                  <div className="text-xs text-white/50">{step.source_agent}</div>
                </div>
                <div className="text-right">
                  <div className={cn("font-bold", step.value >= 0 ? "text-green-400" : "text-red-400")}>
                    {step.value >= 0 ? "+" : ""}{step.value}
                  </div>
                  <div className="text-xs text-white/50">→ {step.cumulative}</div>
                </div>
              </div>

              <div className="relative h-8 bg-white/5 rounded border border-white/10 overflow-hidden">
                {step.value !== 0 && (
                  <div
                    className={cn("h-full transition-all duration-500", getBarColor(step.type))}
                    style={{
                      width: `${barWidth}%`,
                      marginLeft: isNegative ? "auto" : "0",
                    }}
                  />
                )}
                <div className="absolute inset-0 flex items-center px-3 text-xs text-white/70 font-mono">
                  {step.cumulative}
                </div>
              </div>

              {step.note && <p className="text-xs text-white/60 italic">{step.note}</p>}
            </div>
          );
        })}
      </div>

      <div className="mt-8 pt-6 border-t border-white/10 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <p className="text-white/60 text-sm">Net Monthly Impact</p>
          <p className={cn("text-2xl font-bold", waterfall.net_monthly >= 0 ? "text-green-400" : "text-red-400")}>
            {waterfall.net_monthly >= 0 ? "+" : ""}{waterfall.net_monthly}
          </p>
        </div>
        <div>
          <p className="text-white/60 text-sm">Net Annual Impact</p>
          <p className={cn("text-2xl font-bold", waterfall.net_annual >= 0 ? "text-green-400" : "text-red-400")}>
            {waterfall.net_annual >= 0 ? "+" : ""}{waterfall.net_annual}
          </p>
        </div>
        <div>
          <p className="text-white/60 text-sm">% of Income</p>
          <p className="text-2xl font-bold text-blue-400">{waterfall.pct_of_income.toFixed(2)}%</p>
        </div>
      </div>
    </section>
  );
}

// 4. IMPACT MATRIX
function ImpactMatrix({ impact_matrix }: { impact_matrix: SynthesisReport["impact_matrix"] }) {
  const getVerdictColor = (verdict: string) => {
    if (verdict.includes("better") || verdict.includes("gain")) return "bg-green-500/20 border-green-500/30 text-green-300";
    if (verdict.includes("marginally") || verdict.includes("mixed")) return "bg-amber-500/20 border-amber-500/30 text-amber-300";
    return "bg-red-500/20 border-red-500/30 text-red-300";
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.3s" }}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">{impact_matrix.title}</h2>
        <p className="text-white/60 mt-1">{impact_matrix.subtitle}</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left px-3 py-2 text-white/70 font-semibold">Income</th>
              <th className="text-left px-3 py-2 text-white/70 font-semibold">Geography</th>
              <th className="text-right px-3 py-2 text-white/70 font-semibold">Net Monthly</th>
              <th className="text-right px-3 py-2 text-white/70 font-semibold">% Income</th>
              <th className="text-left px-3 py-2 text-white/70 font-semibold">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {impact_matrix.cells.map((cell, idx) => (
              <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition">
                <td className="px-3 py-3 text-white">{cell.income}</td>
                <td className="px-3 py-3 text-white/70">{cell.geography}</td>
                <td className={cn("px-3 py-3 text-right font-semibold", cell.net_monthly.central >= 0 ? "text-green-400" : "text-red-400")}>
                  {cell.net_monthly.central >= 0 ? "+" : ""}{cell.net_monthly.central}
                </td>
                <td className="px-3 py-3 text-right text-white/70">
                  {cell.pct_of_income.central.toFixed(2)}%
                </td>
                <td className="px-3 py-3">
                  <span className={cn("inline-block px-2 py-1 rounded text-xs border", getVerdictColor(cell.verdict))}>
                    {cell.verdict}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// 5. CATEGORY BREAKDOWN
function CategoryBreakdown({ categories }: { categories: CategoryBreakdown[] }) {
  const maxChange = Math.max(...categories.map(c => Math.abs(c.pct_change.central)), 1);

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.4s" }}>
      <h2 className="text-2xl font-bold text-white mb-6">Spending Impact by Category</h2>

      <div className="space-y-6">
        {categories.map((cat, idx) => {
          const barWidth = Math.abs(cat.pct_change.central) / maxChange * 100;
          const isPositive = cat.pct_change.central >= 0;

          return (
            <div key={idx} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{cat.icon}</span>
                  <div>
                    <div className="font-semibold text-white">{cat.name}</div>
                    <div className="text-xs text-white/50">
                      Budget share: {cat.budget_share_low_income.toFixed(1)}% (low) → {cat.budget_share_high_income.toFixed(1)}% (high)
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={cn("font-bold", isPositive ? "text-green-400" : "text-red-400")}>
                    {isPositive ? "+" : ""}{cat.pct_change.central.toFixed(1)}%
                  </div>
                  <span className={cn("inline-block px-2 py-1 rounded border text-xs mt-1", confidenceBg(cat.confidence), confidenceTextColor(cat.confidence))}>
                    {String(cat.confidence).toLowerCase()}
                  </span>
                </div>
              </div>

              <div className="relative h-6 bg-white/5 rounded border border-white/10 overflow-hidden">
                <div
                  className={cn("h-full transition-all duration-500", isPositive ? "bg-green-500/80" : "bg-red-500/80")}
                  style={{
                    width: `${barWidth}%`,
                    marginLeft: !isPositive ? "auto" : "0",
                  }}
                />
              </div>

              <p className="text-xs text-white/60">{cat.explanation}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// 6. TIMELINE
function Timeline({ timeline }: { timeline: SynthesisReport["timeline"] }) {
  const moodEmoji: Record<string, string> = {
    positive: "😊",
    optimistic: "🙂",
    neutral: "😐",
    cautious: "😟",
    negative: "😞",
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.5s" }}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">{timeline.title}</h2>
        <p className="text-white/60 mt-1">{timeline.subtitle}</p>
        <p className="text-sm text-white/50 mt-2">Profile: {timeline.household_profile}</p>
      </div>

      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500/50 to-transparent" />

        <div className="space-y-6 ml-16">
          {timeline.phases.map((phase, idx) => (
            <div
              key={idx}
              className="relative p-4 rounded-lg border border-white/10 bg-white/[0.03]"
              style={{ animationDelay: `${0.55 + idx * 0.06}s` }}
            >
              <div className="absolute -left-[2.65rem] top-2 w-8 h-8 rounded-full border-2 border-blue-500 bg-slate-900/90" />

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-white">{phase.label}</h3>
                  <span className="text-2xl">{moodEmoji[phase.mood] || "🤔"}</span>
                </div>

                <p className="text-sm text-white/70">
                  Month {phase.period_start}–{phase.period_end}
                </p>

                <div className="text-sm bg-white/5 rounded px-3 py-2 border border-white/10">
                  <p className="text-white/60 text-xs uppercase tracking-wide mb-1">Net Monthly Impact</p>
                  <p className={cn("text-lg font-bold", phase.cumulative_net_monthly.central >= 0 ? "text-green-400" : "text-red-400")}>
                    {phase.cumulative_net_monthly.central >= 0 ? "+" : ""}{phase.cumulative_net_monthly.central}
                  </p>
                </div>

                <div className="space-y-1">
                  {phase.what_happens.map((event, i) => (
                    <p key={i} className="text-sm text-white/70 flex gap-2">
                      <span className="text-blue-400">▸</span> {event}
                    </p>
                  ))}
                </div>

                <p className="text-xs text-white/50 italic">Driver: {phase.dominant_driver}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// 7. WINNERS & LOSERS
function WinnersAndLosers({ winners_losers }: { winners_losers: SynthesisReport["winners_losers"] }) {
  const renderProfiles = (profiles: WinnerLoserProfile[], color: "green" | "amber" | "red") => {
    const bgColor = color === "green" ? "bg-green-500/10 border-green-500/30" : color === "amber" ? "bg-amber-500/10 border-amber-500/30" : "bg-red-500/10 border-red-500/30";
    const iconBg = color === "green" ? "bg-green-500/20" : color === "amber" ? "bg-amber-500/20" : "bg-red-500/20";

    return (
      <div className="space-y-4">
        {profiles.map((profile, idx) => (
          <div key={idx} className={cn("rounded-lg border p-4", bgColor)}>
            <div className="flex gap-3 mb-3">
              <div className={cn("w-10 h-10 rounded-full flex items-center justify-center text-lg", iconBg)}>
                {profile.icon}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-white">{profile.profile}</h4>
                <p className="text-xs text-white/60 mt-1">{profile.why}</p>
              </div>
            </div>

            <div className="space-y-2 mt-3 pt-3 border-t border-white/10">
              <div className="flex justify-between text-sm">
                <span className="text-white/60">Monthly Impact:</span>
                <span className="font-semibold text-white">{profile.net_monthly_range}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-white/60">% of Income:</span>
                <span className="font-semibold text-white">{profile.pct_of_income_range}</span>
              </div>
            </div>

            {profile.caveat && (
              <p className="text-xs text-white/50 italic mt-3 pt-3 border-t border-white/10">{profile.caveat}</p>
            )}

            <span className={cn("inline-block mt-3 px-2 py-1 rounded border text-xs", confidenceBg(profile.confidence), confidenceTextColor(profile.confidence))}>
              {String(profile.confidence).toLowerCase()}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.6s" }}>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">{winners_losers.title}</h2>
        <div className="mt-4 space-y-2">
          <p className="text-white/70">
            <span className="font-semibold">Distribution:</span> {winners_losers.distributional_verdict.progressive_or_regressive}
          </p>
          <p className="text-white/60 text-sm">{winners_losers.distributional_verdict.explanation}</p>
          <p className="text-white/60 text-sm">
            <span className="font-semibold">Geographic:</span> {winners_losers.distributional_verdict.geographic_equity}
          </p>
          <p className="text-white/60 text-sm">
            <span className="font-semibold">Generational:</span> {winners_losers.distributional_verdict.generational_equity}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <h3 className="text-lg font-bold text-green-300 mb-4">Winners 🟢</h3>
          {renderProfiles(winners_losers.winners, "green")}
        </div>
        <div>
          <h3 className="text-lg font-bold text-amber-300 mb-4">Mixed 🟡</h3>
          {renderProfiles(winners_losers.mixed, "amber")}
        </div>
        <div>
          <h3 className="text-lg font-bold text-red-300 mb-4">Losers 🔴</h3>
          {renderProfiles(winners_losers.losers, "red")}
        </div>
      </div>
    </section>
  );
}

// 8. GEOGRAPHIC IMPACT
function GeographicImpact({ geographic_impact }: { geographic_impact: SynthesisReport["geographic_impact"] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.7s" }}>
      <h2 className="text-2xl font-bold text-white mb-6">{geographic_impact.title}</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {geographic_impact.regions.map((region, idx) => {
          const accentColor =
            region.color === "green" ? "border-green-500/40 bg-green-500/10" :
            region.color === "amber" ? "border-amber-500/40 bg-amber-500/10" :
            "border-red-500/40 bg-red-500/10";

          const textColor =
            region.color === "green" ? "text-green-300" :
            region.color === "amber" ? "text-amber-300" :
            "text-red-300";

          return (
            <div key={region.id} className={cn("rounded-xl border p-6", accentColor)}>
              <h3 className={cn("text-lg font-bold mb-2", textColor)}>{region.name}</h3>
              <p className="text-sm text-white/70 mb-4">Examples: {region.examples}</p>

              <div className="space-y-3 bg-white/5 rounded px-3 py-3 mb-4 border border-white/10">
                <div>
                  <p className="text-xs text-white/60 uppercase tracking-wide">Net Direction</p>
                  <p className="text-sm font-semibold text-white">{region.net_direction}</p>
                </div>
                <div>
                  <p className="text-xs text-white/60 uppercase tracking-wide">Monthly Impact</p>
                  <p className={cn("text-sm font-semibold", region.net_direction.includes("positive") || region.net_direction.includes("gain") ? "text-green-400" : "text-red-400")}>
                    {region.net_monthly_range_median_hh}
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <p>
                  <span className="text-white/60">Rent Pressure:</span> <span className="text-white/80">{region.rent_impact_severity}</span>
                </p>
                <p>
                  <span className="text-white/60">Price Pressure:</span> <span className="text-white/80">{region.price_impact_severity}</span>
                </p>
              </div>

              <p className="text-xs text-white/50 italic mt-3 pt-3 border-t border-white/10">{region.explanation}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// 9. CONSISTENCY REPORT
function ConsistencyReport({ consistency_report }: { consistency_report: SynthesisReport["consistency_report"] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.8s" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between hover:opacity-80 transition"
      >
        <h2 className="text-2xl font-bold text-white">{consistency_report.title}</h2>
        <span className={cn("text-2xl transition-transform", isOpen ? "rotate-180" : "")}>▼</span>
      </button>

      {isOpen && (
        <div className="mt-6 space-y-6">
          {consistency_report.adjustments.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Adjustments ({consistency_report.adjustments.length})</h3>
              <div className="space-y-4">
                {consistency_report.adjustments.map((adj, idx) => (
                  <div key={idx} className="rounded-lg border border-white/10 bg-white/5 p-4">
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-semibold text-white">{adj.variable}</h4>
                      <span className={cn(
                        "text-xs px-2 py-1 rounded border",
                        adj.severity === "high" ? "bg-red-500/20 border-red-500/30 text-red-300" :
                        adj.severity === "medium" ? "bg-amber-500/20 border-amber-500/30 text-amber-300" :
                        "bg-blue-500/20 border-blue-500/30 text-blue-300"
                      )}>
                        {adj.severity}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-white/60 text-xs uppercase">Original</p>
                        <p className="text-white/80">{adj.original_value} ({adj.original_source})</p>
                      </div>
                      <div>
                        <p className="text-white/60 text-xs uppercase">Resolved</p>
                        <p className="text-green-300">{adj.resolved_value} ({adj.resolved_source})</p>
                      </div>
                    </div>

                    <p className="text-xs text-white/60 mt-3 pt-3 border-t border-white/10">{adj.issue}</p>
                    <p className="text-xs text-white/50 italic mt-2">Impact: {adj.impact_on_output}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {consistency_report.unresolved_gaps.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-amber-300 mb-4">Unresolved Gaps ({consistency_report.unresolved_gaps.length})</h3>
              <ul className="space-y-2">
                {consistency_report.unresolved_gaps.map((gap, idx) => (
                  <li key={idx} className="flex gap-2 text-white/70 text-sm">
                    <span className="text-amber-400">⚠</span> {gap}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// 10. CONFIDENCE ASSESSMENT
function ConfidenceAssessment({ confidence_assessment }: { confidence_assessment: SynthesisReport["confidence_assessment"] }) {
  const overallColor =
    String(confidence_assessment.overall).toUpperCase() === "EMPIRICAL" || String(confidence_assessment.overall).toUpperCase() === "HIGH" ? "text-green-400" :
    String(confidence_assessment.overall).toUpperCase() === "THEORETICAL" || String(confidence_assessment.overall).toUpperCase() === "MEDIUM" ? "text-amber-400" :
    "text-red-400";

  const componentBgColor = (conf: Confidence | string) => {
    const normalized = String(conf).toUpperCase();
    if (normalized === "EMPIRICAL" || normalized === "HIGH") return "bg-green-500/20 border-green-500/30";
    if (normalized === "THEORETICAL" || normalized === "MEDIUM") return "bg-amber-500/20 border-amber-500/30";
    return "bg-red-500/20 border-red-500/30";
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "0.9s" }}>
      <h2 className="text-2xl font-bold text-white mb-8">Confidence Assessment</h2>

      <div className="mb-8 p-6 rounded-lg border border-white/10 bg-white/5">
        <p className="text-white/60 text-sm uppercase tracking-wide mb-2">Overall Confidence</p>
        <p className={cn("text-4xl font-bold", overallColor)}>
          {String(confidence_assessment.overall).charAt(0).toUpperCase() + String(confidence_assessment.overall).slice(1).toLowerCase()}
        </p>
      </div>

      <div className="space-y-4 mb-8">
        <h3 className="text-lg font-semibold text-white">By Component</h3>
        {confidence_assessment.by_component.map((comp, idx) => {
          const compWidth = String(comp.confidence).toUpperCase() === "EMPIRICAL" || String(comp.confidence).toUpperCase() === "HIGH" ? 90 :
                            String(comp.confidence).toUpperCase() === "THEORETICAL" || String(comp.confidence).toUpperCase() === "MEDIUM" ? 60 : 30;

          return (
            <div key={idx} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-white font-semibold">{comp.component}</span>
                <span className={cn("text-sm font-semibold", confidenceColor(comp.confidence))}>
                  {String(comp.confidence).charAt(0).toUpperCase() + String(comp.confidence).slice(1).toLowerCase()}
                </span>
              </div>

              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", componentBgColor(comp.confidence))}
                  style={{ width: `${compWidth}%` }}
                />
              </div>

              <p className="text-xs text-white/60">{comp.reasoning}</p>
            </div>
          );
        })}
      </div>

      <div className="space-y-3 p-4 rounded-lg border border-white/10 bg-white/[0.03]">
        <p className="text-sm">
          <span className="text-white/60">Weakest Link:</span> <span className="text-white/80 ml-2">{confidence_assessment.weakest_link}</span>
        </p>

        <div>
          <p className="text-white/60 text-sm font-semibold mb-2">What Would Change This Conclusion:</p>
          <ul className="space-y-1">
            {confidence_assessment.what_would_change_conclusion.map((item, idx) => (
              <li key={idx} className="flex gap-2 text-white/70 text-sm">
                <span className="text-blue-400">▸</span> {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

// 11. EVIDENCE SUMMARY
function EvidenceSummary({ evidence_summary }: { evidence_summary: SynthesisReport["evidence_summary"] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "1s" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between hover:opacity-80 transition"
      >
        <h2 className="text-2xl font-bold text-white">{evidence_summary.title}</h2>
        <span className={cn("text-2xl transition-transform", isOpen ? "rotate-180" : "")}>▼</span>
      </button>

      {isOpen && (
        <div className="mt-6 space-y-6">
          <div className="p-4 rounded-lg border border-white/10 bg-white/5">
            <p className="text-white/70">{evidence_summary.consensus}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Key Studies</h3>
            <div className="space-y-4">
              {evidence_summary.key_studies.map((study, idx) => (
                <div key={idx} className="rounded-lg border border-white/10 bg-white/5 p-4">
                  <h4 className="font-semibold text-white mb-2">{study.name}</h4>
                  <p className="text-white/70 text-sm mb-3">{study.finding}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-white/60">Agent: {study.source_agent}</span>
                    <span className="px-2 py-1 rounded bg-blue-500/20 border border-blue-500/30 text-blue-300">
                      {study.applicability}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10">
            <p className="text-amber-300 text-sm font-semibold mb-1">Major Gap</p>
            <p className="text-white/70 text-sm">{evidence_summary.major_gap}</p>
          </div>
        </div>
      )}
    </section>
  );
}

// 12. DATA SOURCES & METHODOLOGY
function DataSources({ data_sources }: { data_sources: SynthesisReport["data_sources"] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "1.1s" }}>
      <h2 className="text-2xl font-bold text-white mb-6">{data_sources.title}</h2>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="p-4 rounded-lg border border-white/10 bg-white/[0.03]">
          <p className="text-white/60 text-sm uppercase tracking-wide">Total Tool Calls</p>
          <p className="text-3xl font-bold text-blue-400 mt-2">{data_sources.total_tool_calls}</p>
        </div>
        <div className="p-4 rounded-lg border border-white/10 bg-white/[0.03]">
          <p className="text-white/60 text-sm uppercase tracking-wide">Unique Data Series</p>
          <p className="text-3xl font-bold text-blue-400 mt-2">{data_sources.total_unique_data_series}</p>
        </div>
        <div className="p-4 rounded-lg border border-white/10 bg-white/[0.03]">
          <p className="text-white/60 text-sm uppercase tracking-wide">Agents Completed</p>
          <p className="text-3xl font-bold text-green-400 mt-2">{data_sources.agents_and_calls.length}</p>
        </div>
      </div>

      <h3 className="text-lg font-semibold text-white mb-4">Agent Breakdown</h3>
      <div className="space-y-4">
        {data_sources.agents_and_calls.map((agent, idx) => (
          <div key={idx} className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-white capitalize">{titleCase(agent.agent)}</h4>
              <span className="text-sm font-mono text-blue-300">{agent.tool_calls} calls</span>
            </div>
            <div className="text-xs text-white/60 mb-2">Key Data Sources:</div>
            <div className="flex flex-wrap gap-2">
              {agent.key_data.map((source, i) => (
                <span key={i} className="px-2 py-1 rounded bg-white/10 border border-white/10 text-white/70 text-xs">
                  {source}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {data_sources.methodology_notes.length > 0 && (
        <div className="mt-8 pt-6 border-t border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Methodology Notes</h3>
          <ul className="space-y-2">
            {data_sources.methodology_notes.map((note, idx) => (
              <li key={idx} className="flex gap-2 text-white/70 text-sm">
                <span className="text-blue-400">◆</span> {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

// 13. NARRATIVE (Tabbed)
function Narrative({ narrative }: { narrative: SynthesisReport["narrative"] }) {
  const [activeTab, setActiveTab] = useState<"executive" | "low" | "middle" | "upper" | "business">("executive");

  const tabs = [
    { id: "executive", label: "Executive Summary", content: narrative.executive_summary },
    { id: "low", label: "For Low Income", content: narrative.for_low_income },
    { id: "middle", label: "For Middle Income", content: narrative.for_middle_income },
    { id: "upper", label: "For Upper Income", content: narrative.for_upper_income },
    { id: "business", label: "For Small Business", content: narrative.for_small_business },
  ];

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-8 enter-card" style={{ animationDelay: "1.2s" }}>
      <h2 className="text-2xl font-bold text-white mb-6">Narratives</h2>

      <div className="flex flex-wrap gap-2 mb-6 border-b border-white/10 pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              "px-4 py-2 rounded-lg font-semibold transition-colors",
              activeTab === tab.id
                ? "bg-blue-500/30 border border-blue-500/50 text-blue-300"
                : "text-white/60 hover:text-white/80"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="prose prose-invert max-w-none">
        <p className="text-white/80 leading-relaxed whitespace-pre-wrap">
          {tabs.find((t) => t.id === activeTab)?.content}
        </p>
      </div>

      {narrative.biggest_uncertainty && (
        <div className="mt-8 pt-6 border-t border-white/10 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10">
          <p className="text-amber-300 text-sm font-semibold mb-2">Biggest Uncertainty</p>
          <p className="text-white/80">{narrative.biggest_uncertainty}</p>
        </div>
      )}
    </section>
  );
}

// MAIN COMPONENT
export default function ResultsPanel({ report }: ResultsPanelProps) {
  return (
    <div className="min-h-screen bg-slate-950 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto space-y-0">
        <HeroBanner report={report} />
        <HeadlineMetrics metrics={report.headline_metrics} />
        <WaterfallChart waterfall={report.waterfall} />
        <ImpactMatrix impact_matrix={report.impact_matrix} />
        <CategoryBreakdown categories={report.category_breakdown.categories} />
        <Timeline timeline={report.timeline} />
        <WinnersAndLosers winners_losers={report.winners_losers} />
        <GeographicImpact geographic_impact={report.geographic_impact} />
        <ConsistencyReport consistency_report={report.consistency_report} />
        <ConfidenceAssessment confidence_assessment={report.confidence_assessment} />
        <EvidenceSummary evidence_summary={report.evidence_summary} />
        <DataSources data_sources={report.data_sources} />
        <Narrative narrative={report.narrative} />

        <footer className="mt-12 pt-8 border-t border-white/10 text-center text-white/50 text-sm">
          <p>
            Report generated in {formatDuration(report.meta.pipeline_duration_seconds * 1000)} •{" "}
            {report.meta.total_tool_calls} API calls • PolicyPulse Economic Simulation Engine
          </p>
        </footer>
      </div>

      <style jsx>{`
        @keyframes enter-card {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .enter-card {
          animation: enter-card 0.5s ease-out forwards;
          opacity: 0;
        }
      `}</style>
    </div>
  );
}
