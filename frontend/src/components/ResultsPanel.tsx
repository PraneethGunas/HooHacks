"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import SankeyDiagram from "@/components/SankeyDiagram";

// ─── Types ────────────────────────────────────────────────────────────────────

type Confidence = "HIGH" | "MEDIUM" | "LOW";
type Direction = "positive" | "negative";

interface HeadlineMetric {
  id: string;
  label: string;
  value: string;
  range: { low: string; central: string; high: string } | null;
  direction: Direction;
  confidence: Confidence;
  context: string;
}

interface WaterfallStep {
  label: string;
  value: number;
  cumulative: number;
  type: "inflow" | "outflow" | "neutral" | "net";
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
  confidence: Confidence;
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
  confidence: Confidence;
  impact_quality?: string;
  caveat?: string;
  depends_on?: string;
}

interface GeographicRegion {
  id: string;
  name: string;
  examples: string;
  color: string;
  rent_impact_severity: "HIGH" | "MEDIUM" | "LOW";
  price_impact_severity: "HIGH" | "MEDIUM" | "LOW";
  net_monthly_range_median_hh: string;
  explanation: string;
  key_factor: string;
}

interface SankeyNode {
  id: string;
  label: string;
  category: "policy" | "sector" | "effect" | "outcome";
}

interface SankeyLink {
  source: string;
  target: string;
  value: number;
  label?: string;
}

interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
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
    estimated_annual_cost: string;
  };
  headline: {
    verdict: string;
    bottom_line: string;
    confidence: Confidence;
  };
  headline_metrics: HeadlineMetric[];
  waterfall: WaterfallData;
  category_breakdown: { categories: CategoryItem[] };
  timeline: { phases: TimelinePhase[]; household_profile: string };
  winners_losers: {
    winners: WinnerLoserProfile[];
    losers: WinnerLoserProfile[];
    mixed: WinnerLoserProfile[];
    distributional_verdict: { progressive_or_regressive: string; explanation: string };
  };
  geographic_impact: { regions: GeographicRegion[] };
  sankey_data?: SankeyData | null;
  confidence_assessment: {
    weakest_link: string;
    what_would_change_conclusion: string[];
    by_component: { component: string; confidence: Confidence; reasoning: string }[];
  };
  narrative: {
    for_low_income: string;
    for_middle_income: string;
    for_upper_income: string;
    for_small_business: string;
    biggest_uncertainty: string;
  };
}

interface ResultsPanelProps {
  report: FullReport | any;
}

// ─── Safe helpers (all accept unknown/undefined input) ────────────────────────

const CONF_STYLES = {
  HIGH:   { pill: "border-emerald-500/30 bg-emerald-950/40 text-emerald-400", dot: "bg-emerald-400", label: "High confidence" },
  MEDIUM: { pill: "border-amber-500/25 bg-amber-950/30 text-amber-400",      dot: "bg-amber-400",   label: "Medium confidence" },
  LOW:    { pill: "border-slate-500/30 bg-slate-800/40 text-slate-400",       dot: "bg-slate-400",   label: "Low confidence" },
} as const;

function getConfStyle(raw: unknown) {
  if (typeof raw !== "string" || !raw) return CONF_STYLES.MEDIUM;
  const key = raw.toUpperCase();
  if (key in CONF_STYLES) {
    return CONF_STYLES[key as keyof typeof CONF_STYLES];
  }
  return CONF_STYLES.MEDIUM;
}

const SEVERITY_STYLES = {
  HIGH:   { bar: "bg-orange-400/70",  text: "text-orange-400",  label: "High",   width: "75%" },
  MEDIUM: { bar: "bg-amber-400/60",   text: "text-amber-400",   label: "Medium", width: "48%" },
  LOW:    { bar: "bg-teal-400/60",    text: "text-teal-400",    label: "Low",    width: "22%" },
} as const;

function getSeverityStyle(raw: unknown) {
  if (typeof raw !== "string" || !raw) return SEVERITY_STYLES.MEDIUM;
  const key = raw.toUpperCase();
  if (key in SEVERITY_STYLES) {
    return SEVERITY_STYLES[key as keyof typeof SEVERITY_STYLES];
  }
  return SEVERITY_STYLES.MEDIUM;
}

// Safe number: returns 0 for null/undefined/NaN/Infinity
function safeNum(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

// Safe array: returns [] for null/undefined
function safeArr<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

// Safe string: returns "" for null/undefined
function safeStr(v: unknown): string {
  return typeof v === "string" ? v : String(v ?? "");
}

function shortText(v: unknown, max = 120): string {
  const s = safeStr(v).trim();
  // Show significantly more text while keeping existing call sites unchanged.
  const effectiveMax = Math.max(1, Math.round(max * 2.5));
  if (s.length <= effectiveMax) return s;
  return `${s.slice(0, effectiveMax - 1)}...`;
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
    <div className={cn("rounded-2xl border border-white/10 bg-[var(--bg-surface)] p-5", className)}>
      {children}
    </div>
  );
}

function SectionHeading({ label, sub }: { label: string; sub?: string }) {
  return (
    <div className="mb-5">
      <h3 className="text-base font-semibold text-white/85">{label}</h3>
      {sub && <p className="mt-0.5 text-[13px] text-white/60">{sub}</p>}
    </div>
  );
}

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

// ─── 1: Impact verdict card (MINIMALIST)  ────────────────────────────────────

function PolicyHeader({ report }: { report: FullReport }) {
  const metrics = safeArr(report.headline_metrics);
  const pos = metrics.filter((m) => m?.direction === "positive").length;
  const neg = metrics.filter((m) => m?.direction === "negative").length;
  const agentsCompleted = safeArr(report.meta?.agents_completed);
  const headlineConf = getConfStyle(report.headline?.confidence);

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h1 className="mb-1 text-2xl font-bold text-white">{shortText(report.policy?.title, 80)}</h1>
          <p className="text-xs text-white/40">{report.policy?.geography}</p>
        </div>
        <ConfBadge c={report.headline?.confidence} />
      </div>

      {/* Impact verdict box with visual  */}
      <div className="relative mb-5 overflow-hidden rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <span className="text-xs font-semibold text-emerald-400">VERDICT</span>
        </div>
        <p className="text-sm font-semibold leading-snug text-white/90">
          {shortText(report.headline?.verdict, 120)}
        </p>
      </div>

      {/* Outcome ratio visual  */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-white/40">
          <span>{pos} Gains</span>
          <span>{neg} Costs</span>
        </div>
        <div className="flex h-2 overflow-hidden rounded-full bg-white/8">
          <div className="bg-emerald-500/70" style={{ width: `${pos ? Math.round((pos / (pos + neg || 1)) * 100) : 0}%` }} />
          <div className="flex-1 bg-red-500/50" />
        </div>
      </div>

      {/* Meta row */}
      <div className="mt-4 flex gap-3 text-xs text-white/40">
        <span>📊 {safeNum(report.meta?.total_tool_calls)} calls</span>
        <span>·</span>
        <span>🤖 {agentsCompleted.length} agents</span>
        <span>·</span>
        <span>💰 {report.policy?.estimated_annual_cost}</span>
      </div>
    </Card>
  );
}

function SankeyCard({ data }: { data: SankeyData | null | undefined }) {
  if (!data || safeArr(data.nodes).length < 2 || safeArr(data.links).length < 1) return null;
  return (
    <Card>
      <SectionHeading label="Economic flow map" sub="Policy dollars moving through sectors" />
      <SankeyDiagram data={data} />
    </Card>
  );
}

// ─── 2: Headline metrics (HEADLINE VISUAL GRID) ────────────────────────────────

function KpiStrip({ metrics }: { metrics: HeadlineMetric[] | null | undefined }) {
  const safe = safeArr(metrics).slice(0, 4).filter(Boolean);
  if (safe.length === 0) return null;

  const getIcon = (label: string) => {
    if (label.toLowerCase().includes("revenue")) return "💰";
    if (label.toLowerCase().includes("employment")) return "👥";
    if (label.toLowerCase().includes("price") || label.toLowerCase().includes("cost")) return "📈";
    if (label.toLowerCase().includes("household")) return "🏠";
    return "📊";
  };

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {safe.map((m) => (
        <div
          key={m.id}
          className={cn(
            "rounded-lg border p-4",
            m.direction === "positive"
              ? "border-emerald-500/25 bg-emerald-950/20"
              : "border-red-500/25 bg-red-950/20",
          )}
        >
          <div className="mb-2 text-2xl">{getIcon(m.label)}</div>
          <div className="mb-2 text-[13px] font-medium text-white/60 line-clamp-3">{shortText(m.label, 32)}</div>
          <div className={cn("text-xl font-bold",
            m.direction === "positive" ? "text-emerald-300" : "text-red-300")}>
            {shortText(m.value, 16)}
          </div>
          {m.range && (
            <div className="mt-1.5 text-[10px] text-white/35">
              {m.range.low}–{m.range.high}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── 3: Waterfall chart (MINIMAL TEXT VERSION) ────────────────────────────────

function WaterfallChart({ data }: { data: WaterfallData }) {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);

  const steps = safeArr(data?.steps).filter((s) => s?.type !== "neutral").slice(0, 8);
  if (steps.length === 0) return <p className="text-xs text-white/35">No waterfall data.</p>;

  const absVals = steps.map((s) => Math.abs(safeNum(s.value)));
  const maxVal = Math.max(...absVals, 1);

  const BAR_H = 28;
  const BAR_GAP = 4;
  const LABEL_W = 120;
  const TRACK_W = 240;
  const VAL_W = 70;
  const PAD = 8;
  const svgH = steps.length * (BAR_H + BAR_GAP) + PAD * 2;
  const SVG_W = LABEL_W + TRACK_W + VAL_W + PAD * 2;

  const netMonthly = safeNum(data.net_monthly);

  return (
    <div>
      <div className="mb-3 text-xs text-white/35">{shortText(data.subtitle, 70)}</div>

      <div className="overflow-x-auto">
        <svg width="100%" viewBox={`0 0 ${SVG_W} ${svgH}`} style={{ minWidth: 420 }}>
          {steps.map((step, i) => {
            const isNet = step.type === "net";
            const isInflow = step.type === "inflow";
            const absVal = Math.abs(safeNum(step.value));
            const pct = absVal / maxVal;
            const barW = Math.max(3, Math.round(pct * TRACK_W));
            const y = PAD + i * (BAR_H + BAR_GAP);
            const isHovered = hoveredStep === step.label;

            const barFill = isNet ? "rgba(52,211,153,0.7)" : isInflow ? "rgba(52,211,153,0.4)" : "rgba(239,68,68,0.35)";
            const textFill = isNet ? "#6ee7b7" : isInflow ? "#a7f3d0" : "#fca5a5";
            const labelFill = isHovered ? "rgba(255,255,255,0.75)" : isNet ? "rgba(255,255,255,0.70)" : "rgba(255,255,255,0.45)";
            const label = shortText(step.label, 16);

            return (
              <g key={`step-${i}`}
                onMouseEnter={() => setHoveredStep(step.label)}
                onMouseLeave={() => setHoveredStep(null)}>
                <text x={LABEL_W - 6} y={y + BAR_H / 2}
                  textAnchor="end" dominantBaseline="central"
                  fill={labelFill} fontSize="11" fontWeight={isNet ? "600" : "400"}>
                  {label}
                </text>
                <rect x={LABEL_W + PAD} y={y} width={TRACK_W} height={BAR_H} rx="5"
                  fill={isHovered ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)"} />
                <rect x={LABEL_W + PAD} y={y} width={barW} height={BAR_H} rx="5" fill={barFill} />
                <text x={LABEL_W + PAD + TRACK_W + 8} y={y + BAR_H / 2}
                  dominantBaseline="central" fill={textFill} fontSize="12" fontWeight="600" fontFamily="monospace">
                  {isInflow ? "+" : "–"}${absVal}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Net impact summary  */}
      <div className="mt-4 rounded-lg border border-emerald-500/25 bg-emerald-950/15 p-3 text-center">
        <div className="text-xs text-white/40">Net Monthly Impact</div>
        <div className={cn("text-2xl font-bold", netMonthly >= 0 ? "text-emerald-300" : "text-red-300")}>
          {netMonthly >= 0 ? "+" : ""}{netMonthly}/mo
        </div>
        <div className="mt-1 text-xs text-white/35">{netMonthly * 12 >= 0 ? "+" : ""}{netMonthly * 12}/yr</div>
      </div>
    </div>
  );
}

// ─── 4: Category chart (VISUAL ONLY) ──────────────────────────────────────────

function CategoryChart({ categories }: { categories: CategoryItem[] | null | undefined }) {
  const safe = safeArr(categories).filter(Boolean).slice(0, 6);
  if (safe.length === 0) return <p className="text-xs text-white/35">No data</p>;

  const sorted = [...safe].sort(
    (a, b) => Math.abs(safeNum(b.dollar_impact_monthly?.central)) - Math.abs(safeNum(a.dollar_impact_monthly?.central)),
  );

  return (
    <div className="space-y-2.5">
      {sorted.map((cat) => {
        const central = safeNum(cat.dollar_impact_monthly?.central);
        const pct = safeNum(cat.pct_change?.central);
        const isNeg = central < 0;
        const absVal = Math.abs(central);

        return (
          <div key={cat.name} className="group cursor-pointer">
            <div className="mb-1 flex items-end justify-between">
              <span className="text-sm font-medium text-white/75">{shortText(cat.name, 24)}</span>
              <div className="flex items-baseline gap-2">
                <span className={cn("text-sm font-bold", isNeg ? "text-red-300" : "text-emerald-300")}>
                  {isNeg ? "–" : "+"}${absVal}
                </span>
                <span className="text-xs text-white/40">{pct > 0 ? "+" : ""}{pct}%</span>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/8">
              <div
                className={cn("h-full transition-all", isNeg ? "bg-orange-500/60" : "bg-emerald-500/60")}
                style={{ width: `${Math.min(100, Math.abs(pct * 20))}%` }}
              />
            </div>
            <div className="mt-1.5 text-xs text-white/35 opacity-0 transition-opacity group-hover:opacity-100">
              {shortText(cat.explanation, 60)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── 5: Timeline chart (SIMPLIFIED) ───────────────────────────────────────────

function TimelineChart({ phases, household_profile }: { phases: TimelinePhase[] | null | undefined; household_profile: string }) {
  const safe = safeArr(phases).filter(Boolean).slice(0, 5);
  if (safe.length < 2) return <p className="text-xs text-white/35">Not enough data</p>;

  const moodEmoji: Record<string, string> = {
    optimistic: "😊", stable: "😐", settling: "🤔",
    new_normal: "📊", uncertain: "❓",
  };

  return (
    <div className="space-y-2.5">
      {safe.map((p, i) => {
        const central = safeNum(p.cumulative_net_monthly?.central);
        const emoji = moodEmoji[p.mood ?? ""] ?? "📊";

        return (
          <div key={i} className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{emoji}</span>
                <span className="text-sm font-medium text-white/75">{shortText(p.label, 18)}</span>
              </div>
              <span className={cn("text-sm font-bold", central >= 0 ? "text-emerald-300" : "text-red-300")}>
                +${central}/mo
              </span>
            </div>
            <div className="text-xs text-white/40 line-clamp-3">{shortText(p.dominant_driver, 50)}</div>
          </div>
        );
      })}
    </div>
  );
}

// ─── 6: Winners & Losers (VISUAL PROFILES)  ──────────────────────────────────

// CardType uses singular keys; WLTab uses plural — kept separate to avoid mismatch
type CardType = "winner" | "loser" | "mixed";
type WLTab = "winners" | "losers" | "mixed";

const CARD_STYLES: Record<CardType, { border: string; bg: string; dot: string; num: string; emoji: string }> = {
  winner: { border: "border-emerald-500/25", bg: "bg-emerald-950/15", dot: "bg-emerald-400", num: "text-emerald-300", emoji: "🎯" },
  loser:  { border: "border-orange-500/25",  bg: "bg-orange-950/12",  dot: "bg-orange-400",  num: "text-orange-300", emoji: "⚠️" },
  mixed:  { border: "border-amber-500/20",   bg: "bg-amber-950/12",   dot: "bg-amber-400",   num: "text-amber-300", emoji: "⚖️" },
};

function tabToCardType(tab: WLTab): CardType {
  if (tab === "winners") return "winner";
  if (tab === "losers")  return "loser";
  return "mixed";
}

function ProfileCard({ profile, cardType }: { profile: WinnerLoserProfile; cardType: CardType }) {
  const styles = CARD_STYLES[cardType] ?? CARD_STYLES.mixed;

  return (
    <div className={cn("rounded-lg border p-4", styles.border, styles.bg)}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-2xl">{styles.emoji}</span>
        <ConfBadge c={profile.confidence} />
      </div>
      <div className={cn("mb-1 text-sm font-medium text-white/80")}>{shortText(profile.profile, 28)}</div>
      <div className={cn("text-xl font-bold", styles.num)}>
        {safeStr(profile.net_monthly_range)}/mo
      </div>
      {profile.pct_of_income_range && profile.pct_of_income_range !== "N/A" && (
        <div className="mt-2 text-xs text-white/40">{profile.pct_of_income_range}</div>
      )}
    </div>
  );
}

function WinnersLosers({ data }: { data: FullReport["winners_losers"] }) {
  const [tab, setTab] = useState<WLTab>("winners");

  const winners = safeArr(data?.winners).slice(0, 3);
  const losers  = safeArr(data?.losers).slice(0, 3);
  const mixed   = safeArr(data?.mixed).slice(0, 3);

  const tabs: { key: WLTab; label: string; emoji: string }[] = [
    { key: "winners", label: "Win",  emoji: "🎯" },
    { key: "losers",  label: "Lose", emoji: "⚠️" },
    { key: "mixed",   label: "Mixed", emoji: "⚖️" },
  ];

  const profileMap: Record<WLTab, WinnerLoserProfile[]> = { winners, losers, mixed };
  const activeProfiles = profileMap[tab] ?? [];
  const cardType = tabToCardType(tab);

  return (
    <div className="space-y-4">
      {data?.distributional_verdict && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/12 p-3">
          <div className="mb-1 text-xs font-semibold text-emerald-400">
            {safeStr(data.distributional_verdict.progressive_or_regressive)}
          </div>
          <p className="text-xs leading-snug text-white/60">
            {shortText(data.distributional_verdict.explanation, 100)}
          </p>
        </div>
      )}

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={cn(
              "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
              tab === t.key
                ? "border-white/20 bg-white/10 text-white/90"
                : "border-white/8 text-white/40 hover:text-white/60",
            )}>
            <span className="text-lg">{t.emoji}</span>
            {t.label}
          </button>
        ))}
      </div>

      {activeProfiles.length === 0 ? (
        <p className="text-xs text-white/35">No data</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {activeProfiles.map((p, i) => (
            <ProfileCard key={i} profile={p} cardType={cardType} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 7: Geographic impact (VISUAL ONLY) ────────────────────────────────────────

function GeographicImpact({ regions }: { regions: GeographicRegion[] | null | undefined }) {
  const safe = safeArr(regions).filter(Boolean).slice(0, 4);
  if (safe.length === 0) return <p className="text-xs text-white/35">No data</p>;

  const getSeverityEmoji = (sev: string) => {
    if (sev === "HIGH") return "🔴";
    if (sev === "MEDIUM") return "🟡";
    return "🟢";
  };

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {safe.map((r) => (
        <div key={r.id} className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-white/85">{shortText(r.name, 20)}</div>
              <div className="text-xs text-white/40">{shortText(r.examples, 32)}</div>
            </div>
            <span className="text-xl">🗺️</span>
          </div>

          <div className="mb-3 rounded-lg bg-white/5 p-2">
            <div className="text-xl font-bold" style={{ color: r.color || "#94a3b8" }}>
              {r.net_monthly_range_median_hh}
              <span className="ml-1 text-xs font-normal text-white/30">/mo</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/50">Rent</span>
              <span>{getSeverityEmoji(r.rent_impact_severity)}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/50">Prices</span>
              <span>{getSeverityEmoji(r.price_impact_severity)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── 8: Confidence assessment (SIMPLIFIED) ────────────────────────────────────

function ConfidenceRadar({ data }: { data: FullReport["confidence_assessment"] }) {
  const components = safeArr(data?.by_component).filter(Boolean).slice(0, 5);
  const scenarios = safeArr(data?.what_would_change_conclusion).slice(0, 3);

  const confEmoji: Record<string, string> = {
    HIGH: "✅", MEDIUM: "⚠️", LOW: "❓",
  };

  if (components.length === 0) return <p className="text-xs text-white/35">No data</p>;

  return (
    <div className="space-y-2.5">
      {data?.weakest_link && (
        <div className="rounded-lg border border-amber-500/25 bg-amber-950/12 p-3">
          <div className="mb-1 text-xs font-semibold text-amber-400">BIGGEST UNCERTAINTY</div>
          <p className="text-xs text-white/60">{shortText(data.weakest_link, 80)}</p>
        </div>
      )}

      {components.map((c, i) => {
        const emoji = confEmoji[safeStr(c.confidence).toUpperCase()] ?? "❓";
        return (
          <div key={i} className="flex items-center gap-3 rounded-lg border border-white/8 p-3">
            <span className="text-lg">{emoji}</span>
            <div className="flex-1">
              <div className="text-sm font-medium text-white/75">{shortText(c.component, 30)}</div>
              <div className="text-xs text-white/40">{shortText(c.reasoning, 50)}</div>
            </div>
            <ConfBadge c={c.confidence} />
          </div>
        );
      })}

      {scenarios.length > 0 && (
        <div className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
          <div className="mb-2 text-xs font-semibold text-white/60">What would change this?</div>
          <div className="space-y-1.5">
            {scenarios.map((s, i) => (
              <div key={i} className="flex gap-2 text-xs text-white/45">
                <span className="mt-0.5 shrink-0">→</span>
                {shortText(s, 70)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── 9: Narrative (MINIMAL) ───────────────────────────────────────────────────

type NarrativeTab = "low_income" | "middle_income" | "upper_income" | "small_business";

const NARRATIVE_EMOJIS: Record<NarrativeTab, string> = {
  low_income: "💰",
  middle_income: "👨‍💼",
  upper_income: "🏆",
  small_business: "🏢",
};

function NarrativePanel({ narrative }: { narrative: FullReport["narrative"] }) {
  const [activeTab, setActiveTab] = useState<NarrativeTab>("middle_income");

  const tabs: { key: NarrativeTab; label: string }[] = [
    { key: "low_income",     label: "Low income" },
    { key: "middle_income",  label: "Middle income" },
    { key: "upper_income",   label: "High income" },
    { key: "small_business", label: "Business" },
  ];

  function getContent(tab: NarrativeTab): string {
    if (tab === "low_income")    return safeStr(narrative?.for_low_income);
    if (tab === "middle_income") return safeStr(narrative?.for_middle_income);
    if (tab === "upper_income")  return safeStr(narrative?.for_upper_income);
    return safeStr(narrative?.for_small_business);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={cn(
              "flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
              activeTab === t.key
                ? "border-white/20 bg-white/10 text-white/90"
                : "border-white/8 text-white/40 hover:text-white/60",
            )}>
            <span>{NARRATIVE_EMOJIS[t.key]}</span>
            {t.label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
        <p className="text-sm leading-relaxed text-white/65">
          {shortText(getContent(activeTab), 180)}
        </p>
      </div>

      {narrative?.biggest_uncertainty && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-950/12 p-3">
          <div className="mb-1 text-xs font-semibold text-amber-400">Key uncertainty</div>
          <p className="text-xs text-white/50">{shortText(narrative.biggest_uncertainty, 100)}</p>
        </div>
      )}
    </div>
  );
}

// ─── MAIN LAYOUT (INFOGRAPHIC-FIRST) ────────────────────────────────────────

export default function ResultsPanel({ report }: ResultsPanelProps) {
  if (!report) {
    return (
      <section className="mx-auto w-full max-w-6xl px-4 py-12 text-center">
        <p className="text-white/40">No report data available.</p>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-6xl space-y-4 px-4 py-6 sm:px-6">

      {/* BANNER: Policy + Verdict */}
      <PolicyHeader report={report} />

      {/* KPI STRIP: 4 Headline metrics */}
      <KpiStrip metrics={report.headline_metrics} />

      {/* SANKEY FLOW (if available) */}
      {report.sankey_data && <SankeyCard data={report.sankey_data} />}

      {/* MAIN ANALYSIS GRID (2 columns) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* LEFT: Waterfall - Where does money go? */}
        {report.waterfall && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">📊</span>
              <h3 className="text-sm font-semibold text-white/85">Where does it go?</h3>
            </div>
            <WaterfallChart data={report.waterfall} />
          </Card>
        )}

        {/* RIGHT: Timeline - When will you feel it? */}
        {report.timeline?.phases && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">⏱️</span>
              <h3 className="text-sm font-semibold text-white/85">Timeline of impact</h3>
            </div>
            <TimelineChart
              phases={report.timeline.phases}
              household_profile={safeStr(report.timeline?.household_profile)}
            />
          </Card>
        )}
      </div>

      {/* WHO WINS / LOSES */}
      {report.winners_losers && (
        <Card>
          <div className="mb-4 flex items-center gap-2">
            <span className="text-lg">👥</span>
            <h3 className="text-sm font-semibold text-white/85">Who benefits? Who doesn't?</h3>
          </div>
          <WinnersLosers data={report.winners_losers} />
        </Card>
      )}

      {/* SPENDING CATEGORIES + REGIONS (2 columns) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Spending impact */}
        {report.category_breakdown?.categories && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">📈</span>
              <h3 className="text-sm font-semibold text-white/85">What gets pricier?</h3>
            </div>
            <CategoryChart categories={report.category_breakdown.categories} />
          </Card>
        )}

        {/* Geographic impact */}
        {report.geographic_impact?.regions && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">🗺️</span>
              <h3 className="text-sm font-semibold text-white/85">Regional differences</h3>
            </div>
            <GeographicImpact regions={report.geographic_impact.regions} />
          </Card>
        )}
      </div>

      {/* CONFIDENCE + NARRATIVE (2 columns) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {report.confidence_assessment && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">🎯</span>
              <h3 className="text-sm font-semibold text-white/85">How confident?</h3>
            </div>
            <ConfidenceRadar data={report.confidence_assessment} />
          </Card>
        )}

        {report.narrative && (
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-lg">💡</span>
              <h3 className="text-sm font-semibold text-white/85">What it means for you</h3>
            </div>
            <NarrativePanel narrative={report.narrative} />
          </Card>
        )}
      </div>

      {/* FOOTER: Meta */}
      <footer className="flex justify-between px-2 text-xs text-white/20">
        <span>
          {safeNum(report.meta?.total_tool_calls)} calls · {safeArr(report.meta?.agents_completed).length} agents
        </span>
        <span>{safeNum(report.meta?.pipeline_duration_seconds)}s</span>
      </footer>
    </section>
  );
}