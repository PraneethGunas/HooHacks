"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SynthesisReport } from "@/types/pipeline";

// ─── Convenience aliases (kept local so Samank's component code reads cleanly)
// All data comes from SynthesisReport which is the pipeline's canonical type.
// Every access below uses optional chaining + fallback defaults so the UI
// never crashes on partial / malformed LLM output.
// ───────────────────────────────────────────────────────────────────────────────

type Confidence = "HIGH" | "MEDIUM" | "LOW" | "EMPIRICAL" | "THEORETICAL" | "SPECULATIVE";

interface ResultsPanelProps {
  report: SynthesisReport;
}

// ─── Color system ─────────────────────────────────────────────────────────────
// Red = only for genuinely negative economic outcomes
// Amber/orange = warnings, uncertainty, medium severity, trade-offs
// Slate/blue = neutral info, low confidence (not alarming)
// Emerald = gains, positive outcomes, high confidence

const CONF_STYLES: Record<string, { pill: string; dot: string; label: string }> = {
  HIGH:        { pill: "border-emerald-500/30 bg-emerald-950/40 text-emerald-400", dot: "bg-emerald-400", label: "High confidence" },
  MEDIUM:      { pill: "border-amber-500/25 bg-amber-950/30 text-amber-400",      dot: "bg-amber-400",   label: "Medium confidence" },
  LOW:         { pill: "border-slate-500/30 bg-slate-800/40 text-slate-400",       dot: "bg-slate-400",   label: "Low confidence" },
  // Map backend epistemic levels → visual confidence
  EMPIRICAL:   { pill: "border-emerald-500/30 bg-emerald-950/40 text-emerald-400", dot: "bg-emerald-400", label: "Data-backed" },
  THEORETICAL: { pill: "border-amber-500/25 bg-amber-950/30 text-amber-400",      dot: "bg-amber-400",   label: "Model-based" },
  SPECULATIVE: { pill: "border-slate-500/30 bg-slate-800/40 text-slate-400",       dot: "bg-slate-400",   label: "Uncertain" },
};

// Safe lookup — normalises any casing from the API, maps epistemic levels
function confStyle(raw: string | undefined | null) {
  if (!raw) return CONF_STYLES.MEDIUM;
  const key = raw.toUpperCase();
  return CONF_STYLES[key] ?? CONF_STYLES.MEDIUM;
}

// Severity: used for cost/risk indicators — not outcome badness
const SEVERITY_STYLES: Record<"HIGH" | "MEDIUM" | "LOW", { bar: string; text: string; label: string }> = {
  HIGH:   { bar: "bg-orange-400/70",  text: "text-orange-400",  label: "High" },
  MEDIUM: { bar: "bg-amber-400/60",   text: "text-amber-400",   label: "Medium" },
  LOW:    { bar: "bg-teal-400/60",    text: "text-teal-400",    label: "Low" },
};

// ─── Shared atoms ─────────────────────────────────────────────────────────────

function ConfBadge({ c, large }: { c: string | undefined | null; large?: boolean }) {
  const s = confStyle(c);
  const [showTooltip, setShowTooltip] = useState(false);

  const tooltipText: Record<string, string> = {
    "High confidence": "Backed by direct data from government APIs or peer-reviewed studies",
    "Medium confidence": "Based on established economic models with named assumptions",
    "Low confidence": "Agent reasoning flagged as uncertain — treat as directional only",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-medium relative cursor-help",
        large ? "px-3.5 py-1 text-sm gap-2" : "px-2.5 py-0.5 text-xs",
        s.pill,
      )}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className={cn(large ? "h-2 w-2" : "h-1.5 w-1.5", "rounded-full", s.dot)} />
      {large ? null : <span className="ml-1.5" />}
      {s.label}
      {showTooltip && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded-lg bg-black/95 border border-white/10 px-3 py-2 text-[11px] text-white/70 leading-relaxed z-50 pointer-events-none shadow-lg">
          {tooltipText[s.label] ?? "Confidence assessment from multi-agent analysis"}
        </span>
      )}
    </span>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 12 12" fill="none"
      className={cn("shrink-0 text-white/30 transition-transform duration-200", open && "rotate-180")}>
      <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-2xl border border-white/10 bg-[var(--bg-surface)] p-5", className)}>
      {children}
    </div>
  );
}

// Section headings — readable, not decorative
function SectionHeading({ label, sub }: { label: string; sub?: string }) {
  return (
    <div className="mb-5">
      <h3 className="text-base font-semibold text-white/85">{label}</h3>
      {sub && <p className="mt-0.5 text-sm text-white/45">{sub}</p>}
    </div>
  );
}

// Step indicator for the page narrative flow
function StepBadge({ n, label }: { n: number; label: string }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/8 text-xs font-semibold text-white/60">
        {n}
      </div>
      <span className="text-xs font-medium uppercase tracking-widest text-white/40">{label}</span>
      <div className="h-px flex-1 bg-white/8" />
    </div>
  );
}

// ─── 1: Hero header ───────────────────────────────────────────────────────────

function PolicyHeader({ report }: { report: SynthesisReport }) {
  const metrics = report.headline_metrics ?? [];
  const pos = metrics.filter((m) => m.direction === "positive").length;
  const neg = metrics.filter((m) => m.direction === "negative").length;
  const total = pos + neg || 1;
  const posW = Math.round((pos / total) * 100);

  const headlineConf = confStyle(report.headline?.confidence);

  // Verdict border color follows confidence — not always emerald
  const verdictBorder: Record<string, string> = {
    HIGH: "border-emerald-500/60 bg-emerald-950/20",
    MEDIUM: "border-amber-500/50 bg-amber-950/15",
    LOW: "border-slate-500/40 bg-slate-800/15",
  };
  const verdictLabel: Record<string, string> = {
    HIGH: "text-emerald-400/70",
    MEDIUM: "text-amber-400/70",
    LOW: "text-slate-400/70",
  };
  const confKey = (report.headline?.confidence ?? "MEDIUM").toUpperCase();

  return (
    <Card className="p-6">
      {/* Tags row */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {report.policy?.geography && (
          <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-xs text-white/55">
            {report.policy.geography}
          </span>
        )}
        <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-xs text-white/55">
          {report.meta?.agents_completed?.length ?? 0} agents · {report.meta?.total_tool_calls ?? 0} data calls
        </span>
        {report.policy?.estimated_annual_cost && (
          <span className="rounded-full border border-orange-500/25 bg-orange-950/25 px-3 py-1 text-xs text-orange-300/80">
            Federal cost: {report.policy.estimated_annual_cost}/yr
          </span>
        )}
        <span className={cn("ml-auto rounded-full border px-3 py-1 text-xs font-medium", headlineConf.pill)}>
          {headlineConf.label}
        </span>
      </div>

      {/* Title */}
      <h1 className="mb-1 text-2xl font-semibold leading-snug tracking-tight text-white">
        {report.policy?.title ?? "Policy Analysis"}
      </h1>
      <p className="mb-5 text-base text-white/50">{report.policy?.one_liner ?? ""}</p>

      {/* Verdict callout — color follows confidence */}
      <div className={cn("mb-5 rounded-xl border-l-4 px-4 py-3", verdictBorder[confKey] ?? verdictBorder.MEDIUM)}>
        <div className={cn("mb-0.5 text-xs font-semibold uppercase tracking-widest", verdictLabel[confKey] ?? verdictLabel.MEDIUM)}>
          Overall verdict
        </div>
        <p className="text-[15px] font-medium leading-snug text-white/90">{report.headline?.verdict ?? ""}</p>
      </div>

      {/* Signal bar */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-sm text-white/50">
          <span>{pos} positive outcomes</span>
          <span>{neg} costs / risks</span>
        </div>
        <div className="flex h-3 overflow-hidden rounded-full bg-white/8">
          <div className="bg-emerald-500/65 transition-all duration-700" style={{ width: `${posW}%` }} />
          <div className="flex-1 bg-red-500/45" />
        </div>
        <div className="flex justify-between text-xs text-white/35">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500/65" />Gains
          </span>
          <span className="flex items-center gap-1.5">
            Costs &amp; risks
            <span className="h-2 w-2 rounded-full bg-red-500/45" />
          </span>
        </div>
      </div>
    </Card>
  );
}

// ─── 2: KPI strip ─────────────────────────────────────────────────────────────

function KpiStrip({ metrics }: { metrics: SynthesisReport["headline_metrics"] }) {
  if (!metrics || metrics.length === 0) return null;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {metrics.slice(0, 5).map((m) => (
        <div
          key={m.id}
          className={cn(
            "rounded-xl border p-4",
            m.direction === "positive"
              ? "border-emerald-500/20 bg-emerald-950/15"
              : "border-red-500/20 bg-red-950/15",
          )}
        >
          <div className="mb-2 text-xs font-medium text-white/50 leading-tight">{m.label}</div>
          <div className={cn("text-[22px] font-semibold leading-none tracking-tight",
            m.direction === "positive" ? "text-emerald-300" : "text-red-300")}>
            {m.value}
          </div>
          {m.range && (
            <div className="mt-1 text-[11px] text-white/28 tabular-nums">
              {m.range.low} – {m.range.high}
            </div>
          )}
          <div className="mt-2.5">
            <ConfBadge c={m.confidence} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── 3: Waterfall chart — SVG ─────────────────────────────────────────────────

function WaterfallChart({ data }: { data: SynthesisReport["waterfall"] }) {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);
  if (!data?.steps || data.steps.length === 0) return <div className="text-sm text-white/30">No waterfall data available</div>;
  const steps = data.steps.filter((s) => s.value !== 0 && s.type !== "neutral");
  if (steps.length === 0) return null;
  const maxVal = Math.max(...steps.map((s) => Math.abs(s.value))) || 1;

  const BAR_H = 34;
  const BAR_GAP = 5;
  const LABEL_W = 156;
  const TRACK_W = 280;
  const CUM_W = 64;
  const PAD = 10;
  const svgH = steps.length * (BAR_H + BAR_GAP) + PAD * 2;
  const SVG_W = LABEL_W + TRACK_W + CUM_W + PAD * 3;

  return (
    <div>
      <div className="mb-1 text-sm text-white/50">{data.subtitle}</div>
      <div className="mb-5 flex items-center gap-4 text-xs text-white/35">
        <span>{data.household_profile}</span>
        <span className="ml-auto flex items-center gap-3">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-emerald-500/50" />Gain</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-red-500/40" />Cost</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-emerald-500/70" />Net</span>
          <span className="text-white/20">Cumulative →</span>
        </span>
      </div>

      <div className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${SVG_W} ${svgH}`} style={{ minWidth: 460 }}>
          {steps.map((step, i) => {
            const isNet = step.type === "net";
            const isInflow = step.type === "inflow";
            const pct = Math.round((Math.abs(step.value) / maxVal) * 100);
            const barW = Math.max(4, Math.round((pct / 100) * TRACK_W));
            const y = PAD + i * (BAR_H + BAR_GAP);
            const isHovered = hoveredStep === step.label;

            const barFill = isNet
              ? "rgba(52,211,153,0.65)"
              : isInflow
                ? "rgba(52,211,153,0.38)"
                : "rgba(239,68,68,0.35)";
            const textFill = isNet ? "#6ee7b7" : isInflow ? "#a7f3d0" : "#fca5a5";
            const labelFill = isNet
              ? "rgba(255,255,255,0.90)"
              : isHovered
                ? "rgba(255,255,255,0.75)"
                : "rgba(255,255,255,0.55)";

            return (
              <g key={`${step.label}-${i}`}
                className="cursor-default"
                onMouseEnter={() => setHoveredStep(step.label)}
                onMouseLeave={() => setHoveredStep(null)}>
                {/* Label */}
                <text x={LABEL_W - 10} y={y + BAR_H / 2}
                  textAnchor="end" dominantBaseline="central"
                  fill={labelFill}
                  fontSize={isNet ? "13" : "12"}
                  fontWeight={isNet ? "600" : "400"}>
                  {step.label}
                </text>

                {/* Track bg */}
                <rect x={LABEL_W + PAD} y={y} width={TRACK_W} height={BAR_H} rx="6"
                  fill={isHovered ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.03)"} />

                {/* Bar */}
                <rect x={LABEL_W + PAD} y={y} width={barW} height={BAR_H} rx="6" fill={barFill} />

                {/* Value label in bar */}
                {barW > 54 && (
                  <text x={LABEL_W + PAD + barW - 10} y={y + BAR_H / 2}
                    textAnchor="end" dominantBaseline="central"
                    fill={textFill} fontSize="12" fontWeight="500">
                    {isInflow ? "+" : ""}${Math.abs(step.value)}
                  </text>
                )}
                {barW <= 54 && (
                  <text x={LABEL_W + PAD + barW + 6} y={y + BAR_H / 2}
                    dominantBaseline="central"
                    fill={textFill} fontSize="11">
                    {isInflow ? "+" : "–"}${Math.abs(step.value)}
                  </text>
                )}

                {/* Cumulative */}
                <text x={LABEL_W + PAD + TRACK_W + 10} y={y + BAR_H / 2}
                  dominantBaseline="central"
                  fill="rgba(255,255,255,0.28)" fontSize="11" fontFamily="monospace">
                  ${step.cumulative}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Net summary */}
      {(() => {
        const netM = data.net_monthly ?? 0;
        const netA = data.net_annual ?? 0;
        const pctI = data.pct_of_income ?? 0;
        const isNeg = netM < 0;
        const sign = isNeg ? "–" : "+";
        const borderColor = isNeg ? "border-red-500/20 bg-red-950/15" : "border-emerald-500/20 bg-emerald-950/15";
        const textColor = isNeg ? "text-red-300" : "text-emerald-300";
        return (
          <div className="mt-5 grid grid-cols-3 gap-3">
            {[
              { label: isNeg ? "Net monthly cost" : "Net monthly gain", value: `${sign}$${Math.abs(netM)}`, big: true },
              { label: "Over a year", value: `${sign}$${Math.abs(netA).toLocaleString()}` },
              { label: "% of income", value: `${sign}${Math.abs(pctI)}%` },
            ].map((s) => (
              <div key={s.label}
                className={cn("rounded-xl border p-3 text-center", borderColor)}>
                <div className="text-xs text-white/40">{s.label}</div>
                <div className={cn("mt-1 font-semibold", textColor, s.big ? "text-2xl" : "text-lg")}>
                  {s.value}
                </div>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

// ─── 4: Category chart — horizontal SVG bars ─────────────────────────────────

function CategoryChart({ categories }: { categories: SynthesisReport["category_breakdown"]["categories"] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (!categories || categories.length === 0) return <div className="text-sm text-white/30">No category data available</div>;
  const sorted = [...categories].sort(
    (a, b) => Math.abs(b.dollar_impact_monthly?.central ?? 0) - Math.abs(a.dollar_impact_monthly?.central ?? 0),
  );
  const maxAbs = Math.max(...sorted.map((c) => Math.abs(c.dollar_impact_monthly?.central ?? 0))) || 1;

  const BAR_H = 30;
  const BAR_GAP = 7;
  const LABEL_W = 148;
  const TRACK_W = 240;
  const VAL_W = 80;
  const PAD = 8;
  const svgH = sorted.length * (BAR_H + BAR_GAP) + PAD * 2;
  const SVG_W = LABEL_W + TRACK_W + VAL_W + PAD * 2;

  return (
    <div>
      <div className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${SVG_W} ${svgH}`} style={{ minWidth: 420 }}>
          {sorted.map((cat, i) => {
            const centralVal = cat.dollar_impact_monthly?.central ?? 0;
            const isNeg = centralVal < 0;
            const pct = Math.round((Math.abs(centralVal) / maxAbs) * 100);
            const barW = Math.max(4, Math.round((pct / 100) * TRACK_W));
            const y = PAD + i * (BAR_H + BAR_GAP);
            // Costs use orange, not pure red — it's a cost, not a catastrophe
            const barFill = isNeg ? "rgba(249,115,22,0.38)" : "rgba(52,211,153,0.38)";
            const valFill = isNeg ? "#fdba74" : "#6ee7b7";
            const isActive = expanded === cat.name;

            return (
              <g key={cat.name} className="cursor-pointer"
                onClick={() => setExpanded(isActive ? null : cat.name)}>
                <text x={LABEL_W - 10} y={y + BAR_H / 2}
                  textAnchor="end" dominantBaseline="central"
                  fill={isActive ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.60)"}
                  fontSize="12">
                  {cat.name}
                </text>
                <rect x={LABEL_W + PAD} y={y} width={TRACK_W} height={BAR_H} rx="5"
                  fill={isActive ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.04)"} />
                <rect x={LABEL_W + PAD} y={y} width={barW} height={BAR_H} rx="5" fill={barFill} />
                {barW > 36 && (
                  <text x={LABEL_W + PAD + 8} y={y + BAR_H / 2}
                    dominantBaseline="central" fill={valFill} fontSize="11" fontWeight="500">
                    {isNeg ? "" : "+"}{cat.pct_change?.central ?? 0}%
                  </text>
                )}
                <text x={LABEL_W + PAD + TRACK_W + 10} y={y + BAR_H / 2}
                  dominantBaseline="central"
                  fill={valFill} fontSize="12" fontWeight="500" fontFamily="monospace">
                  {isNeg ? "–" : "+"}${Math.abs(centralVal)}/mo
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Expanded detail — outside SVG */}
      {expanded && (() => {
        const cat = sorted.find((c) => c.name === expanded);
        if (!cat) return null;
        return (
          <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-white/85">{cat.name}</span>
              <ConfBadge c={cat.confidence} />
            </div>
            <p className="mb-2 text-sm text-white/55">{cat.explanation}</p>
            {cat.note && <p className="mb-2 text-xs text-amber-300/70">{cat.note}</p>}
            <div className="text-xs text-white/30 tabular-nums">
              Range: ${cat.dollar_impact_monthly?.low ?? 0} – ${cat.dollar_impact_monthly?.high ?? 0}/mo
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ─── 5: Timeline chart ────────────────────────────────────────────────────────

function TimelineChart({ phases, household_profile }: { phases: SynthesisReport["timeline"]["phases"]; household_profile: string }) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  if (!phases || phases.length < 2) return <div className="text-sm text-white/30">Insufficient timeline data</div>;
  const maxVal = Math.max(...phases.map((p) => p.cumulative_net_monthly?.high ?? 0)) || 1;
  const W = 540;
  const H = 150;
  const PL = 48; const PR = 20; const PT = 14; const PB = 34;
  const iW = W - PL - PR; const iH = H - PT - PB;
  const xOf = (i: number) => PL + (i / (phases.length - 1)) * iW;
  const yOf = (v: number) => PT + iH - (v / maxVal) * iH;

  const highPts = phases.map((p, i) => `${xOf(i)},${yOf(p.cumulative_net_monthly?.high ?? 0)}`).join(" ");
  const lowPtsRev = [...phases].reverse().map((p, i) =>
    `${xOf(phases.length - 1 - i)},${yOf(p.cumulative_net_monthly?.low ?? 0)}`
  ).join(" ");
  const centralPts = phases.map((p, i) => `${xOf(i)},${yOf(p.cumulative_net_monthly?.central ?? 0)}`).join(" ");

  // Mood → line color (no red — all phases net positive in this schema)
  const moodColor: Record<string, string> = {
    optimistic: "#34d399", stable: "#60a5fa", settling: "#f59e0b",
    new_normal: "#c4b5fd", uncertain: "#94a3b8",
  };

  return (
    <div>
      <div className="mb-4 text-xs text-white/35">{household_profile}</div>
      <div className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 380 }}>
          {/* Y gridlines */}
          {[0, Math.round(maxVal * 0.5), maxVal].map((t) => (
            <g key={t}>
              <line x1={PL} y1={yOf(t)} x2={W - PR} y2={yOf(t)}
                stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
              <text x={PL - 6} y={yOf(t)} textAnchor="end" dominantBaseline="central"
                fill="rgba(255,255,255,0.28)" fontSize="10">
                ${t}
              </text>
            </g>
          ))}

          {/* Confidence band */}
          <polygon points={`${highPts} ${lowPtsRev}`} fill="rgba(52,211,153,0.08)" />

          {/* Central line */}
          <polyline points={centralPts} fill="none"
            stroke="#34d399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

          {/* Points + interaction */}
          {phases.map((p, i) => {
            const x = xOf(i); const y = yOf(p.cumulative_net_monthly?.central ?? 0);
            const active = activeIdx === i;
            const color = moodColor[p.mood] ?? "#94a3b8";
            return (
              <g key={`pt-${i}`}
                onMouseEnter={() => setActiveIdx(i)}
                onMouseLeave={() => setActiveIdx(null)}>
                {active && (
                  <line x1={x} y1={PT} x2={x} y2={H - PB}
                    stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
                )}
                <circle cx={x} cy={y} r={active ? 5 : 3.5} fill={color}
                  stroke="#111318" strokeWidth="2" className="cursor-pointer" />
                {/* Tooltip */}
                {active && (
                  <g>
                    <rect x={Math.min(x - 65, W - 145)} y={y - 50}
                      width={140} height={42} rx="6"
                      fill="#181C23" stroke="rgba(255,255,255,0.12)" strokeWidth="0.5" />
                    <text x={Math.min(x - 65, W - 145) + 10} y={y - 33}
                      fill="rgba(255,255,255,0.88)" fontSize="13" fontWeight="600">
                      +${p.cumulative_net_monthly?.central ?? 0}/mo
                    </text>
                    <text x={Math.min(x - 65, W - 145) + 10} y={y - 18}
                      fill="rgba(255,255,255,0.38)" fontSize="10">
                      range ${p.cumulative_net_monthly?.low ?? 0}–${p.cumulative_net_monthly?.high ?? 0}
                    </text>
                  </g>
                )}
                {/* X label */}
                <text x={x} y={H - PB + 14} textAnchor="middle"
                  fill="rgba(255,255,255,0.35)" fontSize="10">
                  {p.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Phase rows */}
      <div className="mt-3 space-y-1.5">
        {phases.map((p, i) => {
          const color = moodColor[p.mood] ?? "#94a3b8";
          const isActive = activeIdx === i;
          return (
            <div key={`row-${i}`}
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
                isActive ? "border-white/14 bg-white/5" : "border-white/6 hover:border-white/10",
              )}
              onMouseEnter={() => setActiveIdx(i)}
              onMouseLeave={() => setActiveIdx(null)}>
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
              <span className="w-20 shrink-0 text-sm font-medium text-white/65">{p.label}</span>
              <span className="flex-1 truncate text-sm text-white/38">{p.dominant_driver}</span>
              <span className="shrink-0 tabular-nums text-sm font-semibold text-emerald-300">
                +${p.cumulative_net_monthly?.central ?? 0}/mo
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── 6: Winners & Losers ──────────────────────────────────────────────────────

// ProfileCard as standalone component — NO useState in map()
function ProfileCard({
  profile,
  cardType,
}: {
  profile: SynthesisReport["winners_losers"]["winners"][number];
  cardType: "winner" | "loser" | "mixed";
}) {
  const [open, setOpen] = useState(false);

  const styles = {
    winner: {
      border: "border-emerald-500/20",
      bg: "bg-emerald-950/12",
      dot: "bg-emerald-400",
      num: "text-emerald-300",
    },
    loser: {
      // Losers: use orange/coral — it's a bad outcome but not alarming red
      border: "border-orange-500/20",
      bg: "bg-orange-950/10",
      dot: "bg-orange-400",
      num: "text-orange-300",
    },
    mixed: {
      border: "border-amber-500/18",
      bg: "bg-amber-950/10",
      dot: "bg-amber-400",
      num: "text-amber-300",
    },
  }[cardType];

  return (
    <div className={cn("rounded-xl border p-4", styles.border, styles.bg)}>
      <div className="mb-2 flex items-start gap-2">
        <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", styles.dot)} />
        <span className="text-sm font-semibold leading-snug text-white/85">{profile.profile}</span>
      </div>
      <div className={cn("mb-1 text-xl font-semibold tabular-nums leading-none", styles.num)}>
        {profile.net_monthly_range}
        <span className="ml-1 text-sm font-normal text-white/35">/mo</span>
      </div>
      {profile.pct_of_income_range !== "N/A" && (
        <div className="mb-3 text-xs text-white/35">{profile.pct_of_income_range} of income</div>
      )}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-white/35 hover:text-white/60 transition-colors"
      >
        Why? <Chevron open={open} />
      </button>
      {open && (
        <div className="mt-3 space-y-2 border-t border-white/8 pt-3">
          <p className="text-sm leading-6 text-white/55">{profile.why}</p>
          {profile.caveat && (
            <p className="text-xs text-amber-300/65">{profile.caveat}</p>
          )}
          {profile.depends_on && (
            <p className="text-xs text-white/30">Depends on: {profile.depends_on}</p>
          )}
          <ConfBadge c={profile.confidence} />
        </div>
      )}
    </div>
  );
}

function WinnersLosers({ data }: { data: SynthesisReport["winners_losers"] }) {
  type WLTab = "winners" | "losers" | "mixed";
  const [tab, setTab] = useState<WLTab>("winners");

  const winners = data?.winners ?? [];
  const losers = data?.losers ?? [];
  const mixed = data?.mixed ?? [];

  const tabs: { key: WLTab; label: string; activeClass: string; count: number }[] = [
    {
      key: "winners", label: "Winners", count: winners.length,
      activeClass: "border-emerald-500/35 bg-emerald-950/30 text-emerald-300",
    },
    {
      key: "losers", label: "Losers / risks", count: losers.length,
      activeClass: "border-orange-500/35 bg-orange-950/25 text-orange-300",
    },
    {
      key: "mixed", label: "Mixed", count: mixed.length,
      activeClass: "border-amber-500/30 bg-amber-950/25 text-amber-300",
    },
  ];

  const profiles: Record<WLTab, typeof winners> = {
    winners,
    losers,
    mixed,
  };

  return (
    <div className="space-y-4">
      {/* Distributional verdict */}
      {data?.distributional_verdict && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/15 px-5 py-4">
          <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-emerald-400/70">
            {data.distributional_verdict.progressive_or_regressive ?? "Distributional Impact"}
          </div>
          <p className="text-sm leading-6 text-white/65">{data.distributional_verdict.explanation ?? ""}</p>
        </div>
      )}

      {/* Tab row */}
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "rounded-full border px-4 py-1.5 text-sm font-medium transition-all duration-150",
              tab === t.key ? t.activeClass : "border-white/10 text-white/40 hover:text-white/65",
            )}
          >
            {t.label}
            <span className="ml-1.5 text-xs opacity-60">({t.count})</span>
          </button>
        ))}
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {profiles[tab].map((p) => (
          <ProfileCard key={p.profile} profile={p} cardType={tab === "winners" ? "winner" : tab === "losers" ? "loser" : "mixed"} />
        ))}
      </div>
    </div>
  );
}

// ─── 7: Geographic impact ─────────────────────────────────────────────────────

function GeographicImpact({ regions }: { regions: SynthesisReport["geographic_impact"]["regions"] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {regions.map((r) => (
        <div key={r.id} className="rounded-xl border border-white/10 bg-[var(--bg-surface)] p-5">
          <div className="mb-1 text-base font-semibold text-white/88">{r.name}</div>
          <div className="mb-4 text-xs text-white/35">{r.examples}</div>

          {/* Big net number */}
          <div className="mb-4 text-2xl font-semibold" style={{ color: r.color }}>
            {r.net_monthly_range_median_hh}
            <span className="ml-1 text-sm font-normal text-white/30">/mo</span>
          </div>

          {/* Cost severity meters — orange for high, amber for medium */}
          <div className="mb-4 space-y-2.5">
            {[
              { label: "Rent pressure", severity: r.rent_impact_severity },
              { label: "Price pressure", severity: r.price_impact_severity },
            ].map((s) => (
              <div key={s.label}>
                <div className="mb-1.5 flex justify-between text-xs text-white/40">
                  <span>{s.label}</span>
                  <span className={(SEVERITY_STYLES as Record<string, typeof SEVERITY_STYLES.HIGH>)[s.severity]?.text ?? "text-white/40"}>
                    {(SEVERITY_STYLES as Record<string, typeof SEVERITY_STYLES.HIGH>)[s.severity]?.label ?? s.severity}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/8">
                  <div
                    className={cn("h-full rounded-full transition-all", (SEVERITY_STYLES as Record<string, typeof SEVERITY_STYLES.HIGH>)[s.severity]?.bar ?? "bg-white/20")}
                    style={{ width: s.severity === "HIGH" ? "75%" : s.severity === "MEDIUM" ? "48%" : "22%" }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p className="text-xs leading-4 text-white/40">{r.key_factor}</p>
        </div>
      ))}
    </div>
  );
}

// ─── 8: Confidence radar — SVG pentagon ──────────────────────────────────────

function ConfidenceRadar({ data }: { data: SynthesisReport["confidence_assessment"] }) {
  const [expandedScenario, setExpandedScenario] = useState(false);
  const components = (data?.by_component ?? []).slice(0, 5);
  if (components.length === 0) return <div className="text-sm text-white/30">No confidence data available</div>;
  const scores: Record<string, number> = {
    HIGH: 1, MEDIUM: 0.55, LOW: 0.2,
    EMPIRICAL: 1, THEORETICAL: 0.55, SPECULATIVE: 0.2,
  };

  const SIZE = 180;
  const cx = SIZE / 2; const cy = SIZE / 2;
  const R = 68; const n = components.length;

  function polarPt(i: number, r: number) {
    const angle = (i * 2 * Math.PI) / n - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  }

  const gridLevels = [0.33, 0.67, 1];
  const dataPoints = components.map((c, i) => polarPt(i, R * (scores[(c.confidence ?? "MEDIUM").toUpperCase() as Confidence] ?? 0.55)));
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ") + "Z";

  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
      {/* Pentagon chart */}
      <div className="shrink-0 self-center sm:self-start">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          {gridLevels.map((lvl) => {
            const pts = Array.from({ length: n }, (_, i) => polarPt(i, R * lvl));
            const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ") + "Z";
            return <path key={lvl} d={d} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />;
          })}
          {components.map((_, i) => {
            const outer = polarPt(i, R);
            return <line key={i} x1={cx} y1={cy} x2={outer.x} y2={outer.y}
              stroke="rgba(255,255,255,0.06)" strokeWidth="1" />;
          })}
          <path d={dataPath} fill="rgba(96,165,250,0.18)" stroke="#60a5fa" strokeWidth="1.5" />
          {dataPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="3.5" fill="#60a5fa" stroke="#111318" strokeWidth="2" />
          ))}
          {components.map((c, i) => {
            const pt = polarPt(i, R + 20);
            return (
              <text key={i} x={pt.x} y={pt.y} textAnchor="middle" dominantBaseline="central"
                fill="rgba(255,255,255,0.45)" fontSize="10">
                {c.component.split(" ").slice(0, 2).join(" ")}
              </text>
            );
          })}
        </svg>
      </div>

      <div className="flex-1 space-y-2.5">
        {/* Weakest link — amber, not red */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 px-4 py-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400/70">
            Biggest uncertainty
          </div>
          <p className="text-sm font-medium text-white/80">{data?.weakest_link ?? "Unknown"}</p>
        </div>

        {/* Component confidence rows */}
        {components.map((c) => (
          <div key={c.component} className="flex items-center gap-3 rounded-lg border border-white/7 px-3 py-2.5">
            <ConfBadge c={c.confidence} />
            <span className="flex-1 text-sm text-white/65">{c.component}</span>
          </div>
        ))}

        {/* What would change */}
        <button
          onClick={() => setExpandedScenario(!expandedScenario)}
          className="flex w-full items-center gap-2 rounded-lg border border-white/7 px-3 py-2.5 text-sm text-white/45 hover:text-white/65 transition-colors"
        >
          <span className="flex-1 text-left">
            {(data?.what_would_change_conclusion ?? []).length} scenarios that change this conclusion
          </span>
          <Chevron open={expandedScenario} />
        </button>
        {expandedScenario && (
          <div className="space-y-2 rounded-xl border border-white/8 bg-white/[0.02] p-3">
            {(data?.what_would_change_conclusion ?? []).map((item, i) => (
              <div key={i} className="flex gap-2.5 text-sm text-white/50">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400/50" />
                {item}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── 9: Narrative — audience tabs (FIXED: text keyed correctly) ───────────────

type NarrativeTab = "low_income" | "middle_income" | "upper_income" | "small_business";

function NarrativePanel({ narrative }: { narrative: SynthesisReport["narrative"] }) {
  const [activeTab, setActiveTab] = useState<NarrativeTab>("middle_income");

  const tabs: { key: NarrativeTab; label: string }[] = [
    { key: "low_income",    label: "Low income" },
    { key: "middle_income", label: "Middle income" },
    { key: "upper_income",  label: "Upper income" },
    { key: "small_business", label: "Small business" },
  ];

  // Explicit mapping — no computed key indexing, avoids silent mismatch bugs
  function getContent(tab: NarrativeTab): string {
    if (tab === "low_income")    return narrative?.for_low_income ?? "";
    if (tab === "middle_income") return narrative?.for_middle_income ?? "";
    if (tab === "upper_income")  return narrative?.for_upper_income ?? "";
    return narrative?.for_small_business ?? "";
  }

  return (
    <div>
      {/* Tab row */}
      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={cn(
              "rounded-full border px-4 py-1.5 text-sm font-medium transition-all duration-150",
              activeTab === t.key
                ? "border-white/22 bg-white/10 text-white/90"
                : "border-white/8 text-white/40 hover:text-white/65",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content — always rendered fresh from getContent() */}
      <p className="mb-5 text-sm leading-7 text-white/65">
        {getContent(activeTab) || <span className="italic text-white/30">No specific analysis available for this demographic yet.</span>}
      </p>

      <div className="rounded-xl border border-amber-500/18 bg-amber-950/12 px-4 py-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400/65">
          Key uncertainty
        </div>
        <p className="text-sm text-white/55">{narrative?.biggest_uncertainty ?? ""}</p>
      </div>
    </div>
  );
}

// ─── Evidence Summary ────────────────────────────────────────────────────────

function EvidenceSummary({ data }: { data: SynthesisReport["evidence_summary"] }) {
  const [showAll, setShowAll] = useState(false);
  if (!data?.key_studies?.length) return null;
  const studies = showAll ? data.key_studies : data.key_studies.slice(0, 5);

  return (
    <div className="space-y-3">
      {data.consensus && (
        <p className="text-sm leading-6 text-white/55">{data.consensus}</p>
      )}
      <div className="space-y-2">
        {studies.map((s, i) => (
          <div key={i} className="flex items-start gap-2.5 rounded-lg border border-white/7 px-3 py-2.5">
            <ConfBadge c={s.applicability?.includes("empirical") ? "EMPIRICAL" : s.applicability?.includes("theoretical") ? "THEORETICAL" : "SPECULATIVE"} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white/70 truncate">{s.name}</p>
              <p className="text-xs text-white/35 mt-0.5">{s.source_agent} — {s.finding?.slice(0, 80)}</p>
            </div>
          </div>
        ))}
      </div>
      {data.key_studies.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-xs text-white/40 hover:text-white/60 transition-colors"
        >
          {showAll ? "Show fewer" : `Show all ${data.key_studies.length} citations`}
        </button>
      )}
      {data.major_gap && (
        <div className="rounded-lg border border-amber-500/15 bg-amber-950/10 px-3 py-2 text-xs text-amber-300/70">
          Gap in evidence: {data.major_gap}
        </div>
      )}
    </div>
  );
}

// ─── Data Sources Summary ──────────────────────────────────────────────────────

function DataSourcesSummary({ report }: { report: SynthesisReport }) {
  const ds = report.data_sources;
  if (!ds) return null;

  const agentCalls = ds.agents_and_calls ?? [];
  const totalCalls = ds.total_tool_calls ?? report.meta?.total_tool_calls ?? 0;
  const totalSeries = ds.total_unique_data_series ?? 0;
  const agentsCompleted = report.meta?.agents_completed?.length ?? agentCalls.length;

  // Unique data sources from tool info
  const sourceNames = ["FRED", "BLS", "Census", "BEA", "Semantic Scholar", "CBO", "Tavily"];

  return (
    <div className="rounded-2xl border border-white/10 bg-[var(--bg-surface)] p-4">
      <div className="flex flex-wrap items-center gap-3">
        {/* Stats */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-emerald-400 font-semibold">{totalCalls}</span>
          <span className="text-white/45">data calls</span>
        </div>
        <span className="text-white/15">|</span>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-blue-400 font-semibold">{agentsCompleted}</span>
          <span className="text-white/45">agents</span>
        </div>
        <span className="text-white/15">|</span>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-purple-400 font-semibold">{totalSeries}</span>
          <span className="text-white/45">unique data series</span>
        </div>
        <span className="text-white/15">|</span>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-amber-400 font-semibold">{report.meta?.pipeline_duration_seconds ?? 0}s</span>
          <span className="text-white/45">pipeline time</span>
        </div>

        {/* Source badges */}
        <div className="ml-auto flex flex-wrap gap-1.5">
          {sourceNames.map(name => (
            <span key={name} className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-white/40">
              {name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Actionable Steps ("What You Can Do") ────────────────────────────────────

function ActionableSteps({ report }: { report: SynthesisReport }) {
  // Generate actionable steps from narrative context
  const steps = generateActionableSteps(report);
  if (steps.length === 0) return null;

  return (
    <Card className="border-emerald-500/15 bg-emerald-950/5">
      <SectionHeading
        label="What you can do"
        sub="Concrete next steps based on this analysis"
      />
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3 rounded-lg border border-emerald-500/15 bg-emerald-950/10 px-4 py-3">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-xs font-bold text-emerald-400">
              {i + 1}
            </div>
            <div>
              <p className="text-sm text-white/75 leading-relaxed">{step.action}</p>
              {step.context && <p className="mt-1 text-xs text-white/35">{step.context}</p>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function generateActionableSteps(report: SynthesisReport): Array<{ action: string; context?: string }> {
  const steps: Array<{ action: string; context?: string }> = [];
  const policyType = report.policy?.type?.toLowerCase() ?? "";
  const title = report.policy?.title?.toLowerCase() ?? "";

  // Immigration / visa related
  if (policyType.includes("immigration") || title.includes("visa") || title.includes("h1b") || title.includes("h-1b")) {
    steps.push(
      { action: "Check your visa category and expiration dates immediately", context: "Processing times may change as policy takes effect" },
      { action: "Consult an immigration attorney for personalized guidance", context: "Policy details often differ significantly from headlines" },
      { action: "Monitor USCIS bulletins and Federal Register updates monthly" },
    );
  }
  // Student loan related
  if (title.includes("student loan") || title.includes("forgive") || title.includes("debt")) {
    steps.push(
      { action: "Verify your loan servicer and outstanding balance on StudentAid.gov", context: "Eligibility criteria vary by program and loan type" },
      { action: "Do not stop making payments unless officially instructed", context: "Missed payments during processing can still affect credit" },
      { action: "File your FAFSA and income-driven repayment application proactively" },
    );
  }
  // Tariff / trade related
  if (policyType.includes("tariff") || policyType.includes("trade") || title.includes("tariff") || title.includes("import")) {
    steps.push(
      { action: "Audit your supply chain for exposure to affected imports", context: "Identify components sourced from tariff-targeted countries" },
      { action: "Explore domestic or alternative-country suppliers now", context: "Switching costs increase once tariffs take effect" },
      { action: "Review pricing strategy and communicate potential changes to customers" },
    );
  }
  // Tax related
  if (policyType.includes("tax") || title.includes("tax")) {
    steps.push(
      { action: "Review your exposure to affected sectors and adjust portfolio diversification", context: "Tax changes affect equity valuations before they affect earnings" },
      { action: "Consult a tax professional about planning opportunities before the effective date" },
      { action: "If you run a business: model the impact on your margins using the scenario ranges above" },
    );
  }

  // Generic steps if none matched
  if (steps.length === 0) {
    steps.push(
      { action: "Stay informed — bookmark official government sources for updates", context: "Policy details evolve significantly during implementation" },
      { action: "Assess your personal exposure using the income-tier breakdowns above" },
      { action: "Consider consulting a professional advisor for your specific situation" },
    );
  }

  return steps;
}

// ─── Sticky Section Nav ──────────────────────────────────────────────────────

const SECTION_NAV = [
  { id: "overview", label: "Overview", n: 1 },
  { id: "waterfall", label: "Money Flow", n: 2 },
  { id: "categories", label: "Categories", n: 3 },
  { id: "winners", label: "Winners", n: 4 },
  { id: "geography", label: "Geography", n: 5 },
  { id: "confidence", label: "Confidence", n: 6 },
  { id: "actions", label: "Actions", n: 7 },
];

function SectionNav() {
  const [active, setActive] = useState("overview");

  const scrollTo = (id: string) => {
    const el = document.getElementById(`section-${id}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActive(id);
    }
  };

  return (
    <nav className="hidden lg:flex fixed right-4 top-1/2 -translate-y-1/2 z-40 flex-col gap-2">
      {SECTION_NAV.map((s) => (
        <button
          key={s.id}
          onClick={() => scrollTo(s.id)}
          className={cn(
            "group flex items-center gap-2 transition-all",
          )}
        >
          <span className={cn(
            "h-2 w-2 rounded-full transition-all",
            active === s.id ? "bg-amber-400 scale-125" : "bg-white/20 group-hover:bg-white/40",
          )} />
          <span className={cn(
            "text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity",
            active === s.id ? "text-amber-300" : "text-white/50",
          )}>
            {s.label}
          </span>
        </button>
      ))}
    </nav>
  );
}

// ─── Main — page flow ─────────────────────────────────────────────────────────

export default function ResultsPanel({ report }: ResultsPanelProps) {
  if (!report) return null;

  return (
    <section className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 sm:px-6">
      {/* Sticky section nav dots */}
      <SectionNav />

      {/* Data sources summary banner */}
      <DataSourcesSummary report={report} />

      {/* Agent errors / missing agents banner */}
      {(report.meta?.agents_missing?.length ?? 0) > 0 && (
        <div className="rounded-xl border border-red-500/25 bg-red-950/15 px-5 py-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-red-400/80">
            Agent errors detected
          </div>
          <p className="text-sm text-white/60">
            {report.meta.agents_missing.length} agent(s) failed to produce analysis:{" "}
            <span className="font-medium text-red-300/80">{report.meta.agents_missing.join(", ")}</span>.
            Results below may be incomplete.
          </p>
        </div>
      )}

      {/* Consistency issues banner */}
      {(report.consistency_report?.unresolved_gaps?.length ?? 0) > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-950/12 px-5 py-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400/70">
            Unresolved gaps
          </div>
          {report.consistency_report.unresolved_gaps.map((gap, i) => (
            <p key={i} className="text-sm text-white/55">{gap}</p>
          ))}
        </div>
      )}

      {/* ── Step 1: What is this policy? ── */}
      <div id="section-overview">
        <StepBadge n={1} label="Policy overview" />
      </div>
      <PolicyHeader report={report} />
      <KpiStrip metrics={report.headline_metrics ?? []} />

      {/* ── Step 2: Where does the money go? ── */}
      {report.waterfall && (
        <>
          <div id="section-waterfall">
            <StepBadge n={2} label="Where does the money go?" />
          </div>
          <Card>
            <SectionHeading
              label={report.waterfall?.title ?? "Household Budget Waterfall"}
              sub="Every dollar of the transfer, traced through taxes, rent, and prices to your net monthly gain"
            />
            <WaterfallChart data={report.waterfall} />
          </Card>
        </>
      )}

      {/* ── Step 3: What gets more expensive? ── */}
      <div id="section-categories">
        <StepBadge n={3} label="What gets more expensive?" />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeading
            label="Spending category impacts"
            sub="How much each budget line rises — click any row for detail"
          />
          {report.category_breakdown?.categories && (
            <CategoryChart categories={report.category_breakdown.categories} />
          )}
        </Card>

        <Card>
          <SectionHeading
            label="When will you feel it?"
            sub="Net monthly benefit over time as prices adjust"
          />
          {report.timeline?.phases && (
            <TimelineChart
              phases={report.timeline.phases}
              household_profile={report.timeline.household_profile}
            />
          )}
        </Card>
      </div>

      {/* ── Step 4: Who wins and who loses? ── */}
      <div id="section-winners">
        <StepBadge n={4} label="Who wins and who loses?" />
      </div>
      <Card>
        <SectionHeading
          label="Who benefits — who doesn't"
          sub="Outcomes vary dramatically by income level, housing tenure, and geography"
        />
        {report.winners_losers && <WinnersLosers data={report.winners_losers} />}
      </Card>

      {/* ── Step 5: Does location matter? ── */}
      {(report.geographic_impact?.regions?.length ?? 0) > 0 && (
        <>
          <div id="section-geography">
            <StepBadge n={5} label="Does location matter?" />
          </div>
          <Card>
            <SectionHeading
              label="Impact by region"
              sub="Geographic variation in how this policy affects households"
            />
            <GeographicImpact regions={report.geographic_impact.regions} />
          </Card>
        </>
      )}

      {/* ── Step 6: How certain is this? ── */}
      <div id="section-confidence">
        <StepBadge n={6} label="How certain is this?" />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeading
            label="Confidence by component"
            sub="Closer to the edge = higher confidence. Inner = more uncertain."
          />
          {report.confidence_assessment && (
            <ConfidenceRadar data={report.confidence_assessment} />
          )}
        </Card>

        <Card>
          <SectionHeading
            label="What this means for you"
            sub="Select your situation to see a plain-language summary"
          />
          {report.narrative && <NarrativePanel narrative={report.narrative} />}
        </Card>
      </div>

      {/* Evidence summary — only if we have citations */}
      {(report.evidence_summary?.key_studies?.length ?? 0) > 0 && (
        <Card>
          <SectionHeading
            label={report.evidence_summary?.title ?? "What the Research Says"}
            sub="Citations aggregated from sector agent analyses"
          />
          <EvidenceSummary data={report.evidence_summary} />
        </Card>
      )}

      {/* Methodology notes */}
      {(report.data_sources?.methodology_notes?.length ?? 0) > 0 && (
        <Card className="border-white/8 bg-white/[0.02]">
          <SectionHeading
            label="Methodology"
            sub="How this analysis was produced"
          />
          <div className="space-y-1.5">
            {report.data_sources.methodology_notes.map((note, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm text-white/50">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400/40" />
                {note}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Step 7: What you can do ── */}
      <div id="section-actions">
        <StepBadge n={7} label="What you can do about it" />
      </div>
      <ActionableSteps report={report} />

      {/* Cost transparency footer */}
      <footer className="rounded-2xl border border-white/8 bg-white/[0.02] px-5 py-4">
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs text-white/35">
          <span>{report.meta?.total_tool_calls ?? 0} tool calls</span>
          <span className="text-white/10">|</span>
          <span>{report.meta?.agents_completed?.length ?? 0} agents completed</span>
          <span className="text-white/10">|</span>
          <span>{report.meta?.pipeline_duration_seconds ?? 0}s total</span>
          <span className="text-white/10">|</span>
          <span>{report.meta?.model_used ?? "LLM"}</span>
        </div>
        <div className="mt-2 text-center text-[11px] text-white/20">
          Estimated cost: ~$0.12 (LLM) + 66 sats / ~$0.02 (Lightning) = <span className="text-white/40 font-medium">~$0.14 total</span>
          <span className="mx-2 text-white/10">|</span>
          All government data APIs: $0
        </div>
      </footer>
    </section>
  );
}