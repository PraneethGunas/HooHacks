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
  survived_debate?: boolean;
}

export interface ToolCallRecord {
  tool: string;
  query: string;
  result_summary: string;
  duration_ms: number;
}

export interface SectorReport {
  sector: "labor" | "housing" | "consumer" | "business";
  direct_effects: CausalClaim[];
  second_order_effects: CausalClaim[];
  feedback_loops: CausalClaim[];
  cross_sector_dependencies: string[];
  dissent: string | null;
  tool_calls_made: ToolCallRecord[];
}

export type ChallengeType =
  | "assumption_conflict"
  | "confidence_inflation"
  | "missing_mechanism"
  | "blind_spot";

export interface AgentChallenge {
  target_agent: string;
  target_claim: CausalClaim;
  challenge_type: ChallengeType;
  counter_evidence: string[];
  proposed_revision: string | null;
}

export type RebuttalResponse = "concede" | "defend" | "revise";

export interface AgentRebuttal {
  original_claim: CausalClaim;
  challenge: AgentChallenge;
  response: RebuttalResponse;
  revised_claim: CausalClaim | null;
  new_evidence: string[];
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

export interface SynthesisReport {
  policy_summary: {
    title: string;
    scope: string;
    affected_sectors: string[];
  };
  agreed_findings: Array<{
    claim: CausalClaim;
    agreeing_agents: string[];
  }>;
  disagreements: Array<{
    topic: string;
    positions: Record<string, string>;
  }>;
  challenge_survival: Array<{
    challenge: AgentChallenge;
    outcome: RebuttalResponse;
    final_claim: CausalClaim;
  }>;
  unified_impact: {
    summary: string;
    headline_stats: Array<{ label: string; value: string; sub?: string }>;
    key_claims: CausalClaim[];
  };
  impact_dashboard: Array<{
    category: string;
    direction: "increase" | "decline" | "mixed" | "distortionary";
    magnitude: string;
    confidence: Confidence;
    survived_challenge: "yes" | "no" | "partial";
    status: "works" | "doesnt_work" | "tradeoff";
    sectors: Array<"labor" | "housing" | "consumer" | "business" | "fiscal" | "cross-sector">;
  }>;
  sankey_data: SankeyData;
  metadata: {
    total_tool_calls: number;
    total_llm_calls: number;
    duration_ms: number;
    lightning_payments: LightningPaymentEvent["data"][];
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
  data: { agent: string };
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

export interface DebateChallengeEvent {
  type: "debate_challenge";
  data: { challenge: AgentChallenge };
  timestamp: string;
}

export interface RevisionCompleteEvent {
  type: "revision_complete";
  data: { rebuttal: AgentRebuttal };
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

export type PipelineEvent =
  | ClassifierCompleteEvent
  | AnalystToolCallEvent
  | AnalystCompleteEvent
  | LightningPaymentEvent
  | SectorAgentStartedEvent
  | SectorAgentToolCallEvent
  | SectorAgentCompleteEvent
  | DebateChallengeEvent
  | RevisionCompleteEvent
  | SynthesisCompleteEvent
  | ErrorEvent;

export interface PipelineState {
  status: "idle" | "running" | "complete" | "error";
  query: string;
  elapsedMs: number;
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
    }
  >;
  challenges: AgentChallenge[];
  rebuttals: AgentRebuttal[];
  synthesis: SynthesisReport | null;
  error: string | null;
}
