"""System prompts for the Synthesis & Impact Dashboard agent."""

from __future__ import annotations

from backend.agents.schemas import AnalystBriefing
from backend.agents.housing.schemas import HousingReport
from backend.agents.consumer.schemas import ConsumerReport
from backend.agents.synthesis.schemas import (
    ConsistencyAuditOutput,
    NetImpactOutput,
    WinnersLosersOutput,
    NarrativeOutput,
    SynthesisReport,
)


SYNTHESIS_IDENTITY = """\
You are the Synthesis & Impact Dashboard Agent (v2) — the FINAL agent in PolicyPulse. \
You receive outputs from all upstream agents. Your job: integrate into one answer:

**"How does this policy affect ME — in dollars, per month, everything considered?"**

You do NOT conduct new research. You work EXCLUSIVELY with upstream outputs.

## MODE DETECTION (CHECK FIRST)

Read the Policy Analyst's briefing:
1. `income_effect_exists` → true or false
2. `policy_type` → classification

**If income_effect_exists is TRUE → MODE: BILATERAL**
- Full household balance sheet (inflows AND outflows)
- Net impact can be positive or negative
- Winners and losers framework applies
- Waterfall starts at income change, subtracts costs

**If income_effect_exists is FALSE → MODE: PURE_COST**
- Household balance sheet has ONLY outflows
- Net impact is always negative (a cost to households)
- No "winners" — only "less burdened" vs "more burdened"
- Waterfall starts at $0, subtracts costs
- Frame as: "This policy costs $X/month" NOT "wealth transfer"
- Do NOT call a pure-cost policy "progressive" based on absolute dollars

## PHANTOM CHANNEL DETECTION

After inventorying upstream outputs, scan for fabricated income effects:
IF income_effect_exists is FALSE AND any agent produced income > $0:
→ FLAG as PHANTOM CHANNEL, EXCLUDE from synthesis, document the exclusion.
Exception: Labor displacement risk (job LOSS) is valid — but it's NEGATIVE income, not positive.

## Core Framework: Household Balance Sheet

**BILATERAL mode:** INFLOWS - OUTFLOWS = NET (can be + or -)
**PURE_COST mode:** $0 - OUTFLOWS = TOTAL COST (always negative)

## Key Rules
1. **Net when bilateral, cost when pure.** Do NOT apply net framing to pure-cost policies.
2. Resolve contradictions BEFORE computing — use specialist estimates
3. RANGES not points — low/central/high for every number
4. NEVER double-count
5. Weight costs by ACTUAL budget shares per income tier
6. Account for TAXES on income changes (12%/$30K, 18%/$50K, 22%/$75K, 28%/$120K)
7. **BATCH all code_execute calculations into ONE call.**
8. **Catch phantom channels.** You are the last line of defense against fabricated numbers.
9. **In PURE_COST mode:** Replace "Winners & Losers" with "Burden Distribution" — \
who bears MORE vs LESS of the cost relative to income.
"""

SYNTHESIS_IDENTITY_SHORT = """\
You are the Synthesis Agent (v2). Use code_execute for ALL math. \
Assign answers to `result`. BATCH calculations into ONE call. \
Respect the mode: BILATERAL (income exists) or PURE_COST (no income). \
Produce JSON in ```json code fence."""


def _summarize_housing(housing: HousingReport | None) -> str:
    if not housing:
        return "Housing Agent: MISSING — no housing cost estimates available."
    lines = [f"Housing Agent: RECEIVED (sector={housing.sector})"]
    if housing.affordability_scorecard and housing.affordability_scorecard.sub_markets:
        for sm in housing.affordability_scorecard.sub_markets:
            lines.append(f"  {sm.region_name}: rent change={sm.rent_change}, net={sm.net_affordability_shift}")
    if housing.magnitude_estimates and housing.magnitude_estimates.estimates:
        for e in housing.magnitude_estimates.estimates:
            lines.append(f"  Estimate {e.pathway_id}: {e.central_estimate} ({e.time_horizon})")
    return "\n".join(lines)


def _summarize_consumer(consumer: ConsumerReport | None) -> str:
    if not consumer:
        return "Consumer Agent: MISSING — no price change estimates available."
    lines = [f"Consumer Agent: RECEIVED (sector={consumer.sector})"]
    if consumer.consumer_impact_scorecard and consumer.consumer_impact_scorecard.scorecards:
        for sc in consumer.consumer_impact_scorecard.scorecards[:6]:
            lines.append(f"  {sc.region}|{sc.income_tier}: income={sc.total_income_change}, cost={sc.total_cost_change}, net={sc.net_monthly_change}, verdict={sc.verdict}")
    if consumer.purchasing_power and consumer.purchasing_power.household_profiles:
        for hp in consumer.purchasing_power.household_profiles[:4]:
            lines.append(f"  Profile {hp.name}: net={hp.net_purchasing_power_change}, verdict={hp.verdict}")
    return "\n".join(lines)


def _summarize_analyst(briefing: AnalystBriefing) -> str:
    lines = []
    if briefing.policy_spec:
        lines.append(f"Policy: {briefing.policy_spec.action} — {briefing.policy_spec.value} ({briefing.policy_spec.scope})")
    lines.append(f"Key findings: {len(briefing.key_findings)}")
    for f in briefing.key_findings[:5]:
        lines.append(f"  - {f[:120]}")
    if briefing.sector_exposure:
        lines.append("Sector exposure:")
        for s in briefing.sector_exposure[:5]:
            lines.append(f"  [{s.exposure_level}] {s.sector}")
    return "\n".join(lines)


def phase_1_system_prompt(
    briefing: AnalystBriefing,
    housing: HousingReport | None,
    consumer: ConsumerReport | None,
) -> str:
    schema = ConsistencyAuditOutput.model_json_schema()
    analyst_ctx = _summarize_analyst(briefing)
    housing_ctx = _summarize_housing(housing)
    consumer_ctx = _summarize_consumer(consumer)
    return f"""{SYNTHESIS_IDENTITY}

## YOUR TASK: PHASE 1 — Input Validation + Consistency Audit

Check what you received from each agent and identify contradictions.

### ANALYST BRIEFING:
{analyst_ctx}

### HOUSING AGENT OUTPUT:
{housing_ctx}

### CONSUMER AGENT OUTPUT:
{consumer_ctx}

**Audit these shared variables for contradictions:**
- Income/wage change: Does Consumer's assumed income match Analyst's baseline?
- Rent change: Does Consumer's housing line match Housing's rent estimate?
- Inflation assumption: Did Housing and Consumer use consistent inflation?
- Geographic regions: Did agents analyze the same sub-markets?

**Resolution rule:** Use the SPECIALIST's estimate (Housing for rent, Consumer for prices, \
Analyst for macro). Flag material inconsistencies (>15% difference).

Produce JSON in ```json code fence matching:
{schema}
"""


def phase_2_system_prompt(
    briefing: AnalystBriefing,
    housing: HousingReport | None,
    consumer: ConsumerReport | None,
    phase_1_summary: str | None = None,
) -> str:
    schema = NetImpactOutput.model_json_schema()
    policy_desc = ""
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"
    housing_ctx = _summarize_housing(housing)
    consumer_ctx = _summarize_consumer(consumer)
    audit_ctx = phase_1_summary or "No audit available."
    return f"""Policy: {policy_desc}

## Consistency Audit Results:
{audit_ctx}

## Housing Estimates:
{housing_ctx}

## Consumer Estimates:
{consumer_ctx}

## YOUR TASK: Compute Net Household Impact

Use code_execute for ALL calculations. Compute for this grid:

**Income tiers:** $30K, $50K, $75K, $120K
**Household types:** Single renter, Couple w/ children (renter), Homeowner
**Geographies:** High-cost urban, Moderate suburban, Low-cost rural

For each profile:
1. INCOME SIDE: direct transfer + wage change (after tax) - employment risk - benefits cliff
   Tax rates: 12% at $30K, 18% at $50K, 22% at $75K, 28% at $120K
2. COST SIDE: per-category price changes × budget shares × monthly income
   Budget shares (low income): housing 40%, groceries 11%, transport 16%, restaurants 4%, healthcare 8%
   Budget shares (middle): housing 33%, groceries 8%, transport 17%, restaurants 5%, healthcare 8%
3. NET = income change - cost change

Also produce waterfall chart data for the median household.

Produce JSON matching:
{schema}"""


def phase_3_system_prompt(
    phase_2_summary: str | None = None,
) -> str:
    schema = WinnersLosersOutput.model_json_schema()
    impact_ctx = phase_2_summary or "No impact data."
    return f"""## Household Impact Results:
{impact_ctx}

## YOUR TASK: Winners, Losers, and Confidence Assessment

Use code_execute if you need calculations.

**Identify:**
- Clear WINNERS: net impact strongly positive + HIGH confidence. Who, how much, why.
- Clear LOSERS: net impact negative + MEDIUM+ confidence. Who, how much, why.
- MIXED/UNCERTAIN: net near zero or LOW confidence. What tips them?

**Distributional verdict:** Is the policy progressive, regressive, or geographically uneven?

**Confidence propagation:** Overall confidence = LOWEST confidence of any major component.
Name the weakest link. What would change the conclusion?

Produce JSON matching:
{schema}"""


def phase_4_system_prompt(
    briefing: AnalystBriefing,
    phase_1_summary: str | None = None,
    phase_2_summary: str | None = None,
    phase_3_summary: str | None = None,
) -> str:
    schema = NarrativeOutput.model_json_schema()
    policy_desc = ""
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"
    return f"""{SYNTHESIS_IDENTITY}

## YOUR TASK: PHASE 4 — Narrative Summary + Timeline

Policy: {policy_desc}

## Audit: {phase_1_summary or 'N/A'}
## Impacts: {phase_2_summary or 'N/A'}
## Winners/Losers: {phase_3_summary or 'N/A'}

**Narrative (plain language, no jargon):**
- Executive summary: 3-4 sentences
- Bottom line: ONE sentence — who benefits, who doesn't, by how much
- Key findings: 4 bullets with specific numbers
- Biggest uncertainty

**Timeline (from upstream agents):**
- Month 0-3: What the user experiences immediately
- Month 3-6: Short-term adjustments
- Month 6-12: Medium-term effects
- Year 1-2+: Longer-term settling

Produce JSON matching:
{schema}
"""


def phase_5_system_prompt(
    briefing: AnalystBriefing,
    phase_1_summary: str | None = None,
    phase_2_summary: str | None = None,
    phase_3_summary: str | None = None,
    phase_4_summary: str | None = None,
) -> str:
    schema = SynthesisReport.model_json_schema()
    policy_desc = ""
    if briefing.policy_spec:
        policy_desc = f"{briefing.policy_spec.action}: {briefing.policy_spec.value}"
    return f"""Policy: {policy_desc}

## Audit: {phase_1_summary or 'N/A'}
## Impacts: {phase_2_summary or 'N/A'}
## Winners/Losers: {phase_3_summary or 'N/A'}
## Narrative: {phase_4_summary or 'N/A'}

## YOUR TASK: Produce Final Analytics Payload

Use code_execute for any final calculations.

Assemble the complete SynthesisReport with:
- policy_title, policy_one_liner
- headline_metrics (3-5 key numbers with direction/confidence)
- household_impacts (from Phase 2)
- waterfall chart data
- winners_losers (from Phase 3)
- geographic_impacts
- timeline (from Phase 4)
- consistency_audit (from Phase 1)
- overall_confidence, strongest/weakest components
- narrative (from Phase 4)

Produce JSON matching:
{schema}"""
