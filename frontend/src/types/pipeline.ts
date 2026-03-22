export type Confidence = "EMPIRICAL" | "THEORETICAL" | "SPECULATIVE";

export interface CausalClaim {
  claim: string;
  cause: string;
  effect: string;
  mechanism: string;
  confidence: Confidence;
  evidence: string[];
  assumptions: string[];
  sensitivity: string | null;
}

export interface ToolCallRecord {
  tool: string;
  query: string;
  result_summary: string;
  duration_ms: number;
}

export type AgentMode = "agentic" | "single_shot";

export interface SectorReport {
  sector: "labor" | "housing" | "consumer" | "business";
  direct_effects: CausalClaim[];
  second_order_effects: CausalClaim[];
  feedback_loops: CausalClaim[];
  cross_sector_dependencies: string[];
  dissent: string | null;
  tool_calls_made: ToolCallRecord[];
  agent_mode: AgentMode;
}


export interface SankeyNode {
  id: string;
  label: string;
  category: "policy" | "sector" | "effect" | "outcome";
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
  label?: string;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface Range {
  low: string;
  central: string;
  high: string;
}

export interface NumRange {
  low: number;
  central: number;
  high: number;
}

export interface HeadlineMetric {
  id: string;
  label: string;
  value: string;
  range: Range | null;
  unit: string;
  direction: "positive" | "negative" | "neutral";
  confidence: Confidence;
  icon: string;
  context: string;
}

export interface WaterfallStep {
  label: string;
  value: number;
  cumulative: number;
  type: "inflow" | "outflow" | "neutral" | "net";
  source_agent: string;
  note: string | null;
}

export interface ImpactMatrixCell {
  income: string;
  type: string;
  geography: string;
  net_monthly: NumRange;
  net_annual: NumRange;
  pct_of_income: NumRange;
  confidence: Confidence;
  verdict: string;
  dominant_inflow: string;
  dominant_outflow: string;
  note: string;
}

export interface CategoryBreakdown {
  name: string;
  icon: string;
  pct_change: NumRange;
  dollar_impact_monthly: NumRange;
  budget_share_low_income: number;
  budget_share_middle_income: number;
  budget_share_high_income: number;
  pass_through_rate: string;
  time_to_full_effect: string;
  source_agent: string;
  confidence: Confidence;
  explanation: string;
  note?: string;
}

export interface TimelinePhase {
  label: string;
  period_start: number;
  period_end: number;
  cumulative_net_monthly: NumRange;
  what_happens: string[];
  mood: string;
  dominant_driver: string;
}

export interface WinnerLoserProfile {
  profile: string;
  icon: string;
  net_monthly_range: string;
  pct_of_income_range: string;
  why: string;
  confidence: Confidence;
  impact_quality?: string;
  caveat?: string;
  depends_on?: string;
}

export interface GeographicRegion {
  id: string;
  name: string;
  examples: string;
  net_direction: string;
  color: string;
  rent_impact_severity: string;
  price_impact_severity: string;
  net_monthly_range_median_hh: string;
  explanation: string;
  key_factor: string;
}

export interface SynthesisReport {
  meta: {
    version: string;
    generated_at: string;
    pipeline_duration_seconds: number;
    total_tool_calls: number;
    agents_completed: string[];
    agents_missing: string[];
    model_used: string;
    query: string;
  };
  policy: {
    title: string;
    one_liner: string;
    type: string;
    geography: string;
    effective_date: string | null;
    current_baseline: string;
    proposed_change: string;
    estimated_annual_cost: string;
    key_ambiguities: string[];
    working_assumptions: string[];
  };
  headline: {
    verdict: string;
    bottom_line: string;
    confidence: Confidence | string;
    confidence_explanation: string;
  };
  headline_metrics: HeadlineMetric[];
  waterfall: {
    title: string;
    subtitle: string;
    household_profile: string;
    steps: WaterfallStep[];
    net_monthly: number;
    net_annual: number;
    pct_of_income: number;
  };
  impact_matrix: {
    title: string;
    subtitle: string;
    income_tiers: Array<{ id: string; label: string; monthly: number }>;
    geographies: Array<{ id: string; label: string; example: string }>;
    household_types: Array<{ id: string; label: string }>;
    cells: ImpactMatrixCell[];
  };
  category_breakdown: {
    title: string;
    subtitle: string;
    categories: CategoryBreakdown[];
  };
  timeline: {
    title: string;
    subtitle: string;
    household_profile: string;
    phases: TimelinePhase[];
  };
  winners_losers: {
    title: string;
    winners: WinnerLoserProfile[];
    losers: WinnerLoserProfile[];
    mixed: WinnerLoserProfile[];
    distributional_verdict: {
      progressive_or_regressive: string;
      explanation: string;
      geographic_equity: string;
      generational_equity: string;
    };
  };
  geographic_impact: {
    title: string;
    regions: GeographicRegion[];
  };
  consistency_report: {
    title: string;
    inconsistencies_found: number;
    adjustments: Array<{
      variable: string;
      original_source: string;
      original_value: string;
      issue: string;
      resolved_source: string;
      resolved_value: string;
      impact_on_output: string;
      severity: string;
    }>;
    unresolved_gaps: string[];
  };
  confidence_assessment: {
    overall: Confidence | string;
    by_component: Array<{
      component: string;
      confidence: Confidence | string;
      reasoning: string;
    }>;
    weakest_link: string;
    what_would_change_conclusion: string[];
  };
  evidence_summary: {
    title: string;
    key_studies: Array<{
      name: string;
      finding: string;
      applicability: string;
      source_agent: string;
    }>;
    consensus: string;
    major_gap: string;
  };
  data_sources: {
    title: string;
    agents_and_calls: Array<{
      agent: string;
      tool_calls: number;
      key_data: string[];
      phases_completed: number;
    }>;
    total_tool_calls: number;
    total_unique_data_series: number;
    methodology_notes: string[];
  };
  narrative: {
    executive_summary: string;
    for_low_income: string;
    for_middle_income: string;
    for_upper_income: string;
    for_small_business: string;
    biggest_uncertainty: string;
  };
}

export interface ClassifierCompleteEvent {
  type: "classifier_complete";
  data: {
    task_type: string;
    policy_params: Record<string, string>;
    affected_sectors: string[];
    extracted_tags: string[];
  };
  timestamp: string;
}

export interface AnalystToolCallEvent {
  type: "analyst_tool_call";
  data: { tool: string; query: string };
  timestamp: string;
}

export interface AnalystCompleteEvent {
  type: "analyst_complete";
  data: {
    briefing_summary: string;
    sources_found: number;
    tool_calls_made: number;
  };
  timestamp: string;
}

export interface LightningPaymentEvent {
  type: "lightning_payment";
  data: {
    service: string;
    invoice_amount_sats: number;
    status: "paying" | "paid" | "failed";
    macaroon_received: boolean;
    payment_hash: string;
    duration_ms: number;
  };
  timestamp: string;
}

export interface SectorAgentStartedEvent {
  type: "sector_agent_started";
  data: { agent: string; agent_mode?: AgentMode };
  timestamp: string;
}

export interface SectorAgentToolCallEvent {
  type: "sector_agent_tool_call";
  data: { agent: string; tool: string; query: string };
  timestamp: string;
}

export interface SectorAgentCompleteEvent {
  type: "sector_agent_complete";
  data: { agent: string; report: SectorReport };
  timestamp: string;
}

export type ThinkingStepType = "phase_start" | "tool_call" | "tool_result" | "reasoning" | "reasoning_chunk" | "phase_complete";

export interface ThinkingStep {
  id: number;
  stepType: ThinkingStepType;
  content: string;
  phase: string;
  tool?: string;
  timestamp: number;
}

export interface SectorAgentThinkingEvent {
  type: "sector_agent_thinking";
  data: {
    agent: string;
    step_type: ThinkingStepType;
    content: string;
    phase?: string;
    tool?: string;
  };
  timestamp: string;
}

export interface ClassifierThinkingEvent {
  type: "classifier_thinking";
  data: {
    step_type: ThinkingStepType;
    content: string;
    phase?: string;
    tool?: string;
  };
  timestamp: string;
}

export interface AnalystThinkingEvent {
  type: "analyst_thinking";
  data: {
    step_type: ThinkingStepType;
    content: string;
    phase?: string;
    tool?: string;
  };
  timestamp: string;
}

export interface SynthesisThinkingEvent {
  type: "synthesis_thinking";
  data: {
    step_type: ThinkingStepType;
    content: string;
    phase?: string;
    tool?: string;
  };
  timestamp: string;
}

export interface SynthesisPhaseEvent {
  type: "synthesis_phase";
  data: { phase: number; name: string; status: "running" | "complete" };
  timestamp: string;
}

export interface SynthesisCompleteEvent {
  type: "synthesis_complete";
  data: { report: SynthesisReport };
  timestamp: string;
}

export interface ErrorEvent {
  type: "error";
  data: { message: string; stage?: string };
  timestamp: string;
}

export interface PipelineCompleteEvent {
  type: "pipeline_complete";
  data: { session_id: string; total_seconds: number; stage_times: Record<string, number> };
  timestamp: string;
}

export interface PipelineErrorEvent {
  type: "pipeline_error";
  data: { error: string; stage?: string };
  timestamp: string;
}

export interface AgentStartEvent {
  type: "agent_start";
  data: Record<string, unknown>;
  timestamp: string;
}

export interface AgentResultEvent {
  type: "agent_result";
  data: Record<string, unknown>;
  timestamp: string;
}

export type PipelineEvent =
  | ClassifierThinkingEvent
  | ClassifierCompleteEvent
  | AnalystToolCallEvent
  | AnalystCompleteEvent
  | AnalystThinkingEvent
  | LightningPaymentEvent
  | SectorAgentStartedEvent
  | SectorAgentToolCallEvent
  | SectorAgentCompleteEvent
  | SectorAgentThinkingEvent
  | SynthesisPhaseEvent
  | SynthesisThinkingEvent
  | SynthesisCompleteEvent
  | ErrorEvent
  | PipelineCompleteEvent
  | PipelineErrorEvent
  | AgentStartEvent
  | AgentResultEvent;

export interface PipelineState {
  status: "idle" | "running" | "complete" | "error";
  query: string;
  elapsedMs: number;
  classifierThinkingSteps: ThinkingStep[];
  classifier: ClassifierCompleteEvent["data"] | null;
  analystToolCalls: AnalystToolCallEvent["data"][];
  analystComplete: AnalystCompleteEvent["data"] | null;
  lightningPayments: LightningPaymentEvent["data"][];
  sectorAgents: Record<
    string,
    {
      status: "pending" | "running" | "complete";
      toolCalls: SectorAgentToolCallEvent["data"][];
      report: SectorReport | null;
      agentMode: AgentMode | null;
      /** Current LangGraph phase (1-5) for agentic agents, null for single-shot */
      currentPhase: string | null;
      /** Human-readable description of current phase */
      phaseLabel: string | null;
      /** Live thinking feed from LangGraph agent */
      thinkingSteps: ThinkingStep[];
    }
  >;
  analystThinkingSteps: ThinkingStep[];
  synthesisPhase: { phase: number; name: string; status: "running" | "complete" } | null;
  synthesisThinkingSteps: ThinkingStep[];
  synthesis: SynthesisReport | null;
  error: string | null;
}
