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

const POLICY_TITLE = "Implement a 30% corporate tax increase on tech companies with revenue over $50B";

const mkClaim = (
  claim: string,
  confidence: "EMPIRICAL" | "THEORETICAL" | "SPECULATIVE",
  mechanism: string,
  evidence: string[],
  survived = true,
): CausalClaim => ({
  claim,
  cause: "Corporate tax increase on large tech firms",
  effect: claim,
  mechanism,
  confidence,
  evidence,
  assumptions: ["Large firms adjust through a mix of pricing, shareholder returns, and cost optimization"],
  sensitivity: "Profit-shifting intensity and cloud pricing competition",
  survived_debate: survived,
});

const laborReport: SectorReport = {
  sector: "labor",
  direct_effects: [
    mkClaim(
      "Direct employment declines by roughly 14,000-35,000 jobs after revision and profit-shifting adjustment",
      "THEORETICAL",
      "Higher effective tax rates compress after-tax profits and slow hiring in non-core functions first.",
      ["BLS tech employment series", "UK 2023 corporate tax adjustment", "CBO incidence framework"],
    ),
    mkClaim(
      "Tech wage growth slows by about 0.3-0.8 percentage points annually",
      "EMPIRICAL",
      "Part of tax incidence passes through compensation growth in large firms with stable wages.",
      ["Fuest et al. labor-incidence estimates", "CBO methodology note"],
    ),
  ],
  second_order_effects: [
    mkClaim(
      "R&D headcount tilts offshore by 5,000-25,000 roles over multiple years",
      "THEORETICAL",
      "Relative tax differentials make existing international R&D hubs more attractive at the margin.",
      ["Hines and Rice", "OECD 2023 minimum-tax assessments"],
    ),
  ],
  feedback_loops: [
    mkClaim(
      "Reduced buybacks absorb a larger share of burden than payroll cuts",
      "THEORETICAL",
      "Shareholder distributions are faster to adjust than strategic engineering headcount.",
      ["TCJA buyback evidence", "Large-cap earnings call commentary"],
    ),
  ],
  cross_sector_dependencies: ["consumer", "business", "housing"],
  dissent: "Magnitude depends on whether cloud pricing absorbs more of the burden.",
  tool_calls_made: [
    {
      tool: "bls_get_series",
      query: "NAICS 5112, 5415, 5182 employment",
      result_summary: "Tech labor baseline and recent hiring trend",
      duration_ms: 820,
    },
  ],
};

const housingReport: SectorReport = {
  sector: "housing",
  direct_effects: [
    mkClaim(
      "Sustained rent softening in SF and Seattle is likely 0.5-1.5%",
      "THEORETICAL",
      "Lower stock-comp purchasing power and slower hiring reduce high-income bid pressure.",
      ["FRED metro rent panels", "Census metro housing burden"],
    ),
  ],
  second_order_effects: [
    mkClaim(
      "A transient sentiment dip of 1-2% may occur in the first 3-6 months before partial rebound",
      "SPECULATIVE",
      "Housing listings react quickly to tech-market sentiment before fundamentals settle.",
      ["2022-2023 SF rent trend", "REIS market pulse"],
    ),
  ],
  feedback_loops: [],
  cross_sector_dependencies: ["labor", "consumer"],
  dissent: "If AI hiring offsets layoffs, housing impact could be near zero.",
  tool_calls_made: [
    {
      tool: "fred_get_series",
      query: "SF, Seattle, Austin rent and home price time series",
      result_summary: "Tech-hub concentration and affordability baseline",
      duration_ms: 910,
    },
  ],
};

const consumerReport: SectorReport = {
  sector: "consumer",
  direct_effects: [
    mkClaim(
      "Cloud and SaaS prices are likely to rise 0.7-2.0% under revised burden allocation",
      "THEORETICAL",
      "Oligopoly pricing with high switching costs supports partial pass-through.",
      ["Baker et al. concentrated-market pass-through", "Cloud market share benchmarks"],
    ),
  ],
  second_order_effects: [
    mkClaim(
      "Household cost impact remains modest at roughly $25-80 per year",
      "THEORETICAL",
      "Most direct burden lands on enterprise software spend rather than broad consumer staples.",
      ["BLS CPI digital services baskets", "Subscription pricing histories"],
    ),
  ],
  feedback_loops: [
    mkClaim(
      "More successful pass-through reduces pressure for labor cuts",
      "THEORETICAL",
      "Price and payroll channels substitute each other in burden distribution.",
      ["Debate coordination memo"],
    ),
  ],
  cross_sector_dependencies: ["labor", "business"],
  dissent: "Pass-through collapses if one hyperscaler holds price to gain share.",
  tool_calls_made: [
    {
      tool: "bls_get_series",
      query: "CUSR0000SEEE02 + software/services CPI components",
      result_summary: "Baseline for digital-service pricing",
      duration_ms: 760,
    },
  ],
};

const businessReport: SectorReport = {
  sector: "business",
  direct_effects: [
    mkClaim(
      "Vendor and contractor spend likely declines by about $8B-$25B after challenge revisions",
      "SPECULATIVE",
      "Procurement budgets are the fastest lever, but urgency is lower than in revenue-shock cycles.",
      ["2022-2023 vendor spend cut behavior", "large-cap margin disclosures"],
      false,
    ),
  ],
  second_order_effects: [
    mkClaim(
      "Mid-size firms below $50B gain a structural cost-of-capital advantage",
      "THEORETICAL",
      "A threshold-based regime creates relative tax asymmetry favoring sub-threshold competitors.",
      ["OECD competition notes", "industry revenue tier mapping"],
    ),
    mkClaim(
      "Cloud-dependent startups may face 0.5-2% margin compression if pass-through occurs",
      "THEORETICAL",
      "Infrastructure costs represent a high share of COGS in many SaaS businesses.",
      ["Startup COGS benchmarks", "cloud cost allocation studies"],
    ),
  ],
  feedback_loops: [
    mkClaim(
      "A hard $50B cutoff can create cliff incentives for restructuring",
      "THEORETICAL",
      "Discrete thresholds encourage entity design and growth-timing optimization.",
      ["Tax notch and cliff-effect literature"],
    ),
  ],
  cross_sector_dependencies: ["consumer", "labor", "housing"],
  dissent: "If policy phases in smoothly, competitive distortion is much smaller.",
  tool_calls_made: [
    {
      tool: "census_cbp_query",
      query: "NAICS 51/54 vendor ecosystem concentration",
      result_summary: "Dependency map of suppliers and contractors",
      duration_ms: 990,
    },
  ],
};

const burdenChallenge: AgentChallenge = {
  target_agent: "Labor",
  target_claim: mkClaim(
    "Labor and Consumer burden shares must sum to a single coordinated allocation",
    "THEORETICAL",
    "Independent high-end estimates over-allocate the same tax dollar pool.",
    ["Baker et al. 40-60 split guidance"],
    false,
  ),
  challenge_type: "assumption_conflict",
  counter_evidence: [
    "Price pass-through and payroll cuts were modeled independently",
    "Coordinated burden allocation was missing",
  ],
  proposed_revision: "Use a 50/50 split between pass-through and internal absorption before sector-level allocation.",
};

const housingChallenge: AgentChallenge = {
  target_agent: "Housing",
  target_claim: mkClaim(
    "Rent impact needs decomposition into lasting demand effect and transient sentiment effect",
    "THEORETICAL",
    "Undifferentiated estimates obscure timing and persistence.",
    ["2022-2023 tech layoff rent response"],
    false,
  ),
  challenge_type: "missing_mechanism",
  counter_evidence: [
    "Sentiment-driven listing moves can reverse quickly",
    "Lease renewal cycle delays fundamentals",
  ],
  proposed_revision: "Split estimate into lasting 12-24 month effect and short-term 3-6 month sentiment effect.",
};

const shiftingChallenge: AgentChallenge = {
  target_agent: "All agents",
  target_claim: mkClaim(
    "Profit shifting can reduce domestic tax impact by 30-50%",
    "EMPIRICAL",
    "Global firms can relocate taxable profits and selected operations to lower-tax jurisdictions.",
    ["Torslov-Wier-Zucman 2023", "OECD Pillar Two analysis"],
    true,
  ),
  challenge_type: "blind_spot",
  counter_evidence: [
    "US multinationals already shift significant profits offshore",
    "Proposed 27.3% rate still exceeds global minimum by a wide margin",
  ],
  proposed_revision: "Rebase revenue, labor, and pricing impacts with a 30-50% avoidance scenario.",
};

const vendorChallenge: AgentChallenge = {
  target_agent: "Business",
  target_claim: mkClaim(
    "Vendor cut estimate confidence is overstated when using revenue-downturn precedent",
    "THEORETICAL",
    "Tax-driven and demand-driven optimization cycles are not equivalent.",
    ["Meta/Google 2022-2023 efficiency period"],
    false,
  ),
  challenge_type: "confidence_inflation",
  counter_evidence: [
    "Top-line demand remains healthy in tax-only scenario",
    "Healthy gross margins reduce urgency for aggressive cuts",
  ],
  proposed_revision: "Downgrade confidence to SPECULATIVE and narrow range.",
};

function buildSynthesisReport(query: string): SynthesisReport {
  return {
    policy_summary: {
      title: query || POLICY_TITLE,
      scope: "federal",
      affected_sectors: ["labor", "housing", "consumer", "business"],
    },
    agreed_findings: [
      {
        claim: mkClaim(
          "Domestic impact is moderate and concentrated in tech hubs rather than broad national disruption",
          "EMPIRICAL",
          "Affected employment and compensation are geographically concentrated while national labor base is large.",
          ["Metro concentration table", "national workforce denominator"],
        ),
        agreeing_agents: ["Labor", "Housing", "Consumer", "Business"],
      },
      {
        claim: mkClaim(
          "Shareholder returns absorb more burden than labor in the revised coordinated scenario",
          "THEORETICAL",
          "Buybacks and dividends are more flexible adjustment channels than strategic payroll.",
          ["2017 TCJA aftermath", "rebuttal alignment notes"],
        ),
        agreeing_agents: ["Labor", "Consumer", "Business"],
      },
    ],
    disagreements: [
      {
        topic: "Speed of labor-market adjustment",
        positions: {
          Labor: "Adjustment plays out over 12-18 months.",
          Business: "Vendor and contractor impact appears within 1-2 quarters.",
          Housing: "Most housing effects trail labor shifts by lease cycles.",
        },
      },
      {
        topic: "Cloud pricing behavior among hyperscalers",
        positions: {
          Consumer: "0.7-2.0% pass-through is likely in concentrated categories.",
          Business: "One provider holding price could erase most pass-through.",
        },
      },
      {
        topic: "Long-run R&D relocation scale",
        positions: {
          Labor: "5K-25K jobs can shift offshore over years.",
          Housing: "Remote work and domestic AI hiring dampen location effects.",
        },
      },
    ],
    challenge_survival: [
      {
        challenge: burdenChallenge,
        outcome: "revise",
        final_claim: mkClaim(
          "Revised burden split: 50% pass-through and 50% internal absorption with labor impacts moderated",
          "THEORETICAL",
          "Coordinated accounting reconciles sector estimates into a single dollar allocation.",
          ["Baker et al.", "Revision round notes"],
          true,
        ),
      },
      {
        challenge: housingChallenge,
        outcome: "revise",
        final_claim: mkClaim(
          "Sustained SF/Seattle rent impact is likely 0.5-1.5%, plus transient sentiment move",
          "THEORETICAL",
          "Separating short-term sentiment from medium-term demand clarifies persistence.",
          ["Housing revision memo"],
          true,
        ),
      },
      {
        challenge: shiftingChallenge,
        outcome: "revise",
        final_claim: mkClaim(
          "Profit shifting likely reduces both collected revenue and domestic knock-on effects",
          "EMPIRICAL",
          "Behavioral avoidance reduces realized policy incidence versus static estimates.",
          ["TWZ 2023", "OECD Pillar Two"],
          true,
        ),
      },
      {
        challenge: vendorChallenge,
        outcome: "concede",
        final_claim: mkClaim(
          "Vendor-spend contraction remains plausible but with SPECULATIVE confidence and reduced range",
          "SPECULATIVE",
          "Tax-only shocks do not mechanically replicate downturn-era cuts.",
          ["Business revision statement"],
          false,
        ),
      },
    ],
    unified_impact: {
      summary:
        "A 30% corporate tax increase on US tech firms above $50B revenue likely raises federal receipts by about $50B-$85B per year after behavioral responses. Effects are concentrated in major tech hubs and vendor ecosystems, while national-level consumer and housing impacts remain modest.",
      headline_stats: [
        { label: "Additional revenue", value: "+$50B-$85B/yr", sub: "After profit shifting" },
        { label: "Direct jobs", value: "-14K to -35K", sub: "Revised with burden coordination" },
        { label: "Cloud/SaaS prices", value: "+0.7% to +2.0%", sub: "Category-dependent pass-through" },
      ],
      key_claims: [
        mkClaim(
          "Revenue gain is meaningful but below static projections because 30-50% of exposure can be behaviorally shifted",
          "EMPIRICAL",
          "Global tax-planning channels reduce taxable domestic base.",
          ["TWZ 2023", "OECD 2023"],
          true,
        ),
        mkClaim(
          "Employment and wage-growth effects are moderate and concentrated in large-firm ecosystems",
          "THEORETICAL",
          "Most burden is split across price, shareholder returns, and selective cost optimization.",
          ["Revision round burden split", "BLS metro concentration"],
          true,
        ),
        mkClaim(
          "A hard $50B threshold introduces competitive distortion and restructuring incentives",
          "THEORETICAL",
          "Discrete policy cliffs reward structural optimization rather than productive expansion.",
          ["Tax notch literature", "near-threshold company mapping"],
          true,
        ),
        mkClaim(
          "Vendor/contractor contraction is possible but remains highly uncertain",
          "SPECULATIVE",
          "Cut behavior depends on management preference for buyback reduction versus procurement tightening.",
          ["Business challenge response", "efficiency-cycle comparisons"],
          false,
        ),
      ],
    },
    impact_dashboard: [
      {
        category: "Federal tax revenue",
        direction: "increase",
        magnitude: "+$50B-$85B/year",
        confidence: "EMPIRICAL",
        survived_challenge: "yes",
        status: "works",
        sectors: ["fiscal", "cross-sector"],
      },
      {
        category: "Tech sector employment",
        direction: "decline",
        magnitude: "-14,000 to -35,000 direct",
        confidence: "THEORETICAL",
        survived_challenge: "yes",
        status: "doesnt_work",
        sectors: ["labor"],
      },
      {
        category: "Tech worker compensation growth",
        direction: "decline",
        magnitude: "-0.3 to -0.8% annually",
        confidence: "EMPIRICAL",
        survived_challenge: "yes",
        status: "doesnt_work",
        sectors: ["labor", "housing"],
      },
      {
        category: "Vendor/contractor ecosystem",
        direction: "decline",
        magnitude: "-$8B to -$25B spend; -25K to -70K indirect jobs",
        confidence: "SPECULATIVE",
        survived_challenge: "partial",
        status: "doesnt_work",
        sectors: ["business", "labor"],
      },
      {
        category: "Cloud and SaaS prices",
        direction: "increase",
        magnitude: "+0.7% to +2.0%",
        confidence: "THEORETICAL",
        survived_challenge: "yes",
        status: "doesnt_work",
        sectors: ["consumer", "business"],
      },
      {
        category: "Consumer household cost",
        direction: "increase",
        magnitude: "+$25 to +$80/year",
        confidence: "THEORETICAL",
        survived_challenge: "yes",
        status: "doesnt_work",
        sectors: ["consumer"],
      },
      {
        category: "Tech-hub housing (SF/Seattle)",
        direction: "decline",
        magnitude: "-0.5 to -1.5% sustained rent",
        confidence: "THEORETICAL",
        survived_challenge: "yes",
        status: "tradeoff",
        sectors: ["housing", "labor"],
      },
      {
        category: "Mid-size tech competitiveness",
        direction: "increase",
        magnitude: "~6pp tax cost advantage",
        confidence: "THEORETICAL",
        survived_challenge: "partial",
        status: "works",
        sectors: ["business"],
      },
      {
        category: "Profit-shifting incentive",
        direction: "increase",
        magnitude: "30-50% of tax impact avoided",
        confidence: "EMPIRICAL",
        survived_challenge: "partial",
        status: "doesnt_work",
        sectors: ["fiscal", "cross-sector"],
      },
      {
        category: "$50B threshold cliff effect",
        direction: "distortionary",
        magnitude: "5-10 near-threshold firms face restructuring incentives",
        confidence: "THEORETICAL",
        survived_challenge: "partial",
        status: "doesnt_work",
        sectors: ["business", "cross-sector"],
      },
    ],
    sankey_data: {
      nodes: [
        { id: "policy", label: "30% Tax Increase", category: "policy" },
        { id: "tech_revenue", label: "$2.1T Tech Revenue", category: "sector" },
        { id: "offshore", label: "$130B Shifted Offshore", category: "effect" },
        { id: "taxable", label: "$1.97T Taxable Base", category: "sector" },
        { id: "gov", label: "Government Revenue", category: "outcome" },
        { id: "wages", label: "Wages", category: "effect" },
        { id: "rnd", label: "R&D", category: "effect" },
        { id: "buybacks", label: "Buybacks/Dividends", category: "effect" },
        { id: "vendor", label: "Vendor Operations", category: "effect" },
        { id: "prices", label: "Price Pass-through", category: "effect" },
        { id: "consumers", label: "Consumers/Businesses", category: "outcome" },
      ],
      links: [
        { source: "policy", target: "tech_revenue", value: 100, label: "Policy shock" },
        { source: "tech_revenue", target: "offshore", value: 13, label: "Behavioral shift" },
        { source: "tech_revenue", target: "taxable", value: 87, label: "Remaining base" },
        { source: "taxable", target: "gov", value: 27, label: "Tax to government" },
        { source: "taxable", target: "wages", value: 18, label: "Compensation" },
        { source: "taxable", target: "rnd", value: 14, label: "R&D budgets" },
        { source: "taxable", target: "buybacks", value: 16, label: "Largest absorber" },
        { source: "taxable", target: "vendor", value: 13, label: "Procurement" },
        { source: "taxable", target: "prices", value: 12, label: "Pass-through" },
        { source: "prices", target: "consumers", value: 12, label: "Downstream cost" },
      ],
    },
    metadata: {
      total_tool_calls: 52,
      total_llm_calls: 33,
      duration_ms: 47000,
      lightning_payments: [
        {
          service: "premium-policy-data-pack",
          invoice_amount_sats: 34,
          status: "paid",
          macaroon_received: true,
          payment_hash: "mockhash-tax-001",
          duration_ms: 318,
        },
        {
          service: "journal-paywall-gateway",
          invoice_amount_sats: 22,
          status: "paid",
          macaroon_received: true,
          payment_hash: "mockhash-tax-002",
          duration_ms: 281,
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

function buildSectorToolCalls(): Array<{ delayMs: number; event: PipelineEvent }> {
  return [
    { delayMs: 11500, event: mkEvent("sector_agent_tool_call", { agent: "Labor", tool: "bls_get_series", query: "NAICS 5112, 5415, 5182 employment" }) },
    { delayMs: 12200, event: mkEvent("sector_agent_tool_call", { agent: "Housing", tool: "fred_get_series", query: "SF, Seattle, Austin rent panels" }) },
    { delayMs: 12800, event: mkEvent("sector_agent_tool_call", { agent: "Consumer", tool: "bls_get_series", query: "Digital service CPI and cloud proxies" }) },
    { delayMs: 13400, event: mkEvent("sector_agent_tool_call", { agent: "Business", tool: "census_cbp_query", query: "Tech vendor ecosystem concentration" }) },
    { delayMs: 14100, event: mkEvent("sector_agent_tool_call", { agent: "Labor", tool: "semantic_scholar_search", query: "corporate tax incidence wages employment" }) },
    { delayMs: 14700, event: mkEvent("sector_agent_tool_call", { agent: "Housing", tool: "census_housing_query", query: "Housing burden in tech metros" }) },
    { delayMs: 15300, event: mkEvent("sector_agent_tool_call", { agent: "Consumer", tool: "market_competition_scan", query: "AWS Azure GCP pricing power" }) },
    { delayMs: 15900, event: mkEvent("sector_agent_tool_call", { agent: "Business", tool: "sec_10k_scan", query: "Large-cap buyback versus opex sensitivity" }) },
  ];
}

export function buildMockTimeline(query: string): TimedPipelineEvent[] {
  const events: TimedPipelineEvent[] = [];

  events.push({
    delayMs: 450,
    event: mkEvent("classifier_complete", {
      task_type: "policy_proposal",
      policy_params: {
        policy_action: "Corporate tax increase on large tech companies",
        specific_value: "30% increase (effective rate ~21% -> ~27.3%)",
        scope: "Federal",
        threshold: ">$50B annual revenue",
      },
      affected_sectors: ["labor", "housing", "consumer", "business"],
      extracted_tags: ["corporate tax", "big tech", "federal", "$50B threshold"],
    }),
  });

  const analystTools = [
    ["fred_get_series", "Federal corporate tax receipts baseline"],
    ["bls_get_series", "Tech sector employment and wage trends"],
    ["semantic_scholar_search", "corporate tax increase investment effects"],
    ["cbo_report_lookup", "Revenue effects of corporate tax changes"],
    ["precedent_scan", "2017 TCJA reverse analogy"],
    ["uk_policy_lookup", "UK corporate tax increase 2023 outcomes"],
    ["oecd_policy_lookup", "Pillar Two and profit shifting"],
    ["news_monitor", "corporate tax tech companies 2026"],
  ] as const;

  analystTools.forEach(([tool, queryText], index) => {
    events.push({
      delayMs: 1300 + index * 780,
      event: mkEvent("analyst_tool_call", { tool, query: queryText }),
    });
  });

  events.push({
    delayMs: 8400,
    event: mkEvent("analyst_complete", {
      briefing_summary: "Baseline assembled: ~18 firms above $50B, estimated static revenue gain $80B-$120B before behavioral response.",
      sources_found: 24,
      tool_calls_made: 8,
    }),
  });

  events.push({
    delayMs: 8700,
    event: mkEvent("lightning_payment", {
      service: "premium-policy-data-pack",
      invoice_amount_sats: 34,
      status: "paying",
      macaroon_received: true,
      payment_hash: "mockhash-tax-001",
      duration_ms: 151,
    }),
  });

  events.push({
    delayMs: 9050,
    event: mkEvent("lightning_payment", {
      service: "premium-policy-data-pack",
      invoice_amount_sats: 34,
      status: "paid",
      macaroon_received: true,
      payment_hash: "mockhash-tax-001",
      duration_ms: 318,
    }),
  });

  events.push({
    delayMs: 9300,
    event: mkEvent("lightning_payment", {
      service: "journal-paywall-gateway",
      invoice_amount_sats: 22,
      status: "paid",
      macaroon_received: true,
      payment_hash: "mockhash-tax-002",
      duration_ms: 281,
    }),
  });

  ["Labor", "Housing", "Consumer", "Business"].forEach((agent) => {
    events.push({
      delayMs: 9800,
      event: mkEvent("sector_agent_started", { agent }),
    });
  });

  buildSectorToolCalls().forEach((entry) => {
    events.push({
      delayMs: entry.delayMs,
      event: entry.event,
    });
  });

  events.push({
    delayMs: 18100,
    event: mkEvent("sector_agent_complete", { agent: "Labor", report: laborReport }),
  });
  events.push({
    delayMs: 19000,
    event: mkEvent("sector_agent_complete", { agent: "Housing", report: housingReport }),
  });
  events.push({
    delayMs: 19900,
    event: mkEvent("sector_agent_complete", { agent: "Consumer", report: consumerReport }),
  });
  events.push({
    delayMs: 20700,
    event: mkEvent("sector_agent_complete", { agent: "Business", report: businessReport }),
  });

  events.push({ delayMs: 21600, event: mkEvent("debate_challenge", { challenge: burdenChallenge }) });
  events.push({ delayMs: 22100, event: mkEvent("debate_challenge", { challenge: housingChallenge }) });
  events.push({ delayMs: 22600, event: mkEvent("debate_challenge", { challenge: shiftingChallenge }) });
  events.push({ delayMs: 23100, event: mkEvent("debate_challenge", { challenge: vendorChallenge }) });

  events.push({
    delayMs: 24400,
    event: mkEvent("revision_complete", {
      rebuttal: {
        original_claim: burdenChallenge.target_claim,
        challenge: burdenChallenge,
        response: "revise",
        revised_claim: mkClaim(
          "Burden allocation synchronized at 50% pass-through and 50% internal absorption",
          "THEORETICAL",
          "Coordinated agent assumptions prevent overcounting burden channels.",
          ["Baker et al.", "revision ledger"],
          true,
        ),
        new_evidence: ["Cross-agent reconciliation worksheet"],
      },
    }),
  });

  events.push({
    delayMs: 25400,
    event: mkEvent("revision_complete", {
      rebuttal: {
        original_claim: housingChallenge.target_claim,
        challenge: housingChallenge,
        response: "revise",
        revised_claim: mkClaim(
          "Sustained housing effect revised to 0.5-1.5% with separate short-lived sentiment component",
          "THEORETICAL",
          "Mechanism clarity improved by splitting timescales.",
          ["Housing decomposition note"],
          true,
        ),
        new_evidence: ["Metro lease-cycle lag model"],
      },
    }),
  });

  events.push({
    delayMs: 26300,
    event: mkEvent("revision_complete", {
      rebuttal: {
        original_claim: shiftingChallenge.target_claim,
        challenge: shiftingChallenge,
        response: "revise",
        revised_claim: mkClaim(
          "All impact ranges now include a 30-50% profit-shifting scenario",
          "EMPIRICAL",
          "Behavioral adjustment lowers both fiscal gain and domestic side effects.",
          ["TWZ 2023", "OECD Pillar Two"],
          true,
        ),
        new_evidence: ["International tax structuring sensitivity run"],
      },
    }),
  });

  events.push({
    delayMs: 27300,
    event: mkEvent("revision_complete", {
      rebuttal: {
        original_claim: vendorChallenge.target_claim,
        challenge: vendorChallenge,
        response: "concede",
        revised_claim: mkClaim(
          "Vendor-spend contraction downgraded to SPECULATIVE with reduced range ($8B-$25B)",
          "SPECULATIVE",
          "Tax-only shock evidence is weaker than downturn-era analogies.",
          ["Business concession note"],
          false,
        ),
        new_evidence: ["Gross-margin resilience checks"],
      },
    }),
  });

  events.push({
    delayMs: 47000,
    event: mkEvent("synthesis_complete", { report: buildSynthesisReport(query || POLICY_TITLE) }),
  });

  return events;
}
