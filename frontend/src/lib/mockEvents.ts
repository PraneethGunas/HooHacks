import type {
  AgentChallenge,
  CausalClaim,
  PipelineEvent,
  SectorReport,
  SynthesisReport,
} from "@/types/pipeline";

export interface TimedPipelineEvent {
  delayMs: number;
  event: PipelineEvent;
}

const mkClaim = (
  claim: string,
  confidence: "EMPIRICAL" | "THEORETICAL" | "SPECULATIVE",
  mechanism: string,
  evidence: string[],
  survived = true,
): CausalClaim => ({
  claim,
  cause: "Minimum wage increase",
  effect: claim,
  mechanism,
  confidence,
  evidence,
  assumptions: ["Low-wage labor demand remains inelastic in service sectors"],
  sensitivity: "Regional labor market tightness",
  survived_debate: survived,
});

const laborReport: SectorReport = {
  sector: "labor",
  direct_effects: [
    mkClaim(
      "Wages rise for workers previously below $15/hour",
      "EMPIRICAL",
      "Policy floor binds where market wage distribution sits below target.",
      ["BLS CPS wage percentiles", "Dube et al. 2019"],
    ),
  ],
  second_order_effects: [
    mkClaim(
      "Turnover declines in retail and food service",
      "THEORETICAL",
      "Higher wages increase retention and reduce replacement churn costs.",
      ["QCEW separations", "JMP turnover elasticity estimates"],
    ),
  ],
  feedback_loops: [],
  cross_sector_dependencies: ["consumer", "business"],
  dissent: null,
  tool_calls_made: [
    {
      tool: "bls_get_series",
      query: "CES0500000003",
      result_summary: "Average hourly earnings baseline",
      duration_ms: 740,
    },
  ],
};

const challenge: AgentChallenge = {
  target_agent: "Labor",
  target_claim: mkClaim(
    "Large job losses are unlikely under tight labor market conditions",
    "THEORETICAL",
    "Wage floor pass-through and productivity offsets dampen employment effects.",
    ["Neumark and Shirley 2022", "CBO 2023"],
    false,
  ),
  challenge_type: "confidence_inflation",
  counter_evidence: [
    "Neumark range implies higher downside risk in low-margin counties",
    "Regional heterogeneity not fully controlled",
  ],
  proposed_revision: "Downgrade confidence and scope the claim to metro areas with low unemployment.",
};

function buildSynthesisReport(query: string): SynthesisReport {
  return {
    policy_summary: {
      title: query || "Raise the federal minimum wage to $15/hr",
      scope: "federal",
      affected_sectors: ["labor", "consumer", "business", "housing"],
    },
    agreed_findings: [
      {
        claim: mkClaim(
          "Wage gains are concentrated in the bottom decile of earners",
          "EMPIRICAL",
          "Direct floor binding creates immediate wage compression at lower percentiles.",
          ["BLS CPS", "EPI minimum wage tracker"],
        ),
        agreeing_agents: ["Labor", "Consumer"],
      },
    ],
    disagreements: [
      {
        topic: "Employment elasticity in rural low-margin counties",
        positions: {
          Labor: "Elasticity remains modest and temporary",
          Business: "Persistent margin pressure could cut entry-level hiring",
          Consumer: "Demand offsets some hiring drag through wage-led spending",
        },
      },
      {
        topic: "Pass-through to price inflation",
        positions: {
          Business: "Menu-price effects likely visible in 6-12 months",
          Consumer: "Pass-through remains limited outside labor-intensive goods",
        },
      },
    ],
    challenge_survival: [
      {
        challenge,
        outcome: "revise",
        final_claim: mkClaim(
          "Employment effects vary by county and are less certain outside tight labor markets",
          "THEORETICAL",
          "Heterogeneous regional demand conditions mediate employer response.",
          ["Neumark and Shirley 2022", "County Business Patterns"],
          true,
        ),
      },
    ],
    unified_impact: {
      summary:
        "The model projects clear wage gains at the lower end of the income distribution, with moderate uncertainty around hiring elasticity in lower-margin regions and partial price pass-through in specific sectors.",
      headline_stats: [
        { label: "Impacted workers", value: "23.1M", sub: "Bottom wage deciles" },
        { label: "Median wage lift", value: "+8.4%", sub: "Affected cohort" },
        { label: "Estimated CPI drag", value: "+0.2pp", sub: "12-month window" },
      ],
      key_claims: [
        mkClaim(
          "Wages rise for workers previously below $15/hour",
          "EMPIRICAL",
          "Binding wage floor shifts observed hourly wage distribution upward.",
          ["BLS CPS", "QCEW", "premium: payroll_micro_panel"],
          true,
        ),
        mkClaim(
          "Consumer spending rises in low-income ZIP codes",
          "THEORETICAL",
          "Higher marginal propensity to consume channels wage gains to local spending.",
          ["BEA PCE", "premium: card-panel-stream"],
          true,
        ),
        mkClaim(
          "Some small firms reduce entry-level hours",
          "SPECULATIVE",
          "Margin-constrained operators may adjust staffing mixes before productivity adapts.",
          ["SBO small business pulse", "premium: l2-firm-ledger"],
          false,
        ),
      ],
    },
    sankey_data: {
      nodes: [
        { id: "policy", label: "Minimum wage to $15", category: "policy" },
        { id: "labor", label: "Labor market", category: "sector" },
        { id: "consumer", label: "Consumer demand", category: "sector" },
        { id: "business", label: "Business margins", category: "sector" },
        { id: "wage", label: "Higher low-end wages", category: "effect" },
        { id: "prices", label: "Selective price pass-through", category: "effect" },
        { id: "employment", label: "Localized hiring pressure", category: "outcome" },
        { id: "spending", label: "Increased household spending", category: "outcome" },
      ],
      links: [
        { source: "policy", target: "labor", value: 10 },
        { source: "policy", target: "business", value: 8 },
        { source: "policy", target: "consumer", value: 6 },
        { source: "labor", target: "wage", value: 11 },
        { source: "business", target: "prices", value: 7 },
        { source: "wage", target: "spending", value: 9 },
        { source: "prices", target: "employment", value: 5 },
        { source: "business", target: "employment", value: 4 },
        { source: "consumer", target: "spending", value: 6 },
      ],
    },
    metadata: {
      total_tool_calls: 28,
      total_llm_calls: 41,
      duration_ms: 28600,
      lightning_payments: [
        {
          service: "premium-econ-models",
          invoice_amount_sats: 25,
          status: "paid",
          macaroon_received: true,
          payment_hash: "mockhash-001",
          duration_ms: 312,
        },
        {
          service: "journal-paywall-gateway",
          invoice_amount_sats: 18,
          status: "paid",
          macaroon_received: true,
          payment_hash: "mockhash-002",
          duration_ms: 276,
        },
      ],
    },
  };
}

function mkEvent<T extends PipelineEvent>(type: T["type"], data: T["data"]): T {
  return {
    type,
    data,
    timestamp: new Date().toISOString(),
  } as T;
}

export function buildMockTimeline(query: string): TimedPipelineEvent[] {
  const events: TimedPipelineEvent[] = [];

  events.push({
    delayMs: 400,
    event: mkEvent("classifier_complete", {
      task_type: "wage_policy",
      policy_params: { floor: "$15", jurisdiction: "federal" },
      affected_sectors: ["labor", "consumer", "business", "housing"],
      extracted_tags: ["wage policy", "federal scope", "$15"],
    }),
  });

  const analystTools = [
    ["fred_get_series", "FEDMINNFRWG"],
    ["bls_get_series", "LNS14000000"],
    ["bea_get_pce", "PCE low income"],
    ["cbo_report_lookup", "minimum wage 2023"],
    ["imf_paper_search", "wage floors price pass-through"],
    ["nber_search", "minimum wage employment heterogeneity"],
    ["qcew_lookup", "retail turnover"],
    ["crossref_search", "local labor market elasticity"],
  ] as const;

  analystTools.forEach(([tool, queryText], index) => {
    events.push({
      delayMs: 1100 + index * 700,
      event: mkEvent("analyst_tool_call", { tool, query: queryText }),
    });
  });

  events.push({
    delayMs: 7000,
    event: mkEvent("analyst_complete", {
      briefing_summary: "Baseline assembled from federal data and labor literature.",
      sources_found: 19,
      tool_calls_made: 8,
    }),
  });

  events.push({
    delayMs: 7400,
    event: mkEvent("lightning_payment", {
      service: "premium-econ-models",
      invoice_amount_sats: 25,
      status: "paying",
      macaroon_received: true,
      payment_hash: "mockhash-001",
      duration_ms: 140,
    }),
  });

  events.push({
    delayMs: 7800,
    event: mkEvent("lightning_payment", {
      service: "premium-econ-models",
      invoice_amount_sats: 25,
      status: "paid",
      macaroon_received: true,
      payment_hash: "mockhash-001",
      duration_ms: 312,
    }),
  });

  events.push({
    delayMs: 8200,
    event: mkEvent("lightning_payment", {
      service: "journal-paywall-gateway",
      invoice_amount_sats: 18,
      status: "paid",
      macaroon_received: true,
      payment_hash: "mockhash-002",
      duration_ms: 276,
    }),
  });

  ["Labor", "Consumer", "Business", "Housing"].forEach((agent) => {
    events.push({
      delayMs: 8500,
      event: mkEvent("sector_agent_started", { agent }),
    });
  });

  events.push({
    delayMs: 9400,
    event: mkEvent("sector_agent_tool_call", {
      agent: "Labor",
      tool: "bls_get_series",
      query: "CES0500000003",
    }),
  });
  events.push({
    delayMs: 9900,
    event: mkEvent("sector_agent_tool_call", {
      agent: "Consumer",
      tool: "bea_get_consumption",
      query: "Food away from home quintile spend",
    }),
  });
  events.push({
    delayMs: 10300,
    event: mkEvent("sector_agent_tool_call", {
      agent: "Business",
      tool: "sec_10k_scan",
      query: "Operating margin exposure to labor cost",
    }),
  });
  events.push({
    delayMs: 11000,
    event: mkEvent("sector_agent_tool_call", {
      agent: "Housing",
      tool: "hud_rent_panel",
      query: "Rent burden by income decile",
    }),
  });

  events.push({
    delayMs: 16900,
    event: mkEvent("sector_agent_complete", { agent: "Labor", report: laborReport }),
  });
  events.push({
    delayMs: 17700,
    event: mkEvent("sector_agent_complete", {
      agent: "Consumer",
      report: { ...laborReport, sector: "consumer" },
    }),
  });
  events.push({
    delayMs: 18800,
    event: mkEvent("sector_agent_complete", {
      agent: "Business",
      report: { ...laborReport, sector: "business" },
    }),
  });
  events.push({
    delayMs: 19700,
    event: mkEvent("sector_agent_complete", {
      agent: "Housing",
      report: { ...laborReport, sector: "housing" },
    }),
  });

  events.push({
    delayMs: 20500,
    event: mkEvent("debate_challenge", { challenge }),
  });

  events.push({
    delayMs: 21300,
    event: mkEvent("revision_complete", {
      rebuttal: {
        original_claim: challenge.target_claim,
        challenge,
        response: "revise",
        revised_claim: mkClaim(
          "Employment effects vary by region and likely remain modest in tighter labor markets",
          "THEORETICAL",
          "Heterogeneous sector pass-through and productivity response alter net labor demand.",
          ["County Business Patterns", "Neumark and Shirley 2022"],
          true,
        ),
        new_evidence: ["County panel updated with post-pandemic regime controls"],
      },
    }),
  });

  events.push({
    delayMs: 27300,
    event: mkEvent("synthesis_complete", { report: buildSynthesisReport(query) }),
  });

  return events;
}
