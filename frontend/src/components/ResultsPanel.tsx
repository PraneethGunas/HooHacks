"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import SankeyDiagram from "@/components/SankeyDiagram";

// ─── Types (permissive — API sends inconsistent casing) ───────────────────────

interface HeadlineMetric {
  id: string;
  label: string;
  value: string;
  range: { low: string; central: string; high: string } | null;
  direction: string; // "Positive" | "Negative" | "positive" | "negative"
  confidence: string; // mixed casing from API
  context: string;
}

interface WaterfallStep {
  label: string;
  value: number;
  cumulative: number;
  type: string; // "base" | "income" | "cost" | "net" | "inflow" | "outflow"
  note: string | null;
}

interface WaterfallData {
  title: string;
  subtitle: string;
  household_profile: string;
  steps: WaterfallStep[];
  net_monthly: number;
  net_annual: number;
  pct_of_income: number;
}

interface CategoryItem {
  name: string;
  dollar_impact_monthly: { low: number; central: number; high: number };
  pct_change: { low: number; central: number; high: number };
  confidence: string;
  explanation: string;
  note?: string;
}

interface TimelinePhase {
  label: string;
  cumulative_net_monthly: { low: number; central: number; high: number };
  what_happens: string[];
  mood: string;
  dominant_driver: string;
}

interface WinnerLoserProfile {
  profile: string;
  net_monthly_range: string;
  pct_of_income_range: string;
  why: string;
  confidence: string;
  impact_quality?: string;
  caveat?: string;
  depends_on?: string;
}

interface GeographicRegion {
  id: string;
  name: string;
  examples: string;
  color: string;
  rent_impact_severity: string; // "Neutral" | "High" | "Low" | "Medium"
  price_impact_severity: string;
  net_monthly_range_median_hh: string;
  explanation: string;
  key_factor: string;
}

interface ImpactMatrixCell {
  income: string;
  type: string;
  geography: string;
  net_monthly?: { low: number; central: number; high: number };
  pct_of_income?: { low: number; central: number; high: number };
  confidence?: string;
  verdict?: string;
  note?: string;
}

interface SankeyData {
  nodes: Array<{ id: string; label: string; category: "policy" | "sector" | "effect" | "outcome" }>;
  links: Array<{ source: string; target: string; value: number; label?: string }>;
}

interface FullReport {
  meta: {
    pipeline_duration_seconds: number;
    total_tool_calls: number;
    agents_completed: string[];
    model_used: string;
  };
  policy: {
    title: string;
    one_liner: string;
    geography: string;
    estimated_annual_cost?: string;
  };
  headline: {
    verdict: string;
    bottom_line: string;
    confidence: string;
    confidence_explanation?: string;
  };
  headline_metrics: HeadlineMetric[];
  waterfall: WaterfallData;
  impact_matrix?: { cells?: ImpactMatrixCell[] };
  category_breakdown?: { categories?: CategoryItem[] };
  timeline?: { phases?: TimelinePhase[]; household_profile?: string };
  winners_losers?: {
    winners?: WinnerLoserProfile[];
    losers?: WinnerLoserProfile[];
    mixed?: WinnerLoserProfile[];
    distributional_verdict?: { progressive_or_regressive?: string; explanation?: string };
  };
  geographic_impact?: { regions?: GeographicRegion[] };
  confidence_assessment?: {
    weakest_link?: string;
    what_would_change_conclusion?: string[];
    by_component?: { component: string; confidence: string; reasoning: string }[];
  };
  narrative?: {
    executive_summary?: string;
    for_low_income?: string;
    for_middle_income?: string;
    for_upper_income?: string;
    for_small_business?: string;
    biggest_uncertainty?: string;
  };
  data_sources?: {
    agents_and_calls?: Array<{ tool_calls?: number }>;
    total_tool_calls?: number;
  };
  sankey_data?: SankeyData;
}

interface ResultsPanelProps {
  report: FullReport;
}

// ─── Safe helpers ─────────────────────────────────────────────────────────────

const CONF_STYLES = {
  HIGH:   { pill: "border-emerald-500/30 bg-emerald-950/40 text-emerald-400", dot: "bg-emerald-400", label: "High confidence" },
  MEDIUM: { pill: "border-amber-500/25 bg-amber-950/30 text-amber-400",      dot: "bg-amber-400",   label: "Medium confidence" },
  LOW:    { pill: "border-slate-500/30 bg-slate-800/40 text-slate-400",       dot: "bg-slate-400",   label: "Low confidence" },
} as const;

function getConfStyle(raw: unknown) {
  if (typeof raw !== "string" || !raw) return CONF_STYLES.MEDIUM;
  const key = raw.toUpperCase();
  const confMap: Record<string, (typeof CONF_STYLES)[keyof typeof CONF_STYLES]> = CONF_STYLES;
  return confMap[key] ?? CONF_STYLES.MEDIUM;
}

// "Neutral" maps to near-zero bar; handles any casing
const SEVERITY_MAP: Record<string, { bar: string; text: string; label: string; width: string }> = {
  HIGH:    { bar: "bg-orange-400/70", text: "text-orange-400", label: "High",    width: "75%" },
  MEDIUM:  { bar: "bg-amber-400/60",  text: "text-amber-400",  label: "Medium",  width: "48%" },
  LOW:     { bar: "bg-teal-400/60",   text: "text-teal-400",   label: "Low",     width: "22%" },
  NEUTRAL: { bar: "bg-slate-500/35",  text: "text-slate-400",  label: "Neutral", width: "10%" },
};

function getSeverityStyle(raw: unknown) {
  if (typeof raw !== "string" || !raw) return SEVERITY_MAP.MEDIUM;
  return SEVERITY_MAP[raw.toUpperCase()] ?? SEVERITY_MAP.LOW;
}

function isPositive(direction: unknown): boolean {
  if (typeof direction !== "string") return false;
  const d = direction.toLowerCase();
  return d === "positive" || d === "up";
}

function isNegative(direction: unknown): boolean {
  if (typeof direction !== "string") return false;
  const d = direction.toLowerCase();
  return d === "negative" || d === "down";
}

// Normalise waterfall step type across both schema versions
function stepKind(type: unknown): "inflow" | "outflow" | "net" | "base" {
  const t = typeof type === "string" ? type.toLowerCase() : "";
  if (t === "net") return "net";
  if (t === "base") return "base";
  if (t === "inflow" || t === "income") return "inflow";
  return "outflow";
}

function safeNum(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function safeArr<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

function safeStr(v: unknown): string {
  return typeof v === "string" ? v : String(v ?? "");
}

function fmtDollar(n: number): string {
  if (n === 0) return "$0";
  const abs = Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return `${n < 0 ? "-" : "+"}$${abs}`;
}

function buildFallbackSankey(categories: CategoryItem[] | null | undefined): SankeyData | null {
  const safe = safeArr(categories).filter(Boolean);
  if (safe.length === 0) return null;

  const top = [...safe]
    .map((c) => ({
      name: safeStr(c.name).trim() || "Category",
      value: Math.abs(safeNum(c.dollar_impact_monthly?.central)),
    }))
    .filter((c) => c.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  if (top.length === 0) return null;

  const toId = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

  const nodes: SankeyData["nodes"] = [
    { id: "policy", label: "Policy shock", category: "policy" },
    ...top.map((c) => ({ id: `effect-${toId(c.name)}`, label: c.name.slice(0, 34), category: "effect" as const })),
    { id: "outcome", label: "Household net impact", category: "outcome" },
  ];

  const links: SankeyData["links"] = [
    ...top.map((c) => ({ source: "policy", target: `effect-${toId(c.name)}`, value: c.value })),
    ...top.map((c) => ({ source: `effect-${toId(c.name)}`, target: "outcome", value: c.value })),
  ];

  return { nodes, links };
}

// ─── Shared atoms ─────────────────────────────────────────────────────────────

function ConfBadge({ c }: { c: unknown }) {
  const s = getConfStyle(c);
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", s.pill)}>
      <span className={cn("mr-1.5 h-1.5 w-1.5 rounded-full", s.dot)} />
      {s.label}
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
    <div className={cn("rounded-2xl border border-white/10 bg-(--bg-surface) p-5", className)}>
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
    <div className="mb-2 flex items-center gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/8 text-xs font-semibold text-white/60">
        {n}
      </div>
      <span className="text-xs font-medium uppercase tracking-widest text-white/40">{label}</span>
      <div className="h-px flex-1 bg-white/8" />
    </div>
  );
}

// ─── 1: Hero header ───────────────────────────────────────────────────────────
// ─── 1: Hero header ───────────────────────────────────────────────────────────

function PolicyHeader({ report }: { report: FullReport }) {
  const metrics = safeArr(report.headline_metrics);
  const pos = metrics.filter((m) => isPositive(m?.direction)).length;
  const neg = metrics.filter((m) => isNegative(m?.direction)).length;
  const total = pos + neg || 1;
  const posW = Math.round((pos / total) * 100);
  const headlineConf = getConfStyle(report.headline?.confidence);
  const agentsCompleted = safeArr(report.meta?.agents_completed);

  // Prefer bottom_line when verdict appears abbreviated/cut mid-sentence.
  const verdict = safeStr(report.headline?.verdict).trim();
  const bottomLine = safeStr(report.headline?.bottom_line).trim();
  const hasStrongEnding = /[.!?]$/.test(verdict);
  const hasCutEnding = /[-,;:\u2014]$/.test(verdict);
  const muchShorterThanBottomLine =
    bottomLine.length > 0 && verdict.length > 0 && verdict.length <= Math.floor(bottomLine.length * 0.45);
  const looksAbbreviated = hasCutEnding || (!hasStrongEnding && muchShorterThanBottomLine);
  const displayVerdict = looksAbbreviated && bottomLine ? bottomLine : (verdict || bottomLine);

  return (
    <Card className="p-6">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {report.policy?.geography && (
          <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-xs text-white/55">
            {report.policy.geography}
          </span>
        )}
        {agentsCompleted.length > 0 && (
          <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-xs text-white/55">
            {agentsCompleted.length} agents
          </span>
        )}
        {report.policy?.estimated_annual_cost && (
          <span className="rounded-full border border-orange-500/25 bg-orange-950/25 px-3 py-1 text-xs text-orange-300/80">
            Cost: {report.policy.estimated_annual_cost}/yr
          </span>
        )}
        <span className={cn("ml-auto rounded-full border px-3 py-1 text-xs font-medium", headlineConf.pill)}>
          {headlineConf.label}
        </span>
      </div>

      <h1 className="mb-1 text-2xl font-semibold leading-snug tracking-tight text-white">
        {safeStr(report.policy?.title)}
      </h1>
      {report.policy?.one_liner && (
        <p className="mb-5 text-base text-white/50">{report.policy.one_liner}</p>
      )}

      {displayVerdict && (
        <div className="mb-5 rounded-xl border-l-4 border-emerald-500/60 bg-emerald-950/20 px-4 py-3">
          <div className="mb-0.5 text-xs font-semibold uppercase tracking-widest text-emerald-400/70">
            Overall verdict
          </div>
          <p className="text-[15px] font-medium leading-snug text-white/90">{displayVerdict}</p>
        </div>
      )}

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
// ─── 2: KPI strip ─────────────────────────────────────────────────────────────

function KpiStrip({ metrics }: { metrics: HeadlineMetric[] | null | undefined }) {
  const safe = safeArr(metrics).filter(Boolean);
  if (safe.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {safe.map((m, i) => {
        const pos = isPositive(m.direction);
        return (
          <div key={m.id ?? i}
            className={cn(
              "w-full rounded-2xl border p-5 shadow-sm",
              pos ? "border-emerald-400/35 bg-emerald-950/22" : "border-red-400/35 bg-red-950/20",
            )}>
            <div className="mb-2 text-sm font-semibold leading-tight text-white/75">{safeStr(m.label)}</div>
            <div className={cn("text-[30px] font-bold leading-none tracking-tight",
              pos ? "text-emerald-200" : "text-red-200")}>
              {safeStr(m.value)}
            </div>
            {m.range && (
              <div className="mt-2 text-xs tabular-nums text-white/45">
                {m.range.low} to {m.range.high}
              </div>
            )}
            {m.context && (
              <div className="mt-2 text-xs leading-relaxed text-white/55">{m.context}</div>
            )}
            <div className="mt-3">
              <ConfBadge c={m.confidence} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── 3: Waterfall chart ───────────────────────────────────────────────────────

function WaterfallChart({ data }: { data: WaterfallData }) {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);

  const steps = safeArr(data?.steps).filter((s) => {
    const kind = stepKind(s?.type);
    return kind !== "base" && s?.value !== 0;
  });

  if (steps.length === 0) {
    return <p className="text-sm text-white/35">No impact breakdown available.</p>;
  }

  const absVals = steps.map((s) => Math.abs(safeNum(s.value)));
  const maxVal = Math.max(...absVals, 1);

  const BAR_H = 24, BAR_GAP = 7, LABEL_W = 122, TRACK_W = 154, CUM_W = 54, PAD = 6;
  const svgH = steps.length * (BAR_H + BAR_GAP) + PAD * 2;
  const SVG_W = LABEL_W + TRACK_W + CUM_W + PAD * 3;

  const netMonthly = safeNum(data.net_monthly);
  const netAnnual = safeNum(data.net_annual);
  const pctIncome = safeNum(data.pct_of_income);
  const netIsNeg = netMonthly < 0;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-[12px] text-white/35">
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-emerald-500/50" />Gain</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-red-500/40" />Cost</span>
          <span className="text-white/20">Running total</span>
        </span>
      </div>

      <div className="w-full overflow-hidden rounded-lg border border-white/8 bg-white/2 p-2">
        <svg
          className="block w-full"
          height={svgH}
          viewBox={`0 0 ${SVG_W} ${svgH}`}
          preserveAspectRatio="xMidYMin meet"
        >
          {steps.map((step, i) => {
            const kind = stepKind(step.type);
            const isNet = kind === "net";
            const isInflow = kind === "inflow";
            const stepVal = safeNum(step.value);
            const absVal = Math.abs(stepVal);
            const barW = Math.max(4, Math.round((absVal / maxVal) * TRACK_W));
            const y = PAD + i * (BAR_H + BAR_GAP);
            const isHovered = hoveredStep === step.label;

            const barFill = isNet
              ? (stepVal < 0 ? "rgba(239,68,68,0.60)" : "rgba(52,211,153,0.65)")
              : isInflow ? "rgba(52,211,153,0.38)" : "rgba(239,68,68,0.35)";
            const textFill = isNet
              ? (stepVal < 0 ? "#fca5a5" : "#6ee7b7")
              : isInflow ? "#a7f3d0" : "#fca5a5";
            const labelFill = isNet ? "rgba(255,255,255,0.90)"
              : isHovered ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.55)";
            const cumDisplay = isNet ? stepVal : safeNum(step.cumulative);

            return (
              <g key={`${step.label}-${i}`}
                onMouseEnter={() => setHoveredStep(step.label)}
                onMouseLeave={() => setHoveredStep(null)}>
                <text x={LABEL_W - 8} y={y + BAR_H / 2}
                  textAnchor="end" dominantBaseline="central"
                  fill={labelFill} fontSize={isNet ? "12" : "11"} fontWeight={isNet ? "600" : "400"}>
                  {safeStr(step.label)}
                </text>
                <rect x={LABEL_W + PAD} y={y} width={TRACK_W} height={BAR_H} rx="6"
                  fill={isHovered ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.03)"} />
                <rect x={LABEL_W + PAD} y={y} width={barW} height={BAR_H} rx="6" fill={barFill} />
                {barW > 54 ? (
                  <text x={LABEL_W + PAD + barW - 8} y={y + BAR_H / 2}
                    textAnchor="end" dominantBaseline="central" fill={textFill} fontSize="11" fontWeight="500">
                    {fmtDollar(stepVal)}
                  </text>
                ) : (
                  <text x={LABEL_W + PAD + barW + 6} y={y + BAR_H / 2}
                    dominantBaseline="central" fill={textFill} fontSize="11">
                    {fmtDollar(stepVal)}
                  </text>
                )}
                <text x={SVG_W - PAD} y={y + BAR_H / 2}
                  textAnchor="end"
                  dominantBaseline="central"
                  fill="rgba(255,255,255,0.28)" fontSize="11" fontFamily="monospace">
                  {fmtDollar(cumDisplay)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3">
        {[
          { label: "Net monthly", value: fmtDollar(netMonthly), neg: netIsNeg },
          { label: "Net annual",  value: fmtDollar(netAnnual),  neg: netAnnual < 0 },
          pctIncome !== 0
            ? { label: "% of income", value: `${pctIncome > 0 ? "+" : ""}${pctIncome}%`, neg: pctIncome < 0 }
            : { label: "Annual impact", value: fmtDollar(netAnnual), neg: netAnnual < 0 },
        ].map((s) => (
          <div key={s.label}
            className={cn("rounded-xl border p-3 text-center",
              s.neg ? "border-red-500/20 bg-red-950/15" : "border-emerald-500/20 bg-emerald-950/15")}>
            <div className="text-xs text-white/40">{s.label}</div>
            <div className={cn("mt-1 text-base font-semibold sm:text-lg", s.neg ? "text-red-300" : "text-emerald-300")}>
              {s.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── 4: Category chart ────────────────────────────────────────────────────────

function CategoryChart({ categories }: { categories: CategoryItem[] | null | undefined }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const safe = safeArr(categories).filter(Boolean);
  if (safe.length === 0) return <p className="text-sm text-white/35">No category data available.</p>;

  function cleanName(name: string): string {
    const s = name.trim();
    return s.length > 32 ? s.slice(0, 30).trimEnd() + "..." : s;
  }

  const sorted = [...safe].sort(
    (a, b) => Math.abs(safeNum(b.dollar_impact_monthly?.central)) - Math.abs(safeNum(a.dollar_impact_monthly?.central)),
  );
  const maxAbs = Math.max(...sorted.map((c) => Math.abs(safeNum(c.dollar_impact_monthly?.central))), 1);

  const BAR_H = 28, BAR_GAP = 7, LABEL_W = 180, TRACK_W = 200, VAL_W = 88, PAD = 8;
  const svgH = sorted.length * (BAR_H + BAR_GAP) + PAD * 2;
  const SVG_W = LABEL_W + TRACK_W + VAL_W + PAD * 2;

  return (
    <div>
      <div className="max-w-full overflow-x-auto overflow-y-hidden">
        <svg width="100%" viewBox={`0 0 ${SVG_W} ${svgH}`} style={{ minWidth: 420 }}>
          {sorted.map((cat, i) => {
            const central = safeNum(cat.dollar_impact_monthly?.central);
            const isNeg = central < 0;
            const barW = Math.max(4, Math.round((Math.abs(central) / maxAbs) * TRACK_W));
            const y = PAD + i * (BAR_H + BAR_GAP);
            const barFill = isNeg ? "rgba(249,115,22,0.38)" : "rgba(52,211,153,0.38)";
            const valFill = isNeg ? "#fdba74" : "#6ee7b7";
            const isActive = expanded === cat.name;

            return (
              <g key={cat.name ?? i} className="cursor-pointer"
                onClick={() => setExpanded(isActive ? null : cat.name)}>
                <text x={10} y={y + BAR_H / 2}
                  textAnchor="start" dominantBaseline="central"
                  fill={isActive ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.60)"}
                  fontSize="11">
                  {cleanName(safeStr(cat.name))}
                </text>
                <rect x={LABEL_W + PAD} y={y} width={TRACK_W} height={BAR_H} rx="5"
                  fill={isActive ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.04)"} />
                <rect x={LABEL_W + PAD} y={y} width={barW} height={BAR_H} rx="5" fill={barFill} />
                {barW > 32 && (
                  <text x={LABEL_W + PAD + 8} y={y + BAR_H / 2}
                    dominantBaseline="central" fill={valFill} fontSize="11" fontWeight="500">
                    {isNeg ? "" : "+"}{safeNum(cat.pct_change?.central)}%
                  </text>
                )}
                <text x={LABEL_W + PAD + TRACK_W + 10} y={y + BAR_H / 2}
                  dominantBaseline="central" fill={valFill} fontSize="12" fontWeight="500" fontFamily="monospace">
                  {fmtDollar(central)}/mo
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {expanded && (() => {
        const cat = sorted.find((c) => c.name === expanded);
        if (!cat) return null;
        return (
          <div className="mt-3 overflow-hidden rounded-xl border border-white/10 bg-white/3 p-4">
            <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
              <span className="min-w-0 wrap-break-word text-sm font-semibold leading-snug text-white/85">{cleanName(safeStr(cat.name))}</span>
              <ConfBadge c={cat.confidence} />
            </div>
            <p className="mb-2 wrap-break-word text-sm leading-relaxed text-white/55">{safeStr(cat.explanation)}</p>
            {cat.note && <p className="mb-2 wrap-break-word text-xs leading-relaxed text-amber-300/70">{cat.note}</p>}
            <div className="wrap-break-word text-xs tabular-nums text-white/30">
              Range: {fmtDollar(safeNum(cat.dollar_impact_monthly?.low))} to {fmtDollar(safeNum(cat.dollar_impact_monthly?.high))}/mo
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ─── 5: Timeline chart ────────────────────────────────────────────────────────

function TimelineChart({
  phases,
  household_profile,
}: {
  phases: TimelinePhase[] | null | undefined;
  household_profile: string;
}) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const safe = safeArr(phases).filter(Boolean);
  if (safe.length === 0) return <p className="text-sm text-white/35">No timeline data available.</p>;

  if (safe.length < 2) {
    return (
      <div className="space-y-2">
        {safe.map((p, i) => (
          <div key={i} className="rounded-lg border border-white/8 px-3 py-2.5">
            <div className="text-sm font-medium text-white/65">{safeStr(p.label)}</div>
            <div className={cn("text-sm tabular-nums font-semibold",
              safeNum(p.cumulative_net_monthly?.central) < 0 ? "text-red-300" : "text-emerald-300")}>
              {fmtDollar(safeNum(p.cumulative_net_monthly?.central))}/mo
            </div>
          </div>
        ))}
      </div>
    );
  }

  const allVals = safe.flatMap((p) => [
    safeNum(p.cumulative_net_monthly?.low),
    safeNum(p.cumulative_net_monthly?.central),
    safeNum(p.cumulative_net_monthly?.high),
  ]);
  const minVal = Math.min(...allVals);
  const maxVal = Math.max(...allVals);
  const chartMin = minVal < 0 ? minVal * 1.15 : 0;
  const chartMax = maxVal > 0 ? maxVal * 1.15 : maxVal * 0.85;
  const chartRange = Math.abs(chartMax - chartMin) || 1;

  const W = 540, H = 160, PL = 58, PR = 20, PT = 16, PB = 40;
  const iW = W - PL - PR;
  const iH = H - PT - PB;
  const xOf = (i: number) => PL + (i / (safe.length - 1)) * iW;
  const yOf = (v: number) => PT + iH - ((safeNum(v) - chartMin) / chartRange) * iH;

  const showZeroLine = chartMin < 0 && chartMax > 0;
  const allNeg = allVals.every((v) => v <= 0);
  const lineColor = allNeg ? "#f87171" : "#34d399";
  const bandFill = allNeg ? "rgba(248,113,113,0.08)" : "rgba(52,211,153,0.08)";

  const highPts = safe.map((p, i) => `${xOf(i)},${yOf(safeNum(p.cumulative_net_monthly?.high))}`).join(" ");
  const lowPtsRev = [...safe].reverse().map((p, i) =>
    `${xOf(safe.length - 1 - i)},${yOf(safeNum(p.cumulative_net_monthly?.low))}`
  ).join(" ");
  const centralPts = safe.map((p, i) => `${xOf(i)},${yOf(safeNum(p.cumulative_net_monthly?.central))}`).join(" ");

  const moodColor: Record<string, string> = {
    optimistic: "#34d399", stable: "#60a5fa", settling: "#f59e0b",
    new_normal: "#c4b5fd", uncertain: "#94a3b8",
  };

  const yTicks = [chartMin, (chartMin + chartMax) / 2, chartMax].map(Math.round);

  return (
    <div>
      {household_profile && (
        <div className="mb-3 text-xs text-white/35">{household_profile}</div>
      )}
      <div className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 380 }}>
          {yTicks.map((t) => (
            <g key={t}>
              <line x1={PL} y1={yOf(t)} x2={W - PR} y2={yOf(t)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
              <text x={PL - 6} y={yOf(t)} textAnchor="end" dominantBaseline="central"
                fill="rgba(255,255,255,0.28)" fontSize="10">
                {fmtDollar(t)}
              </text>
            </g>
          ))}
          {showZeroLine && (
            <line x1={PL} y1={yOf(0)} x2={W - PR} y2={yOf(0)}
              stroke="rgba(255,255,255,0.20)" strokeWidth="1" strokeDasharray="4 3" />
          )}
          <polygon points={`${highPts} ${lowPtsRev}`} fill={bandFill} />
          <polyline points={centralPts} fill="none" stroke={lineColor} strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round" />
          {safe.map((p, i) => {
            const x = xOf(i);
            const central = safeNum(p.cumulative_net_monthly?.central);
            const y = yOf(central);
            const active = activeIdx === i;
            const moodKey = safeStr(p.mood).toLowerCase().split(" ")[0];
            const color = moodColor[moodKey] ?? "#94a3b8";
            const low = safeNum(p.cumulative_net_monthly?.low);
            const high = safeNum(p.cumulative_net_monthly?.high);
            const tooltipX = Math.max(PL, Math.min(x - 65, W - 160));
            const tooltipY = y < PT + 55 ? y + 10 : y - 55;
            const shortLabel = safeStr(p.label).split(" ")[0];
            return (
              <g key={`pt-${i}`} onMouseEnter={() => setActiveIdx(i)} onMouseLeave={() => setActiveIdx(null)}>
                {active && (
                  <line x1={x} y1={PT} x2={x} y2={H - PB}
                    stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
                )}
                <circle cx={x} cy={y} r={active ? 5 : 3.5} fill={color} stroke="#111318" strokeWidth="2" className="cursor-pointer" />
                {active && (
                  <g>
                    <rect x={tooltipX} y={tooltipY} width={150} height={44} rx="6"
                      fill="#181C23" stroke="rgba(255,255,255,0.12)" strokeWidth="0.5" />
                    <text x={tooltipX + 10} y={tooltipY + 16} fill="rgba(255,255,255,0.88)" fontSize="13" fontWeight="600">
                      {fmtDollar(central)}/mo
                    </text>
                    <text x={tooltipX + 10} y={tooltipY + 32} fill="rgba(255,255,255,0.38)" fontSize="10">
                      {fmtDollar(low)} to {fmtDollar(high)}
                    </text>
                  </g>
                )}
                <text x={x} y={H - PB + 14} textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize="9">
                  {shortLabel}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-2 space-y-1.5">
        {safe.map((p, i) => {
          const moodKey = safeStr(p.mood).toLowerCase().split(" ")[0];
          const color = moodColor[moodKey] ?? "#94a3b8";
          const central = safeNum(p.cumulative_net_monthly?.central);
          const isActive = activeIdx === i;
          return (
            <div key={`row-${i}`}
              className={cn("flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
                isActive ? "border-white/14 bg-white/5" : "border-white/6 hover:border-white/10")}
              onMouseEnter={() => setActiveIdx(i)} onMouseLeave={() => setActiveIdx(null)}>
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
              <span className="w-32 shrink-0 text-sm font-medium text-white/65">{safeStr(p.label)}</span>
              <span className="flex-1 truncate text-sm text-white/38">{safeStr(p.dominant_driver)}</span>
              <span className={cn("shrink-0 tabular-nums text-sm font-semibold",
                central < 0 ? "text-red-300" : "text-emerald-300")}>
                {fmtDollar(central)}/mo
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── 6: Winners & Losers ──────────────────────────────────────────────────────
// ─── 6: Winners & Losers ──────────────────────────────────────────────────────

type CardType = "winner" | "loser" | "mixed";
type WLTab = "winners" | "losers" | "mixed";

const CARD_STYLES: Record<CardType, { border: string; bg: string; dot: string; num: string }> = {
  winner: { border: "border-emerald-500/20", bg: "bg-emerald-950/12", dot: "bg-emerald-400", num: "text-emerald-300" },
  loser:  { border: "border-orange-500/20",  bg: "bg-orange-950/10",  dot: "bg-orange-400",  num: "text-orange-300" },
  mixed:  { border: "border-amber-500/18",   bg: "bg-amber-950/10",   dot: "bg-amber-400",   num: "text-amber-300" },
};

function tabToCardType(tab: WLTab): CardType {
  if (tab === "winners") return "winner";
  if (tab === "losers")  return "loser";
  return "mixed";
}

function ProfileCard({ profile, cardType }: { profile: WinnerLoserProfile; cardType: CardType }) {
  const [open, setOpen] = useState(false);
  const styles = CARD_STYLES[cardType] ?? CARD_STYLES.mixed;

  const numStr = safeStr(profile.net_monthly_range);
  const isVariable = numStr.toLowerCase() === "variable" || numStr === "";
  const isNegNum = numStr.startsWith("-");

  return (
    <div className={cn("rounded-xl border p-4", styles.border, styles.bg)}>
      <div className="mb-2 flex items-start gap-2">
        <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", styles.dot)} />
        <span className="text-sm font-semibold leading-snug text-white/85">{safeStr(profile.profile)}</span>
      </div>
      <div className={cn("mb-1 text-xl font-semibold leading-none tabular-nums",
        isVariable ? "text-amber-300" : isNegNum ? "text-red-300" : styles.num)}>
        {numStr || "Variable"}
        {!isVariable && <span className="ml-1 text-sm font-normal text-white/35">/mo</span>}
      </div>
      {profile.pct_of_income_range && profile.pct_of_income_range !== "N/A" && (
        <div className="mb-3 text-xs text-white/35">{profile.pct_of_income_range} of income</div>
      )}
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-white/35 transition-colors hover:text-white/60">
        Why? <Chevron open={open} />
      </button>
      {open && (
        <div className="mt-3 space-y-2 border-t border-white/8 pt-3">
          <p className="text-sm leading-6 text-white/55">{safeStr(profile.why)}</p>
          {profile.caveat && <p className="text-xs text-amber-300/65">{profile.caveat}</p>}
          {profile.depends_on && (
            <p className="text-xs text-white/30">Depends on: {profile.depends_on}</p>
          )}
          <ConfBadge c={profile.confidence} />
        </div>
      )}
    </div>
  );
}

function WinnersLosers({ data }: { data: NonNullable<FullReport["winners_losers"]> }) {
  const [tab, setTab] = useState<WLTab>("winners");

  const winners = safeArr(data?.winners);
  const losers  = safeArr(data?.losers);
  const mixed   = safeArr(data?.mixed);

  const tabs: { key: WLTab; label: string; activeClass: string; count: number }[] = [
    { key: "winners", label: "Winners",        count: winners.length, activeClass: "border-emerald-500/35 bg-emerald-950/30 text-emerald-300" },
    { key: "losers",  label: "Losers / risks", count: losers.length,  activeClass: "border-orange-500/35 bg-orange-950/25 text-orange-300" },
    { key: "mixed",   label: "Mixed",           count: mixed.length,   activeClass: "border-amber-500/30 bg-amber-950/25 text-amber-300" },
  ];

  const profileMap: Record<WLTab, WinnerLoserProfile[]> = { winners, losers, mixed };
  const activeProfiles = profileMap[tab] ?? [];
  const cardType = tabToCardType(tab);

  const verdictText = safeStr(data?.distributional_verdict?.progressive_or_regressive);
  const verdictExpl = safeStr(data?.distributional_verdict?.explanation);

  return (
    <div className="space-y-4">
      {verdictText && (
        <div className="rounded-xl border border-white/10 bg-white/3 px-5 py-4">
          <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-white/40">
            Distributional verdict
          </div>
          <p className="text-sm leading-6 text-white/75">{verdictText}</p>
          {verdictExpl && <p className="mt-1 text-sm text-white/45">{verdictExpl}</p>}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={cn("rounded-full border px-4 py-1.5 text-sm font-medium transition-all duration-150",
              tab === t.key ? t.activeClass : "border-white/10 text-white/40 hover:text-white/65")}>
            {t.label}
            <span className="ml-1.5 text-xs opacity-60">({t.count})</span>
            <span className="ml-1.5 text-xs opacity-60">({t.count})</span>
          </button>
        ))}
      </div>

      {activeProfiles.length === 0 ? (
        <p className="text-sm text-white/35">No profiles in this group.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {activeProfiles.map((p, i) => (
            <ProfileCard key={safeStr(p.profile) || String(i)} profile={p} cardType={cardType} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 7: Geographic impact ─────────────────────────────────────────────────────
// ─── 7: Geographic impact ─────────────────────────────────────────────────────

function GeographicImpact({ regions }: { regions: GeographicRegion[] | null | undefined }) {
  const safe = safeArr(regions).filter(Boolean);
  if (safe.length === 0) return <p className="text-sm text-white/35">No geographic data available.</p>;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {safe.map((r, i) => {
        const rentSv  = getSeverityStyle(r.rent_impact_severity);
        const priceSv = getSeverityStyle(r.price_impact_severity);
        return (
          <div key={r.id ?? i} className="rounded-xl border border-white/10 bg-(--bg-surface) p-5">
            <div className="mb-1 text-base font-semibold text-white/88">{safeStr(r.name)}</div>
            {r.examples && <div className="mb-3 text-xs text-white/35">{r.examples}</div>}
            {r.net_monthly_range_median_hh && (
              <div className="mb-3 text-2xl font-semibold" style={{ color: r.color || "#94a3b8" }}>
                {r.net_monthly_range_median_hh}
                <span className="ml-1 text-sm font-normal text-white/30">/mo</span>
              </div>
            )}
            <div className="mb-4 space-y-2.5">
              {[
                { label: "Rent pressure",  sv: rentSv },
                { label: "Price pressure", sv: priceSv },
              ].map((s) => (
                <div key={s.label}>
                  <div className="mb-1.5 flex justify-between text-xs text-white/40">
                    <span>{s.label}</span>
                    <span className={s.sv.text}>{s.sv.label}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/8">
                    <div className={cn("h-full rounded-full transition-all", s.sv.bar)}
                      style={{ width: s.sv.width }} />
                  </div>
                </div>
              ))}
            </div>
            {r.explanation && <p className="text-xs leading-4 text-white/50">{r.explanation}</p>}
            {r.key_factor && <p className="mt-2 text-xs text-white/30">{r.key_factor}</p>}
          </div>
        );
      })}
    </div>
  );
}

// ─── 8: Confidence radar ──────────────────────────────────────────────────────

function ConfidenceRadar({ data }: { data: NonNullable<FullReport["confidence_assessment"]> }) {
  const [expandedScenario, setExpandedScenario] = useState(false);

  const components = safeArr(data?.by_component).filter(Boolean).slice(0, 6);
  const scenarios  = safeArr(data?.what_would_change_conclusion);
  const scores: Record<string, number> = { HIGH: 1, MEDIUM: 0.55, LOW: 0.2 };

  const SIZE = 180, cx = SIZE / 2, cy = SIZE / 2, R = 68;
  const n = components.length;

  if (n === 0) {
    return data?.weakest_link ? (
      <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 px-4 py-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400/70">Key uncertainty</div>
        <p className="text-sm font-medium text-white/80">{data.weakest_link}</p>
      </div>
    ) : null;
  }

  function polarPt(i: number, r: number) {
    const angle = (i * 2 * Math.PI) / n - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  }

  const dataPoints = components.map((c, i) => {
    const key = safeStr(c.confidence).toUpperCase();
    return polarPt(i, R * (scores[key] ?? 0.55));
  });
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ") + "Z";

  return (
    <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
      <div className="shrink-0 self-center lg:self-start">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          {[0.33, 0.67, 1].map((lvl) => {
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
            const words = safeStr(c.component).split(" ").slice(0, 2).join(" ");
            return (
              <text key={i} x={pt.x} y={pt.y} textAnchor="middle" dominantBaseline="central"
                fill="rgba(255,255,255,0.45)" fontSize="10">
                {words}
              </text>
            );
          })}
        </svg>
      </div>

      <div className="w-full flex-1 space-y-2.5">
        {data?.weakest_link && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 px-4 py-3">
            <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400/70">Key uncertainty</div>
            <p className="text-sm font-medium text-white/80">{data.weakest_link}</p>
          </div>
        )}

        {components.map((c, i) => (
          <div key={safeStr(c.component) || String(i)}
            className="flex items-start gap-3 rounded-lg border border-white/7 px-3 py-2.5">
            <ConfBadge c={c.confidence} />
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white/65">{safeStr(c.component)}</div>
              {c.reasoning && <div className="text-xs text-white/35">{c.reasoning}</div>}
            </div>
          </div>
        ))}

        {scenarios.length > 0 && (
          <>
            <button onClick={() => setExpandedScenario(!expandedScenario)}
              className="flex w-full items-center gap-2 rounded-lg border border-white/7 px-3 py-2.5 text-sm text-white/45 transition-colors hover:text-white/65">
              <span className="flex-1 text-left">{scenarios.length} scenarios that change this conclusion</span>
              <Chevron open={expandedScenario} />
            </button>
            {expandedScenario && (
              <div className="space-y-2 rounded-xl border border-white/8 bg-white/2 p-3">
                {scenarios.map((item, i) => (
                  <div key={i} className="flex gap-2.5 text-sm text-white/50">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400/50" />
                    {safeStr(item)}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── 9: Narrative tabs ────────────────────────────────────────────────────────

type NarrativeTab = "typical" | "most_impacted" | "least_impacted";

function NarrativePanel({
  narrative,
  impactMatrix,
}: {
  narrative?: FullReport["narrative"];
  impactMatrix?: FullReport["impact_matrix"];
}) {
  const [activeTab, setActiveTab] = useState<NarrativeTab>("typical");

  const cells = safeArr(impactMatrix?.cells).filter(Boolean);
  const sortedByImpact = [...cells].sort(
    (a, b) => safeNum(a.net_monthly?.central) - safeNum(b.net_monthly?.central),
  );

  const typicalCell = cells.find((c) => {
    const income = safeStr(c.income).toLowerCase();
    const geo = safeStr(c.geography).toLowerCase();
    const household = safeStr(c.type).toLowerCase();
    return income.includes("75") && geo.includes("suburban") && household.includes("children");
  }) ?? sortedByImpact[Math.floor(sortedByImpact.length / 2)] ?? null;

  const mostImpactedCell = sortedByImpact[0] ?? null;
  const leastImpactedCell = sortedByImpact[sortedByImpact.length - 1] ?? null;

  const tabs: { key: NarrativeTab; label: string; cell: ImpactMatrixCell | null }[] = [
    { key: "typical", label: "Typical household", cell: typicalCell },
    { key: "most_impacted", label: "Most impacted", cell: mostImpactedCell },
    { key: "least_impacted", label: "Least impacted", cell: leastImpactedCell },
  ];

  const activeCell = tabs.find((t) => t.key === activeTab)?.cell ?? null;

  function buildSummary(cell: ImpactMatrixCell | null): string {
    if (!cell) return "No impact-matrix profile is available yet for this view.";

    const monthly = safeNum(cell.net_monthly?.central);
    const pct = safeNum(cell.pct_of_income?.central);
    const impactLabel = monthly < 0 ? "monthly loss" : "monthly gain";

    return `${safeStr(cell.income)} ${safeStr(cell.type)} in ${safeStr(cell.geography)}: ${impactLabel} of ${fmtDollar(monthly)} (${pct > 0 ? "+" : ""}${pct}% of income).`;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={cn("rounded-full border px-4 py-1.5 text-sm font-medium transition-all duration-150",
              activeTab === t.key
                ? "border-white/22 bg-white/10 text-white/90"
                : "border-white/8 text-white/40 hover:text-white/65")}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="mb-5 rounded-lg border border-white/8 bg-white/2 p-3">
        <p className="text-sm leading-7 text-white/65">{buildSummary(activeCell)}</p>
        {activeCell && (
          <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-white/40 sm:grid-cols-2">
            <div>Confidence: {safeStr(activeCell.confidence) || "N/A"}</div>
            <div>Verdict: {safeStr(activeCell.verdict) || "N/A"}</div>
            {activeCell.note && <div className="sm:col-span-2">{safeStr(activeCell.note)}</div>}
          </div>
        )}
      </div>

      {/* Intentionally omit global context/uncertainty here because this panel is now driven by per-cell impact_matrix data. */}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function ResultsPanel({ report }: ResultsPanelProps) {
  if (!report) {
    return (
      <section className="mx-auto w-full max-w-5xl px-4 py-12 text-center">
        <p className="text-white/40">No report data available.</p>
      </section>
    );
  }

  const hasCategories = safeArr(report.category_breakdown?.categories).length > 0;
  const hasTimeline   = safeArr(report.timeline?.phases).length > 0;
  const hasWinners    = report.winners_losers != null;
  const hasGeo        = safeArr(report.geographic_impact?.regions).length > 0;
  const hasConfidence = report.confidence_assessment != null;
  const hasNarrative  = report.narrative != null;
  const hasImpactMatrix = safeArr(report.impact_matrix?.cells).length > 0;
  const sankeyData = report.sankey_data ?? buildFallbackSankey(report.category_breakdown?.categories);
  const hasSankey = !!sankeyData;

  // Some backend responses leave meta.total_tool_calls as 0.
  // Fallback to data_sources sum for accurate footer display.
  const metaToolCalls = safeNum(report.meta?.total_tool_calls);
  const dataSourcesTotal = safeNum(report.data_sources?.total_tool_calls);
  const summedAgentCalls = safeArr(report.data_sources?.agents_and_calls)
    .reduce((sum, item) => sum + safeNum(item?.tool_calls), 0);
  const displayToolCalls =
    metaToolCalls > 0 ? metaToolCalls
      : dataSourcesTotal > 0 ? dataSourcesTotal
      : summedAgentCalls;

  let stepN = 1;

  return (
    <section className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 sm:px-6">

      <StepBadge n={stepN++} label="Policy overview" />
      <PolicyHeader report={report} />
      <KpiStrip metrics={report.headline_metrics} />

      {report.waterfall && (
        <>
          <StepBadge n={stepN++} label="Where does the money go?" />
          <Card>
            <SectionHeading
              label="Cashflow effects"
              sub={safeStr(report.waterfall.household_profile) || "Monthly impact traced through costs to your net position"}
            />
            <WaterfallChart data={report.waterfall} />
          </Card>
        </>
      )}

      {hasSankey && (
        <>
          <StepBadge n={stepN++} label="How effects flow" />
          <Card>
            <SectionHeading
              label="Economic flow map"
              sub="Sankey view of how policy pressure flows into household outcomes"
            />
            <SankeyDiagram data={sankeyData!} height={280} />
          </Card>
        </>
      )}

      {(hasCategories || hasTimeline) && (
        <>
          <StepBadge n={stepN++} label="What gets more expensive?" />
          <div className={cn("grid grid-cols-1 gap-4", hasCategories && hasTimeline ? "lg:grid-cols-2" : "")}>
            {hasCategories && (
              <Card>
                <SectionHeading label="Spending category impacts" sub="Click any row for detail" />
                <CategoryChart categories={report.category_breakdown?.categories} />
              </Card>
            )}
            {hasTimeline && (
              <Card>
                <SectionHeading label="When will you feel it?" sub="Net impact over time as the economy adjusts" />
                <TimelineChart
                  phases={report.timeline?.phases}
                  household_profile={safeStr(report.timeline?.household_profile)}
                />
              </Card>
            )}
          </div>
        </>
      )}

      {hasWinners && (
        <>
          <StepBadge n={stepN++} label="Who wins and who loses?" />
          <Card>
            <SectionHeading
              label="Who benefits, who does not"
              sub="Outcomes vary by income level, housing tenure, and geography"
            />
            <WinnersLosers data={report.winners_losers!} />
          </Card>
        </>
      )}

      {hasGeo && (
        <>
          <StepBadge n={stepN++} label="Does location matter?" />
          <Card>
            <SectionHeading label="Impact by region" sub="How costs and gains vary across the area" />
            <GeographicImpact regions={report.geographic_impact?.regions} />
          </Card>
        </>
      )}

      {(hasConfidence || hasNarrative || hasImpactMatrix) && (
        <>
          <StepBadge n={stepN++} label="How certain is this?" />
          <div className="grid grid-cols-1 gap-4">
            {hasConfidence && (
              <Card>
                <SectionHeading label="Confidence by component" sub="Closer to the edge = higher confidence" />
                <ConfidenceRadar data={report.confidence_assessment!} />
              </Card>
            )}
            {(hasNarrative || hasImpactMatrix) && (
              <Card>
                <SectionHeading label="What this means for you" sub="Built from household outcomes in the impact matrix" />
                <NarrativePanel narrative={report.narrative} impactMatrix={report.impact_matrix} />
              </Card>
            )}
          </div>
        </>
      )}

      <footer className="pt-2 text-center text-xs text-white/25">
        {displayToolCalls} tool calls
        {" \u00b7 "}
        {safeArr(report.meta?.agents_completed).length} agents
        {" \u00b7 "}
        {safeNum(report.meta?.pipeline_duration_seconds)}s
        {" \u00b7 "}
        {safeStr(report.meta?.model_used)}
      </footer>
    </section>
  );
}