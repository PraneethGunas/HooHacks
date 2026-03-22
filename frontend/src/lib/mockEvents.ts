import type {
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
  _unused?: boolean,
): CausalClaim => ({
  claim,
  cause: "Corporate tax increase on large tech firms",
  effect: claim,
  mechanism,
  confidence,
  evidence,
  assumptions: ["Large firms adjust through a mix of pricing, shareholder returns, and cost optimization"],
  sensitivity: "Profit-shifting intensity and cloud pricing competition",
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
  agent_mode: "single_shot",
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
  agent_mode: "agentic",
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
  agent_mode: "agentic",
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
  agent_mode: "single_shot",
};

function buildSynthesisReport(query: string): SynthesisReport {
  return {
    meta: {
      version: "2.0",
      generated_at: new Date().toISOString(),
      pipeline_duration_seconds: 47,
      total_tool_calls: 52,
      agents_completed: ["classifier", "analyst", "labor", "housing", "consumer", "business", "synthesis"],
      agents_missing: [],
      model_used: "claude-opus-4-6",
      query: query || POLICY_TITLE,
    },
    policy: {
      title: query || POLICY_TITLE,
      one_liner: "A 30% federal corporate tax increase targeting technology companies with annual revenue exceeding $50 billion.",
      type: "Corporate tax increase with sector targeting",
      geography: "United States (federal)",
      effective_date: "2027-01-01",
      current_baseline: "21% federal corporate tax rate (TCJA 2017); large tech firms pay ~15-18% effective rate after deductions.",
      proposed_change: "Increase federal rate to 30% (9pp absolute increase) applied to firms with >$50B annual revenue.",
      estimated_annual_cost: "Static revenue projection: $80B-$120B. Dynamic estimate after behavioral response: $50B-$85B.",
      key_ambiguities: [
        "Phase-in timeline: immediate vs. 2-year phase-in affects first-year incidence.",
        "Scope definition: does $50B threshold apply to consolidated global revenue or US revenue only?",
        "Interaction with OECD global minimum tax — does this complicate profit shifting channels?",
        "Whether rate applies to pass-through entities or C-corp only.",
      ],
      working_assumptions: [
        "Threshold applies to annual consolidated global revenue; measured on a 3-year rolling average.",
        "Rate increase is permanent; no sunset clause or phase-out.",
        "Firm must have US operations; applies to US-source income and repatriated foreign income.",
        "Behavioral response includes profit shifting (30-50%), modest labor cuts (5-10% of burden), and partial price pass-through (40-60% in concentrated sectors).",
        "No interaction with proposed wealth taxes, minimum book income tax, or other concurrent reforms.",
      ],
    },
    headline: {
      verdict: "Significant net federal revenue gain with modest but concentrated negative spillovers to tech workers and downstream consumers.",
      bottom_line: "The policy achieves its primary fiscal goal of raising $50B-$85B annually. The burden distribution tilts toward shareholder returns (largest share), with smaller but material effects on employment growth, wage dynamics in major tech hubs, and cloud/SaaS pricing. Geographic and sectoral inequality effects are notable but not economy-wide.",
      confidence: "THEORETICAL",
      confidence_explanation: "Fiscal revenue effect is empirically grounded in comparable international tax increases and US tax-elasticity literature. Employment and wage-growth impacts are more speculative because US large-firm labor adjustment depends on concurrent hiring in AI and other segments. Price pass-through depends on oligopoly behavior, which is subject to competitive dynamics not fully predictable ex-ante.",
    },
    headline_metrics: [
      {
        id: "revenue_gain",
        label: "Federal Revenue Gain",
        value: "$50B-$85B",
        range: { low: "$50B", central: "$68B", high: "$85B" },
        unit: "annual",
        direction: "positive",
        confidence: "EMPIRICAL",
        icon: "📊",
        context: "After accounting for 30-50% profit-shifting behavior. Static estimate $80B-$120B; behavioral responses reduce by ~$15B-$35B.",
      },
      {
        id: "employment_impact",
        label: "Direct Tech Employment Change",
        value: "-14K to -35K",
        range: { low: "-14K", central: "-24K", high: "-35K" },
        unit: "jobs",
        direction: "negative",
        confidence: "THEORETICAL",
        icon: "👥",
        context: "Concentrated in large firms above $50B threshold. Implies 0.4-1.1% of direct tech workforce affected over 18-month adjustment window.",
      },
      {
        id: "cloud_pricing",
        label: "Cloud/SaaS Price Increase",
        value: "+0.7% to +2.0%",
        range: { low: "+0.7%", central: "+1.3%", high: "+2.0%" },
        unit: "price inflation",
        direction: "negative",
        confidence: "THEORETICAL",
        icon: "☁️",
        context: "Assumes 40-60% pass-through in oligopoly cloud market. Range reflects category concentration differences (AWS/Azure higher pass-through than open-source alternatives).",
      },
      {
        id: "household_cost",
        label: "Median Tech-Worker Household Annual Impact",
        value: "-$1,200 to -$3,800",
        range: { low: "-$1,200", central: "-$2,400", high: "-$3,800" },
        unit: "annual",
        direction: "negative",
        confidence: "THEORETICAL",
        icon: "💰",
        context: "Blend of reduced wage growth (-$800 to -$2,200 from slower comp growth), housing softening (+$100 to -$400 savings in tech hubs), and indirect cloud cost pass-through (-$600 to -$2,000).",
      },
      {
        id: "competitive_distortion",
        label: "Mid-Size Tech Competitiveness Gain",
        value: "~6pp tax cost advantage",
        range: { low: "5pp", central: "6pp", high: "7pp" },
        unit: "effective tax rate differential",
        direction: "positive",
        confidence: "THEORETICAL",
        icon: "📈",
        context: "Firms at $49B-$50B revenue face no increase; firms at $51B-$55B face full 30% rate. Creates incentive to stay below $50B, favoring mid-size competitors.",
      },
    ],
    waterfall: {
      title: "30% Corporate Tax Increase — Burden Distribution Flow",
      subtitle: "Median Tech Worker Household in SF Bay Area ($200k income; $2k/mo tech industry comp component)",
      household_profile: "Household A: 2 tech-sector workers (mid-level IC + PM), $200k joint household income, $50k in tech-company stock/RSUs, $420k SF Bay Area home value.",
      steps: [
        {
          label: "Gross tax increase on firm ($1.2T revenue firm example)",
          value: 1200,
          cumulative: 1200,
          type: "inflow",
          source_agent: "Business",
          note: "Applied to $1.2T firm subset earning ~$150B annually. Aggregate affected firms: ~$1.8T revenue, ~$180B taxable income.",
        },
        {
          label: "Profit shifting / offshore shift (40% avoidance)",
          value: -480,
          cumulative: 720,
          type: "outflow",
          source_agent: "Business",
          note: "IP transfer, expense relocation, earnings stripping reduce effective incidence.",
        },
        {
          label: "Remaining incidence",
          value: 720,
          cumulative: 720,
          type: "neutral",
          source_agent: "Business",
          note: "Net revenue to government and adjustments to firm behavior.",
        },
        {
          label: "Shareholder distributions (buybacks/dividends cut by 35%)",
          value: -252,
          cumulative: 468,
          type: "outflow",
          source_agent: "Business",
          note: "Largest flexible adjustment. Affects stock price appreciation and dividend income; weighted household impact ~$500-$1,200/yr.",
        },
        {
          label: "Compensation & hiring freeze (hiring growth slows 2-3pp)",
          value: -108,
          cumulative: 360,
          type: "outflow",
          source_agent: "Labor",
          note: "Wage growth declines 0.3-0.8pp annually. For household $200k income, reduced bonus/equity growth ≈ $800-$2,200/yr.",
        },
        {
          label: "R&D reallocation (5K-25K roles shift offshore)",
          value: -72,
          cumulative: 288,
          type: "outflow",
          source_agent: "Labor",
          note: "Second-order effect. Career progression and remote-work options affected; concentrated risk in specific high-skill categories.",
        },
        {
          label: "Cloud/SaaS price pass-through (1% avg, 0.7-2.0% range)",
          value: -36,
          cumulative: 252,
          type: "outflow",
          source_agent: "Consumer",
          note: "Household cloud/SaaS spend ~$3k/yr (subscriptions, storage, B2B tools); 1% ≈ $30-80/yr impact.",
        },
        {
          label: "Vendor ecosystem contraction (indirect impact)",
          value: -18,
          cumulative: 234,
          type: "outflow",
          source_agent: "Business",
          note: "Procurement cuts ripple through contractor/vendor payroll; household risk indirect via local unemployment.",
        },
        {
          label: "Housing rent softening benefit (SF/Seattle only, 0.5-1.5%)",
          value: 84,
          cumulative: 318,
          type: "inflow",
          source_agent: "Housing",
          note: "SF median tech-hub rent $3,450/mo; 1% decline ≈ $414/yr household benefit (partial offset).",
        },
        {
          label: "Net monthly household impact",
          value: 265,
          cumulative: 265,
          type: "net",
          source_agent: "Synthesis",
          note: "Median: -$100 to -$320/mo. Range: -$1,200 to -$3,800/year depending on RSU vesting, spouse employment sector, metro.",
        },
      ],
      net_monthly: -210,
      net_annual: -2520,
      pct_of_income: -1.26,
    },
    impact_matrix: {
      title: "Distributional Impact Matrix",
      subtitle: "Net monthly household impact (dollars and % of income) across income tiers, geographies, and household types",
      income_tiers: [
        { id: "low", label: "Low-income ($30k-$60k)", monthly: 45000 },
        { id: "mid", label: "Middle-income ($75k-$150k)", monthly: 110000 },
        { id: "upper", label: "Upper-income ($150k-$250k)", monthly: 190000 },
        { id: "high", label: "High-income ($250k+)", monthly: 350000 },
      ],
      geographies: [
        { id: "sf_bay", label: "SF Bay Area", example: "San Francisco, Palo Alto, Mountain View" },
        { id: "seattle", label: "Seattle Metro", example: "Seattle, Bellevue, Redmond" },
        { id: "denver", label: "Denver / Mountain West", example: "Denver, Boulder, Austin" },
        { id: "midwest", label: "Midwest / Southeast", example: "Chicago, Atlanta, Phoenix" },
      ],
      household_types: [
        { id: "dual_tech", label: "Dual Tech-Worker Household" },
        { id: "single_tech", label: "Single Tech-Worker Household" },
        { id: "non_tech", label: "Non-Tech Household (indirect effects only)" },
      ],
      cells: [
        {
          income: "Upper-income ($150k-$250k)",
          type: "Dual Tech-Worker Household",
          geography: "SF Bay Area",
          net_monthly: { low: -180, central: -280, high: -380 },
          net_annual: { low: -2160, central: -3360, high: -4560 },
          pct_of_income: { low: -1.08, central: -1.68, high: -2.28 },
          confidence: "THEORETICAL",
          verdict: "Modest negative impact; concentrated in wage growth, partially offset by housing softening.",
          dominant_inflow: "Housing rent decline (-$200-$400/yr)",
          dominant_outflow: "Reduced bonus/equity growth (-$2,400-$3,200/yr)",
          note: "Household with ~$180k/yr base + $20k-30k variable comp. One RSU grant (~$50k vesting over 4yr) at risk if hiring slows.",
        },
        {
          income: "Middle-income ($75k-$150k)",
          type: "Single Tech-Worker Household",
          geography: "Seattle Metro",
          net_monthly: { low: -80, central: -140, high: -200 },
          net_annual: { low: -960, central: -1680, high: -2400 },
          pct_of_income: { low: -0.96, central: -1.68, high: -2.40 },
          confidence: "THEORETICAL",
          verdict: "Small negative impact; single income stream means higher employment risk.",
          dominant_inflow: "Housing benefit (-$150-$250/yr, limited RSU appreciation)",
          dominant_outflow: "Wage growth slowdown (-$800-$1,200/yr)",
          note: "Single tech-worker household; higher sensitivity to hiring freeze or R&D offshore shift.",
        },
        {
          income: "Low-income ($30k-$60k)",
          type: "Non-Tech Household",
          geography: "Denver / Mountain West",
          net_monthly: { low: -5, central: -15, high: -30 },
          net_annual: { low: -60, central: -180, high: -360 },
          pct_of_income: { low: -0.12, central: -0.36, high: -0.72 },
          confidence: "THEORETICAL",
          verdict: "Minimal direct impact; indirect cloud cost pass-through very small. Minimal housing benefit.",
          dominant_inflow: "None substantial",
          dominant_outflow: "Cloud/SaaS subscription cost (+$20-40/yr); tech-vendor job losses (low probability)",
          note: "Non-tech household; no wage/equity exposure. Cloud cost impact ~0.5% of tech spending. Vendor layoff risk <2%.",
        },
        {
          income: "High-income ($250k+)",
          type: "Dual Tech-Worker Household",
          geography: "SF Bay Area",
          net_monthly: { low: -800, central: -1200, high: -1600 },
          net_annual: { low: -9600, central: -14400, high: -19200 },
          pct_of_income: { low: -1.09, central: -1.64, high: -2.19 },
          confidence: "THEORETICAL",
          verdict: "Largest absolute impact in dollars (due to RSU/equity exposure), but smallest as pct of income.",
          dominant_inflow: "Housing benefit (-$400-600/yr); concentrated-market tax incentive effects",
          dominant_outflow: "Reduced buybacks & dividends (-$4,800-8,000/yr from lower stock price appreciation); wage/comp slowdown (-$3,600-7,200/yr)",
          note: "Household with $250k+ base, $50k-100k RSUs, significant equity holdings. Buyback reduction most material loss vector.",
        },
      ],
    },
    category_breakdown: {
      title: "Price Changes by Spending Category",
      subtitle: "How each category of spending is affected by the corporate tax increase",
      categories: [
      {
        name: "Wage & Compensation Growth",
        icon: "💼",
        pct_change: { low: -0.3, central: -0.55, high: -0.8 },
        dollar_impact_monthly: { low: -25, central: -55, high: -110 },
        budget_share_low_income: 0.0,
        budget_share_middle_income: 0.22,
        budget_share_high_income: 0.18,
        pass_through_rate: "Direct (100% of tax burden reduction takes wage form among adjusting firms)",
        time_to_full_effect: "12-18 months (staggered across hiring cohorts and bonus cycles)",
        source_agent: "Labor",
        confidence: "THEORETICAL",
        explanation: "Firms adjust headcount, bonus pools, and equity grant sizes. Tech sector wage growth typically 3-5%/yr; decline to 2.5-4.5% likely.",
        note: "Does not include stock buyback effects (which affect equity holders, not wage earners directly).",
      },
      {
        name: "Cloud & SaaS Subscription Costs",
        icon: "☁️",
        pct_change: { low: 0.7, central: 1.3, high: 2.0 },
        dollar_impact_monthly: { low: 2, central: 3, high: 5 },
        budget_share_low_income: 0.1,
        budget_share_middle_income: 0.08,
        budget_share_high_income: 0.06,
        pass_through_rate: "40-60% of tax increase passed to consumers (oligopoly model: Baker et al.)",
        time_to_full_effect: "6-12 months (price increases typically announced in Q1 or Q3 for following month/quarter)",
        source_agent: "Consumer",
        confidence: "THEORETICAL",
        explanation: "AWS, Azure, GCP have high switching costs and concentrated market share. Smaller cloud vendors may compete on price.",
        note: "Impact varies by category: enterprise SaaS (higher pass-through, 1.5-2%) vs. consumer cloud storage (lower, 0.3-0.7%).",
      },
      {
        name: "Housing Costs (Tech Hubs)",
        icon: "🏠",
        pct_change: { low: -0.5, central: -1.0, high: -1.5 },
        dollar_impact_monthly: { low: -15, central: -35, high: -60 },
        budget_share_low_income: 0.32,
        budget_share_middle_income: 0.28,
        budget_share_high_income: 0.24,
        pass_through_rate: "Structural demand shift (not price pass-through) — reduced high-income purchasing power → rent softening",
        time_to_full_effect: "18-36 months (lease churn cycles in high-rent markets)",
        source_agent: "Housing",
        confidence: "THEORETICAL",
        explanation: "SF/Seattle rents peaked in 2022; already soft. Tax policy + slower comp growth reduces institutional investor and tech-worker demand.",
        note: "Only applies to SF, Seattle, Austin, and similar high-cost tech hubs. Mid-tier and low-cost metros see no effect.",
      },
      {
        name: "Vendor/Contractor Ecosystem Contraction",
        icon: "🤝",
        pct_change: { low: -1.5, central: -3.0, high: -5.0 },
        dollar_impact_monthly: { low: 0, central: -10, high: -25 },
        budget_share_low_income: 0.05,
        budget_share_middle_income: 0.08,
        budget_share_high_income: 0.12,
        pass_through_rate: "Procurement reductions flow directly to vendor payroll cuts (indirect employment effect)",
        time_to_full_effect: "3-9 months (procurement cycles shorter than hiring; contracts renegotiated quickly)",
        source_agent: "Business",
        confidence: "SPECULATIVE",
        explanation: "Vendor spend and contractor employment are easiest to adjust. Risk is concentrated in IT services, consulting, logistics contracting.",
        note: "Behavioral response depends on management philosophy: some firms cut vendors, others accept margin compression. Highly uncertain.",
      },
    ]},
    timeline: {
      title: "When Will You Feel the Impact?",
      subtitle: "Cumulative net monthly effect over time for median tech-worker household",
      household_profile: "Senior SWE household, $200K income, SF Bay Area renter",
      phases: [
      {
        label: "Phase 1: Policy Announcement & Expectation Formation (Months 1-3)",
        period_start: 0,
        period_end: 3,
        cumulative_net_monthly: { low: 0, central: -50, high: -100 },
        what_happens: [
          "Markets reprice tech sector stock (2-4% decline typical for large-cap tech)",
          "Firms begin modeling tax scenarios and adjusting FY2027 budgets",
          "Hiring pause in discretionary roles (advisory, consulting, non-critical R&D)",
          "Tech workers assess mobility; some senior talent explores international postings",
        ],
        mood: "Uncertainty & caution",
        dominant_driver: "Anticipatory effects from market repricing and strategic pause",
      },
      {
        label: "Phase 2: Structural Adjustments (Months 4-12)",
        period_start: 4,
        period_end: 12,
        cumulative_net_monthly: { low: -150, central: -250, high: -350 },
        what_happens: [
          "Firms execute hiring slowdown; contractor spend declines 8-12%",
          "Bonus pools reduced for mid-level staff; equity grant rates cut 5-15%",
          "R&D offshore acceleration; 5K-15K roles moved to India, Ireland, Canada",
          "Cloud vendors raise prices (staggered announcements, bundled with feature updates)",
          "Tech-hub housing sentiment turns; rent growth stalls in SF, Seattle",
        ],
        mood: "Adjustment & realization",
        dominant_driver: "Labor-market adjustment (hiring/bonus slowdown) + cloud pricing",
      },
      {
        label: "Phase 3: Partial Rebound (Months 13-24)",
        period_start: 13,
        period_end: 24,
        cumulative_net_monthly: { low: -100, central: -200, high: -300 },
        what_happens: [
          "AI hiring boom partially offsets core tech compression (new roles in ML/ops)",
          "Buyback reduction most durable; shareholder distributions remain suppressed",
          "Housing effects stabilize; rent growth in tech hubs remains 1-2pp below national trend",
          "Mid-size tech firms gain share; acquisition activity increases (cost of capital advantage)",
          "Profit-shifting channels fully operational; 35-50% of tax impact avoided",
        ],
        mood: "Mixed outlook — some sectors thriving, others flat",
        dominant_driver: "Heterogeneous tech sector response (AI boom vs. legacy tech stagnation)",
      },
      {
        label: "Phase 4: Medium-Term Equilibrium (Years 3-5)",
        period_start: 25,
        period_end: 60,
        cumulative_net_monthly: { low: -120, central: -210, high: -290 },
        what_happens: [
          "Wage growth in tech sector stabilizes 0.3-0.8pp below historical trend (permanent)",
          "Cloud/SaaS prices remain 0.7-2.0% elevated (structural)",
          "Housing remains softened in concentrated hubs, but doesn't collapse (supply constraints)",
          "Vendor ecosystem smaller but stabilized; net 25K-70K indirect job loss",
          "Federal revenues $50B-$85B/yr higher; distributed across defense, entitlements, deficit reduction",
        ],
        mood: "Acceptance; economy adjusts around new baseline",
        dominant_driver: "Behavioral response convergence; new steady-state equilibrium",
      },
      {
        label: "Phase 5: Longer-Term Considerations (Years 5+)",
        period_start: 60,
        period_end: 120,
        cumulative_net_monthly: { low: -130, central: -220, high: -310 },
        what_happens: [
          "Compounding effect: AI investment location decisions now factor in 30% tax rate",
          "International tech investment tilts toward Canada, EU, India (if no global minimum tax)",
          "Housing in tech hubs may rebound if domestic AI boom dominates offshore concerns",
          "Cliff-effect incentives: firms at $48B-$52B revenue experience significant restructuring",
          "Political dynamics: policy robustness depends on electoral cycles and competing revenue proposals",
        ],
        mood: "Structural uncertainty; long-term dynamics diverge by sub-sector",
        dominant_driver: "Investment location decisions and global tax coordination",
      },
    ]},
    winners_losers: {
      title: "Winners, Losers, and Mixed Effects",
      winners: [
        {
          profile: "Mid-size tech firms ($10B-$48B revenue)",
          icon: "📈",
          net_monthly_range: "+$50M to +$300M (per firm, reduced competitive pressure)",
          pct_of_income_range: "Not applicable (firm-level metric)",
          why: "Larger firms face 30% rate; mid-size firms gain cost-of-capital advantage. Can undercut pricing and accelerate M&A acquisitions.",
          confidence: "THEORETICAL",
          impact_quality: "Positive",
          caveat: "Only lasts until mid-size firm crosses $50B threshold (creates cliff incentive).",
          depends_on: "No phase-in or smooth graduation schedule; hard threshold.",
        },
        {
          profile: "Tenants in tech-hub metro areas (SF, Seattle, Austin)",
          icon: "🏘️",
          net_monthly_range: "-$50 to +$100/mo (housing rent savings)",
          pct_of_income_range: "0.1% to 0.5%",
          why: "Reduced high-income bidding power + slower tech-worker comp growth = downward pressure on rents.",
          confidence: "THEORETICAL",
          impact_quality: "Positive (savings)",
          caveat: "Effect is small and only in concentrated metros. Non-tech workers in same metros see no comp effect to offset (pure housing benefit).",
          depends_on: "Magnitude of employment adjustment in local tech sector.",
        },
        {
          profile: "Non-tech households in non-tech metros",
          icon: "👥",
          net_monthly_range: "$0 to $5/mo (minimal cloud cost pass-through, no direct effect)",
          pct_of_income_range: "0%",
          why: "No direct exposure to tech sector employment or equity. Cloud/SaaS cost increase very small. Housing unaffected.",
          confidence: "THEORETICAL",
          impact_quality: "Neutral",
          caveat: "Minimal effects mean policy is largely invisible to broad public; hard to explain distributional gains.",
          depends_on: "Second-order fiscal effects (if $50B-85B revenues fund other programs).",
        },
      ],
      losers: [
        {
          profile: "Tech-sector workers in large firms ($50B+ revenue)",
          icon: "👨‍💼",
          net_monthly_range: "-$100 to -$320/mo (wage growth slowdown, equity grant reduction)",
          pct_of_income_range: "-0.6% to -1.9%",
          why: "Direct incidence through hiring slowdown, reduced bonus pools, slower equity vesting. Largest absolute impact in dollars.",
          confidence: "THEORETICAL",
          impact_quality: "Negative",
          caveat: "Effect diluted by AI hiring boom (some offsetting opportunities). Magnitude depends on firm-specific responses.",
          depends_on: "Concurrent labor-market dynamics in AI, cloud infrastructure, and automation sectors.",
        },
        {
          profile: "Shareholders and equity holders of affected firms",
          icon: "📉",
          net_monthly_range: "-$300 to -$1,200/mo (reduced buybacks, lower dividend growth)",
          pct_of_income_range: "-0.5% to -2.5% (depends on portfolio concentration)",
          why: "Buyback reduction is largest and most durable adjustment channel. Affects stock price appreciation and dividend yields.",
          confidence: "THEORETICAL",
          impact_quality: "Negative",
          caveat: "Smaller impact for diversified portfolios; concentrated impact for tech-heavy investors or large shareholders.",
          depends_on: "Payout policy shifts and market competition for capital.",
        },
      ],
      mixed: [
        {
          profile: "Tech vendor and IT-services ecosystem (contractors, consultants, SaaS companies)",
          icon: "🤔",
          net_monthly_range: "-$8B to -$25B annual ecosystem spend; -25K to -70K indirect jobs",
          pct_of_income_range: "Ecosystem-level metric",
          why: "Large firms cut vendor spend (quick adjustment lever), but smaller firms gain share. Cloud vendors raise prices but compete harder for enterprise customers.",
          confidence: "SPECULATIVE",
          impact_quality: "Mixed (sector contraction but competitive reallocation)",
          caveat: "Outcome depends heavily on how firms balance buybacks vs. opex cuts. Management discretion dominates.",
          depends_on: "Capital discipline and shareholder pressure on management; competitive dynamics within vendor ecosystem.",
        },
      ],
      distributional_verdict: {
        progressive_or_regressive: "Moderately progressive at the income level (higher earners more exposed to tech sector); regressive at the household consumption level (cloud cost pass-through hits all income tiers).",
        explanation: "Upper-income households overexposed to tech employment and equity; middle-income and lower-income households bear small but universal cloud-cost burden and benefit modestly from housing softening.",
        geographic_equity: "Concentrated burden in major tech hubs (SF, Seattle, Austin); minimal effect in non-tech metros. Creates inter-regional equity concerns.",
        generational_equity: "Millennials and Gen-X with tech equity holdings (mid to late career) lose most; Gen-Z entrants benefit from lower entry-level comp but face compressed career-growth trajectories.",
      },
    },
    geographic_impact: {
      title: "Geographic Regional Impacts",
      regions: [
        {
          id: "sf_bay",
          name: "San Francisco Bay Area",
          examples: "San Francisco, Palo Alto, Mountain View, San Jose",
          net_direction: "Negative overall (job/comp loss > housing benefit)",
          color: "#ef4444",
          rent_impact_severity: "High: 0.5-1.5% sustained softening",
          price_impact_severity: "High: Cloud/SaaS cost pass-through (users in Bay Area more exposed to enterprise cloud vendors)",
          net_monthly_range_median_hh: "-$150 to -$280 (dual tech worker); -$60 to -$100 (single tech worker)",
          explanation: "Largest concentration of affected large-cap tech firms (Apple, Google, Meta, Nvidia, Intel, Cisco nearby). Employment shock most material here. Housing softens but other costs rise.",
          key_factor: "Large-firm employment concentration: 40% of US tech employment in Bay Area metros.",
        },
        {
          id: "seattle",
          name: "Seattle Metro",
          examples: "Seattle, Bellevue, Redmond, Tacoma",
          net_direction: "Negative (Amazon HQ2 dominates; hiring slowdown in cloud services and logistics)",
          color: "#f97316",
          rent_impact_severity: "Moderate: 0.3-0.8% rent softening",
          price_impact_severity: "Moderate: AWS cloud services (Amazon large employer; pass-through likely)",
          net_monthly_range_median_hh: "-$80 to -$200 (single tech worker); -$40 to -$80 (non-tech household with AWS indirect exposure)",
          explanation: "Amazon (~$2.5T market cap, $500B+ revenue) among largest affected. Hiring pause hits local construction, real estate, restaurants, services. Housing benefit partially offsets.",
          key_factor: "Single large employer dominance (Amazon); concentration risk for local economy.",
        },
        {
          id: "denver_mountain",
          name: "Denver / Mountain West",
          examples: "Denver, Boulder, Austin, Salt Lake City, Boise",
          net_direction: "Modestly negative (secondary tech hub; benefits from some decentralization but grows slower)",
          color: "#fbbf24",
          rent_impact_severity: "Low: 0.1-0.3% softening (benefits from Bay Area/Seattle outmigration may offset)",
          price_impact_severity: "Low: Indirect cloud cost exposure only",
          net_monthly_range_median_hh: "-$20 to -$60 (single remote tech worker)",
          explanation: "Growing secondary tech hub with lower cost of living. Some Bay Area talent relocates (remote work + Texas immigration trends). Cloud cost pass-through affects businesses more than households.",
          key_factor: "Decentralization + secondary hub status = partial offset of national tech slowdown.",
        },
      ],
    },
    consistency_report: {
      title: "Agent Consistency Audit & Data Reconciliation",
      inconsistencies_found: 2,
      adjustments: [
        {
          variable: "R&D employment relocation scale",
          original_source: "Labor agent model (5K-25K jobs offshore)",
          original_value: "25K median estimate",
          issue: "Business agent noted only $8B-25B vendor spend cut, implying ~15K-70K indirect jobs. R&D intensity (cost per job) implied different scale in Labor estimate.",
          resolved_source: "Business agent's vendor ecosystem estimate (validated by Census CBP concentration data) + Labor agent's elasticity estimate",
          resolved_value: "5K-15K direct R&D offshore + 15K-40K vendor ecosystem indirect (cross-validated).",
          impact_on_output: "Reduces total employment loss estimate by 5-10K at median. Waterfall step adjusted downward.",
          severity: "Low — direction of effect unchanged; magnitude confidence narrowed from 5K-25K to 5K-15K.",
        },
        {
          variable: "Cloud price pass-through rate",
          original_source: "Consumer agent (40-60% Baker et al.); Business agent (one hyperscaler hold-price scenario collapses to 0%)",
          original_value: "40-60% vs. potential 0%",
          issue: "Two scenarios not reconciled. Central estimate should weight probability of price discipline vs. competitive pressure.",
          resolved_source: "Merged frameworks: base case 40-60% pass-through (oligopoly model); sensitivity: 0-20% if aggressive price competition",
          resolved_value: "Central 0.7-2.0% price increase (assuming 40-60% pass-through); sensitivity range 0-1.5% (if competition intensifies).",
          impact_on_output: "Household impact range widened slightly on upside; note added about competitive downside risk.",
          severity: "Low-Medium — affects consumer impact quantification but not direction.",
        },
      ],
      unresolved_gaps: [
        "International tax coordination: If OECD global minimum tax reaches consensus at 15%, does $50B US threshold create treaty conflicts? No cross-border tax treaty data available.",
        "Profit-shifting channels post-BEAT/GILTI: Current 30-50% avoidance estimate relies on 2023 academic literature. 2025 regulatory changes (potential interest deduction caps, updated transfer pricing) not modeled.",
        "AI-driven labor-market offset: Concurrent AI hiring boom in ML ops, infrastructure could exceed tech layoff from tax policy. No reliable real-time AI hiring data; Labor agent uses 2024 baseline.",
        "Duration of buyback suppression: Model assumes multi-year buyback reduction. But if tax becomes permanent and firms adjust target payout ratios, pressure to resume distributions could materialize faster.",
      ],
    },
    confidence_assessment: {
      overall: "THEORETICAL",
      by_component: [
        {
          component: "Federal revenue gain ($50B-$85B/year)",
          confidence: "EMPIRICAL",
          reasoning: "US corporate tax elasticity well-studied; OECD 2023 minimum-tax assessments provide benchmarks. 30-50% behavioral avoidance consistent with historical data. Confidence: HIGH.",
        },
        {
          component: "Employment impact (-14K to -35K direct tech jobs)",
          confidence: "THEORETICAL",
          reasoning: "Based on labor elasticity estimates and UK 2023 corporate tax revision precedents. US firm behavior depends on concurrent AI hiring, capital allocation, and acquisition activity — not fully predictable. Confidence: MEDIUM.",
        },
        {
          component: "Cloud/SaaS price pass-through (+0.7% to +2.0%)",
          confidence: "THEORETICAL",
          reasoning: "Oligopoly pricing literature (Baker et al., BEA oligopoly studies) suggests 40-60% pass-through. But outcome depends on competitive dynamics and regulation (cloud pricing scrutiny in Congress). Confidence: MEDIUM.",
        },
        {
          component: "Housing rent softening (SF/Seattle -0.5% to -1.5%)",
          confidence: "THEORETICAL",
          reasoning: "Based on metro employment concentration and housing elasticity. But housing supply constraints and remote-work trends (demand) could offset. Confidence: MEDIUM.",
        },
        {
          component: "Vendor ecosystem contraction (-$8B to -$25B spend; -25K to -70K indirect jobs)",
          confidence: "SPECULATIVE",
          reasoning: "Depends entirely on management preference: cut vendor spend vs. accept margin compression. No reliable signal of firm-level behavior prior to policy enactment. Confidence: LOW-MEDIUM.",
        },
      ],
      weakest_link: "Vendor ecosystem contraction and contractor labor-market impact. This is the least predictable adjustment channel and depends on firm-specific cost-of-capital constraints and shareholder pressure.",
      what_would_change_conclusion: [
        "If AI hiring boom is larger than current estimates (+50K-100K new roles in 2026-2027), employment-loss estimate could be zero or positive — dramatically changing policy verdict.",
        "If cloud vendors engage in aggressive price competition (one hyperscaler holds prices), cloud-cost pass-through could collapse to 0%, eliminating consumer price impact.",
        "If a global minimum tax treaty at 15% is ratified before 2027, profit-shifting incentive could fall to 15-25%, raising federal revenue gain to $70B-$100B (reducing behavioral avoidance).",
        "If Congress pairs this with interest deduction caps or updated GILTI rates, domestic tax base could expand, raising revenue gain and employment loss (less substitution to offshoring).",
      ],
    },
    evidence_summary: {
      title: "Key Studies & Evidence Consensus",
      key_studies: [
        {
          name: "Fuest, Janeba & Schjelderup (2019) — Corporate Tax and Wages",
          finding: "1pp corporate tax increase → 0.3-0.5pp wage growth slowdown in large firms with export sectors.",
          applicability: "High — US tech firms are heavily export-exposed; finding directly applies. Sensitivity: estimate uses lower end (0.3pp) to align with labor agent revision.",
          source_agent: "Labor",
        },
        {
          name: "Baker, Larcker & Wang (2022) — Oligopoly Pass-Through",
          finding: "Concentrated industries (HHI > 2000) pass through 40-60% of cost shocks to consumers; unconcentrated markets <25%.",
          applicability: "High — AWS/Azure/GCP form tight oligopoly (HHI ~2400). Pass-through estimate directly sourced.",
          source_agent: "Consumer",
        },
        {
          name: "UK Office of Budget Responsibility (2023) — Corporate Tax Rate Increase to 25%",
          finding: "Actual revenue increase £15B vs. static forecast £20B; behavioral avoidance consumed 25% of static estimate. Employment effects minimal (< 0.2%).",
          applicability: "Moderate — UK has strong profit-shifting incentives (Ireland, Netherlands). US avoidance likely 30-50% (higher). Employment effects in US less studied.",
          source_agent: "Analyst",
        },
      ],
      consensus: "Broad agreement across agents that federal revenue effect is material and robust (EMPIRICAL); employment and price effects are moderate but plausible (THEORETICAL); vendor-ecosystem contraction is the most uncertain channel (SPECULATIVE).",
      major_gap: "No US study of threshold-based tax policy (hard cliff at firm size) and its effects on restructuring incentives. Literature focuses on continuous tax-rate schedules. Model relies on tax-notch theory from behavioral-economics literature (weight-loss studies, tax bracket effects) — may not directly apply to corporate restructuring.",
    },
    data_sources: {
      title: "Agent Tool Calls & Data Sources",
      agents_and_calls: [
        {
          agent: "Analyst",
          tool_calls: 14,
          key_data: [
            "FRED corporate tax receipts (FCTAX), corporate profits after tax (CP)",
            "CBO baseline projection & revenue-scoring methodology",
            "Semantic Scholar: 'corporate tax incidence', 'profit-shifting elasticity'",
            "NBER working papers on tax elasticity and international taxation",
            "UK OBR 2023 corporate tax assessment",
          ],
          phases_completed: 5,
        },
        {
          agent: "Labor",
          tool_calls: 12,
          key_data: [
            "BLS employment & wage data for NAICS 5112 (software), 5415 (computer services), 5182 (data processing)",
            "Semantic Scholar: 'corporate tax elasticity employment', 'large-firm wage dynamics'",
            "SEC 10-K filings (sample: Apple, Google, Microsoft) for headcount and comp trends",
            "Fuest et al. labor-incidence estimates from academic databases",
          ],
          phases_completed: 4,
        },
        {
          agent: "Housing",
          tool_calls: 9,
          key_data: [
            "FRED metro-level rent indices (SF Bay, Seattle, Austin)",
            "Census housing-burden data by metro and income tier",
            "Semantic Scholar: 'local employment and housing demand', 'tech sector rent volatility'",
            "REIS market sentiment indices for tech-hub metros",
          ],
          phases_completed: 5,
        },
        {
          agent: "Consumer",
          tool_calls: 11,
          key_data: [
            "BLS CPI digital services & cloud categories (CUSR0000SEEE02 proxy)",
            "Baker et al. oligopoly pass-through literature",
            "Market share data: AWS ~31%, Azure ~25%, GCP ~11% of cloud market",
            "Subscription-price histories from SaaS vendors (public announcements)",
          ],
          phases_completed: 5,
        },
        {
          agent: "Business",
          tool_calls: 10,
          key_data: [
            "Census County Business Patterns (CBP): vendor ecosystem concentration and supplier revenue",
            "Semantic Scholar: 'corporate procurement sensitivity', 'tax incidence on vendor spend'",
            "SEC filings: R&D spend, buyback authorizations, vendor relationships (large firms)",
            "Tax-notch literature on firm restructuring incentives",
          ],
          phases_completed: 4,
        },
      ],
      total_tool_calls: 52,
      total_unique_data_series: 34,
      methodology_notes: [
        "All FRED and BLS data pulled with 3-year historical baseline to control for trend.",
        "Elasticity estimates cross-validated across 2+ academic sources where available.",
        "Behavioral avoidance rate (30-50%) sourced from Gravelle (2011 comprehensive review) and OECD minimum tax assessments.",
        "Timeline phases derived from historical tech-sector adjustment cycles (2020 COVID hiring, 2022 layoffs, 2024 AI reallocation).",
        "Confidence levels assigned per epistemology framework: EMPIRICAL (direct data), THEORETICAL (model-based), SPECULATIVE (scenario-dependent).",
      ],
    },
    narrative: {
      executive_summary:
        "A 30% corporate tax increase on US tech firms above $50B revenue would raise federal revenues by $50B-$85B annually after accounting for 30-50% behavioral profit-shifting. The policy concentrates negative effects in major tech hubs (SF Bay, Seattle) and among tech-sector workers and large shareholders, while imposing modest broad-based costs through cloud-service price increases and vendor-ecosystem contraction. The burden distribution is moderately progressive at the household income level (higher-income households more exposed to tech employment and equity) but regressive at the consumption level (cloud-cost pass-through affects all households). No major broad-based macroeconomic disruption is expected, but localized labor-market effects in tech metros could be significant, and the hard $50B threshold creates cliff-based incentives for corporate restructuring.",
      for_low_income:
        "If you earn $30k-$60k and don't work in tech, this policy will have minimal direct impact on you. You may see a small increase in cloud and software subscription costs (+$20-50/year), but that affects businesses you depend on more than direct household spending. If you live in a tech hub like SF or Austin, you might benefit slightly from softer rental markets (rents could decline 0.5-1.5% over 2-3 years). The primary benefit is federal government revenue ($50B-$85B/year) that could fund education, healthcare, or infrastructure — though that depends on Congressional spending priorities. The policy is largely invisible to non-tech households.",
      for_middle_income:
        "If you earn $75k-$150k and work in tech (or have a spouse who does), expect a 1-2% reduction in take-home income growth over 12-18 months. Your employer will likely slow hiring (affecting bonuses), reduce equity-grant sizes, and freeze discretionary raises. If you work outside tech, the impact is small: cloud subscriptions and software might cost 0.5-1% more, affecting business efficiency more than personal budgets. Housing relief is modest if you live in SF, Seattle, or Austin (0.1-0.5% of income savings), but could be absorbed by slower income growth. Career trajectory within large tech firms will be flatter for 2-3 years; lateral moves to smaller tech firms or non-tech sectors become more attractive.",
      for_upper_income:
        "If you earn $150k+ and hold tech-company equity (RSUs, stock, index funds with tech weight), prepare for material losses. Stock buyback reductions (the largest buffer firms use) directly reduce stock-price appreciation; expect 2-4% lower stock-price growth for large-cap tech over 2-3 years. Your bonus pools and equity grants will shrink 5-15% in the first 12-18 months. Dividend yields may decline slightly if firms redirect payouts to tax payments. The absolute-dollar impact is substantial ($5,000-$20,000/year for high-earning tech households), but as a percentage of income (~0.5-2%), it's manageable if you're diversified. Housing markets in tech hubs may soften slightly (offsetting a small portion of your investment loss). Consider rebalancing portfolios away from large-cap tech.",
      for_small_business:
        "If you own or manage a small tech firm (< $50B revenue), this creates a structural advantage: you face no rate increase while larger competitors do. You can undercut their pricing, attract their talent with equity offers, and acquire their distressed assets at discounts. However, if you're a vendor or contractor serving large tech firms, expect 8-15% cuts in procurement spend within 6-9 months — plan contingency: shift to smaller-firm customers or lower-cost service models. If you rely on cloud infrastructure (AWS, Azure), prepare for 1-2% cost increases; budget planning should include those line-item rises. The $50B threshold creates restructuring incentives for firms just above it — potential acquisition targets for you if you're patient and capitalized.",
      biggest_uncertainty:
        "The biggest unknown is how concurrent trends will interact: AI hiring may offset tech layoffs (potentially eliminating employment losses entirely), cloud vendors may compete harder on price (reducing pass-through to nearly zero), and international tax coordination (OECD minimum tax) may collapse profit-shifting channels (raising revenue gains). Additionally, Congress may pair this with other reforms (interest deduction caps, updated GILTI rates) that could amplify or dampen effects. Finally, firm-specific management responses to shareholder pressure are not predictable ex-ante: some will cut vendors aggressively, others will accept margin compression. The narrow path the policy takes through all these variables determines whether effects are 'moderate and manageable' or 'sharp and concentrated.'",
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

  // Classifier thinking events
  events.push({ delayMs: 100, event: mkEvent("classifier_thinking", { step_type: "phase_start", content: "Analyzing policy query and extracting structured parameters", phase: "1" }) });
  events.push({ delayMs: 180, event: mkEvent("classifier_thinking", { step_type: "reasoning", content: `Input query: "${query}"`, phase: "1" }) });
  events.push({ delayMs: 250, event: mkEvent("classifier_thinking", { step_type: "tool_call", content: "Invoking Google ADK classifier (Gemini Flash)", phase: "1", tool: "google_adk" }) });
  events.push({ delayMs: 380, event: mkEvent("classifier_thinking", { step_type: "tool_result", content: "ADK classification: policy_proposal (confidence: high)", phase: "1", tool: "google_adk" }) });
  events.push({ delayMs: 420, event: mkEvent("classifier_thinking", { step_type: "reasoning", content: "Identified policy type: policy_proposal", phase: "2" }) });
  events.push({ delayMs: 430, event: mkEvent("classifier_thinking", { step_type: "reasoning", content: "Extracted parameters: policy_action=Corporate tax increase, scope=Federal, threshold=>$50B revenue", phase: "2" }) });
  events.push({ delayMs: 440, event: mkEvent("classifier_thinking", { step_type: "phase_complete", content: "Classification complete — routing to Analyst Agent", phase: "2" }) });

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

  // Analyst events — 5-phase agentic flow with scrolling status labels
  const analystSteps: [string, string][] = [
    // Phase 1: Policy Specification (ReAct)
    ["phase_1_start", "Phase 1/5 · Policy Specification"],
    ["web_search_news", "Searching news: corporate tax increase tech sector 2026"],
    ["fred_get_series", "Pulling FRED: FCTAX — federal corporate tax receipts"],
    ["fetch_document_text", "Reading CBO baseline projection document"],
    ["phase_1_complete", "Policy spec complete — 3 tool calls, 4.2s"],
    // Phase 2: Baseline & Counterfactual (ReAct)
    ["phase_2_start", "Phase 2/5 · Baseline & Counterfactual"],
    ["fred_search", "Discovering FRED series for corporate profits, effective rates"],
    ["fred_get_series", "Pulling FRED: CP — corporate profits after tax"],
    ["bls_get_data", "BLS: tech sector employment, wage data (CES5051200001)"],
    ["phase_2_complete", "Baseline complete — 3 tool calls, 3.8s"],
    // Phase 3: Transmission Mapping (reasoning only)
    ["phase_3_start", "Phase 3/5 · Transmission Channel Mapping"],
    ["reasoning", "Mapping causal channels: profit margins → investment → hiring → wages"],
    ["phase_3_complete", "6 transmission channels identified"],
    // Phase 4: Evidence Gathering (ReAct)
    ["phase_4_start", "Phase 4/5 · Evidence Gathering"],
    ["search_academic_papers", "Searching: corporate tax elasticity of investment"],
    ["search_openalex", 'OpenAlex: "corporate tax" capital expenditure NBER'],
    ["search_cbo_reports", "CBO: revenue effects of corporate rate changes"],
    ["fetch_document_text", "Reading NBER working paper on tax incidence"],
    ["web_search_news", "UK corporate tax 25% 2023 outcomes investment"],
    ["phase_4_complete", "Evidence gathered — 5 tool calls, 5.1s"],
    // Phase 5: Synthesis (reasoning only)
    ["phase_5_start", "Phase 5/5 · Synthesis & Briefing"],
    ["reasoning", "Synthesizing analyst briefing with distributional analysis"],
    ["phase_5_complete", "Analyst briefing produced — 14 total tool calls"],
  ];

  analystSteps.forEach(([tool, queryText], index) => {
    events.push({
      delayMs: 1300 + index * 350,
      event: mkEvent("analyst_tool_call", { tool, query: queryText }),
    });
  });

  events.push({
    delayMs: 1300 + analystSteps.length * 350 + 200,
    event: mkEvent("analyst_complete", {
      briefing_summary: "Baseline assembled: ~18 firms above $50B, estimated static revenue gain $80B-$120B before behavioral response.",
      sources_found: 24,
      tool_calls_made: 14,
      mode: "agentic",
      phases_completed: 5,
    }),
  });

  events.push({
    delayMs: 10400,
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
    delayMs: 10750,
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
    delayMs: 11000,
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
      delayMs: 11200,
      event: mkEvent("sector_agent_started", { agent, agent_mode: (agent === "Housing" || agent === "Consumer") ? "agentic" : "single_shot" }),
    });
  });

  buildSectorToolCalls().forEach((entry) => {
    events.push({
      delayMs: entry.delayMs,
      event: entry.event,
    });
  });

  // --- Mock thinking events for agentic agents (Housing & Consumer) ---
  const housingThinking: Array<{ delayMs: number; step_type: string; content: string; phase?: string; tool?: string }> = [
    { delayMs: 10200, step_type: "phase_start", content: "Phase 1: Gathering baseline housing data for tech metros", phase: "1" },
    { delayMs: 10800, step_type: "tool_call", content: "Querying FRED for SF, Seattle, Austin rent time series", phase: "1", tool: "fred_get_series" },
    { delayMs: 11400, step_type: "tool_result", content: "Retrieved 36 months of rent data across 3 metros — SF median rent $3,450, Seattle $2,180", phase: "1", tool: "fred_get_series" },
    { delayMs: 11900, step_type: "reasoning", content: "SF rents already softened 4.2% since 2024 peak. Tech layoffs explain ~60% of that decline based on metro employment correlation.", phase: "1" },
    { delayMs: 12500, step_type: "phase_complete", content: "Baseline data collection complete", phase: "1" },
    { delayMs: 12800, step_type: "phase_start", content: "Phase 2: Modeling demand shock from reduced tech compensation", phase: "2" },
    { delayMs: 13400, step_type: "tool_call", content: "Searching academic papers on corporate tax incidence and housing markets", phase: "2", tool: "search_academic_papers" },
    { delayMs: 14000, step_type: "tool_result", content: "Found 4 relevant papers — key finding: 1pp corporate tax increase → 0.3-0.5% rent decline in concentrated metros", phase: "2", tool: "search_academic_papers" },
    { delayMs: 14600, step_type: "reasoning", content: "Applying elasticity: 30% tax increase on ~$2.1T revenue → estimated 0.5-1.5% sustained rent softening in SF/Seattle. Austin less affected due to diversified employer base.", phase: "2" },
    { delayMs: 15200, step_type: "phase_complete", content: "Demand modeling complete", phase: "2" },
    { delayMs: 15400, step_type: "tool_call", content: "Free sources insufficient for rent-regulation precedent data — initiating L402 micropayment to premium-legal-db", phase: "2", tool: "l402_fetch" },
    { delayMs: 15900, step_type: "tool_result", content: "L402 payment complete (10 sats) — received housing regulation impact assessments and rent-control precedent data", phase: "2", tool: "l402_fetch" },
    { delayMs: 16200, step_type: "phase_start", content: "Phase 3: Analyzing sentiment vs fundamental decomposition", phase: "3" },
    { delayMs: 16800, step_type: "reasoning", content: "Historical pattern: 2022-2023 tech layoffs caused 6-8% rent dip in SF but 40% rebounded within 6 months. Need to separate transient sentiment from structural demand shift.", phase: "3" },
    { delayMs: 17200, step_type: "reasoning", content: "Premium legal data confirms: rent-regulation precedents in SF show policy-driven declines of 0.8-2.1% in tech corridors, aligning with our elasticity estimates.", phase: "3" },
    { delayMs: 17600, step_type: "phase_complete", content: "Sentiment decomposition complete", phase: "3" },
    { delayMs: 17900, step_type: "phase_start", content: "Phase 4: Cross-sector dependency analysis", phase: "4" },
    { delayMs: 18400, step_type: "reasoning", content: "Housing impact depends on labor agent's employment estimates and consumer agent's spending patterns. If AI hiring offsets layoffs, housing impact could be near zero.", phase: "4" },
    { delayMs: 18900, step_type: "phase_complete", content: "Cross-sector analysis complete", phase: "4" },
    { delayMs: 19200, step_type: "phase_start", content: "Phase 5: Synthesizing housing sector report", phase: "5" },
    { delayMs: 19600, step_type: "reasoning", content: "Finalizing: sustained rent softening 0.5-1.5% in SF/Seattle, transient sentiment dip of 1-2% in first 3-6 months. Austin insulated. Confidence: THEORETICAL.", phase: "5" },
    { delayMs: 19800, step_type: "phase_complete", content: "Housing report synthesized", phase: "5" },
  ];

  housingThinking.forEach(({ delayMs, step_type, content, phase, tool }) => {
    events.push({
      delayMs,
      event: mkEvent("sector_agent_thinking", { agent: "Housing", step_type, content, phase, tool } as any),
    });
  });

  // Lightning payment triggered by Housing agent's L402 fetch (top-level event for LightningRow)
  events.push({
    delayMs: 15500,
    event: mkEvent("lightning_payment", {
      service: "premium-legal-db",
      invoice_amount_sats: 10,
      status: "paying",
      macaroon_received: false,
      payment_hash: "mockhash-housing-l402-001",
      duration_ms: 0,
    }),
  });
  events.push({
    delayMs: 15850,
    event: mkEvent("lightning_payment", {
      service: "premium-legal-db",
      invoice_amount_sats: 10,
      status: "paid",
      macaroon_received: true,
      payment_hash: "mockhash-housing-l402-001",
      duration_ms: 420,
    }),
  });

  const consumerThinking: Array<{ delayMs: number; step_type: string; content: string; phase?: string; tool?: string }> = [
    { delayMs: 10400, step_type: "phase_start", content: "Phase 1: Establishing consumer price baselines", phase: "1" },
    { delayMs: 11000, step_type: "tool_call", content: "Pulling BLS CPI data for digital services and cloud proxies", phase: "1", tool: "bls_get_series" },
    { delayMs: 11600, step_type: "tool_result", content: "CPI digital services up 2.1% YoY. Cloud infrastructure costs stable but enterprise software +3.4%", phase: "1", tool: "bls_get_series" },
    { delayMs: 12100, step_type: "reasoning", content: "Cloud market is oligopolistic (AWS 31%, Azure 25%, GCP 11%). High switching costs support partial pass-through of cost increases.", phase: "1" },
    { delayMs: 12700, step_type: "phase_complete", content: "Baseline data collection complete", phase: "1" },
    { delayMs: 13000, step_type: "phase_start", content: "Phase 2: Modeling price pass-through mechanisms", phase: "2" },
    { delayMs: 13600, step_type: "tool_call", content: "Searching for concentrated-market tax pass-through studies", phase: "2", tool: "search_academic_papers" },
    { delayMs: 14200, step_type: "tool_result", content: "Baker et al.: oligopoly pass-through rate 40-60% depending on market concentration", phase: "2", tool: "search_academic_papers" },
    { delayMs: 14800, step_type: "reasoning", content: "Applying Baker et al. framework: 30% tax increase × ~50% pass-through = 0.7-2.0% price increase on cloud/SaaS. Range depends on category concentration.", phase: "2" },
    { delayMs: 15400, step_type: "phase_complete", content: "Pass-through modeling complete", phase: "2" },
    { delayMs: 15700, step_type: "phase_start", content: "Phase 3: Estimating household-level impact", phase: "3" },
    { delayMs: 16300, step_type: "reasoning", content: "Most direct burden lands on enterprise software spend. Household impact modest: ~$25-80/year through indirect subscription cost increases.", phase: "3" },
    { delayMs: 16900, step_type: "phase_complete", content: "Household impact analysis complete", phase: "3" },
    { delayMs: 17200, step_type: "phase_start", content: "Phase 4: Feedback loop with labor and business sectors", phase: "4" },
    { delayMs: 17800, step_type: "reasoning", content: "Key feedback: more successful price pass-through reduces pressure for labor cuts. Price and payroll channels substitute each other in burden distribution.", phase: "4" },
    { delayMs: 18400, step_type: "phase_complete", content: "Feedback loop analysis complete", phase: "4" },
    { delayMs: 18700, step_type: "phase_start", content: "Phase 5: Compiling consumer sector report", phase: "5" },
    { delayMs: 19100, step_type: "reasoning", content: "Final assessment: cloud/SaaS +0.7-2.0%, household cost +$25-80/yr, pass-through collapses if one hyperscaler holds price. Confidence: THEORETICAL.", phase: "5" },
    { delayMs: 19600, step_type: "phase_complete", content: "Consumer report synthesized", phase: "5" },
  ];

  consumerThinking.forEach(({ delayMs, step_type, content, phase, tool }) => {
    events.push({
      delayMs,
      event: mkEvent("sector_agent_thinking", { agent: "Consumer", step_type, content, phase, tool } as any),
    });
  });

  events.push({
    delayMs: 18100,
    event: mkEvent("sector_agent_complete", { agent: "Labor", report: laborReport }),
  });
  events.push({
    delayMs: 20200,
    event: mkEvent("sector_agent_complete", { agent: "Housing", report: housingReport }),
  });
  events.push({
    delayMs: 20800,
    event: mkEvent("sector_agent_complete", { agent: "Consumer", report: consumerReport }),
  });
  events.push({
    delayMs: 21200,
    event: mkEvent("sector_agent_complete", { agent: "Business", report: businessReport }),
  });

  // Stage 3: Synthesis phases
  events.push({ delayMs: 22200, event: mkEvent("synthesis_phase", { phase: 1, name: "Consistency Audit", status: "running" }) });
  events.push({ delayMs: 24000, event: mkEvent("synthesis_phase", { phase: 1, name: "Consistency Audit", status: "complete" }) });
  events.push({ delayMs: 24200, event: mkEvent("synthesis_phase", { phase: 2, name: "Net Household Impact", status: "running" }) });
  events.push({ delayMs: 27000, event: mkEvent("synthesis_phase", { phase: 2, name: "Net Household Impact", status: "complete" }) });
  events.push({ delayMs: 27200, event: mkEvent("synthesis_phase", { phase: 3, name: "Winners & Losers", status: "running" }) });
  events.push({ delayMs: 30000, event: mkEvent("synthesis_phase", { phase: 3, name: "Winners & Losers", status: "complete" }) });
  events.push({ delayMs: 30200, event: mkEvent("synthesis_phase", { phase: 4, name: "Narrative & Timeline", status: "running" }) });
  events.push({ delayMs: 33000, event: mkEvent("synthesis_phase", { phase: 4, name: "Narrative & Timeline", status: "complete" }) });
  events.push({ delayMs: 33200, event: mkEvent("synthesis_phase", { phase: 5, name: "Analytics Payload", status: "running" }) });
  events.push({ delayMs: 36000, event: mkEvent("synthesis_phase", { phase: 5, name: "Analytics Payload", status: "complete" }) });

  events.push({
    delayMs: 37000,
    event: mkEvent("synthesis_complete", { report: buildSynthesisReport(query || POLICY_TITLE) }),
  });

  return events;
}
