"""
Mock premium data services for PolicyPulse.

These FastAPI endpoints serve curated premium data for demo scenarios.
In production, these would be real paid APIs (legal databases, econometric
model providers, research archives). For the hackathon, they return
pre-loaded data — but the L402 payment gate in front of them (via Aperture)
is cryptographically real.

These services run as a standalone FastAPI app on port 8082.
Aperture proxies to them and gates access behind Lightning invoices.

===========================================================================
INTEGRATION GUIDE — What's mocked & where to plug in real sources
===========================================================================

STATUS: 🟡 FULLY MOCKED — Hardcoded demo data for 3 scenarios only.

WHAT'S REAL:
  - The FastAPI server and endpoint structure are production-ready
  - Aperture gates these endpoints with real L402 Lightning invoices
  - The response schema is what the agent pipeline actually consumes

WHAT'S MOCKED:
  - All data (H1B_LEGAL_DATA, H1B_ECON_MODEL, etc.) is hand-curated fiction
  - Only 3 scenarios exist: h1b, student_loan, tariff
  - No external API calls — everything is returned from Python dicts

TO MAKE THIS REAL:
  Option A — Replace mock data with live API calls:
    - /v1/legal/{scenario}  → Call a legal database API (e.g. Westlaw, CourtListener)
    - /v1/econ-models/{scenario} → Call FRED, BLS, or a proprietary econ model
    - /v1/research/{scenario}  → Call Semantic Scholar, SSRN, or arXiv APIs
    Each endpoint would fetch + transform data on-the-fly instead of
    reading from the hardcoded dicts below.

  Option B — Keep this as a caching layer (recommended for demo):
    - Add a DB or Redis cache in front of real API calls
    - Seed it with pre-fetched data for the 3 demo scenarios
    - Fall back to live API for unknown scenarios

  Either way, preserve the current response schema so premium_agent.py
  doesn't need changes. The agent pipeline expects these keys:
    legal:      { source, policy, regulatory_impact }
    econ_models: { source, model, policy, projections }
    research:   { source, papers: [{ title, authors, year, key_finding }] }
===========================================================================
"""

from fastapi import FastAPI

app = FastAPI(title="PolicyPulse Premium Data Services", version="0.1.0")


# ---------------------------------------------------------------------------
# Scenario 1: H1B Visa Policy
# 🟡 MOCK: Hardcoded data. Replace with real legal DB query.
#    Integration point: Call CourtListener/Westlaw API here.
# ---------------------------------------------------------------------------

H1B_LEGAL_DATA = {
    "source": "premium-legal-db",
    "policy": "H1B Visa Reform Act 2026",
    "regulatory_impact": {
        "summary": (
            "The proposed rule modifies the H-1B selection process to prioritize "
            "wage-level-based selection over the current lottery system. Workers "
            "offered Level 3+ wages are selected first, significantly disadvantaging "
            "entry-level hires (Level 1), which account for ~55% of new CS graduates."
        ),
        "effective_date": "2026-10-01",
        "comment_period_ends": "2026-06-15",
        "legal_precedents": [
            {
                "case": "ITServe Alliance v. USCIS (2020)",
                "relevance": "Established limits on USCIS authority to redefine specialty occupation criteria without rulemaking",
            },
            {
                "case": "Nuvision Auto Glass v. USCIS (2023)",
                "relevance": "Court upheld wage-based prioritization as within statutory authority under INA §214(g)(3)",
            },
        ],
        "opt_impact": (
            "OPT STEM extensions remain unaffected. However, the transition from "
            "OPT to H-1B becomes significantly harder for entry-level candidates. "
            "Modeling suggests 30-40% reduction in successful OPT-to-H1B transitions "
            "for Level 1 wage offers."
        ),
    },
}

H1B_ECON_MODEL = {
    "source": "premium-econ-models",
    "model": "Labor Market Equilibrium Model v3.2",
    "policy": "H1B Visa Reform Act 2026",
    "projections": {
        "scenario_base": {
            "description": "Wage-based selection fully implemented",
            "h1b_approval_rate_level1": 0.12,
            "h1b_approval_rate_level3_plus": 0.78,
            "avg_starting_salary_shift": "+8.4%",
            "employer_sponsorship_willingness_drop": "-22%",
            "offshoring_increase": "+15% of affected roles relocated within 18 months",
        },
        "scenario_bull": {
            "description": "Employers raise wages to meet Level 3 threshold",
            "avg_salary_increase_cs_entry": "$12,400",
            "talent_retention_rate": 0.71,
        },
        "scenario_bear": {
            "description": "Employers shift to non-H1B pathways or offshore",
            "domestic_hiring_substitution": 0.35,
            "roles_moved_offshore": 0.45,
            "net_us_job_impact": "-18,000 tech roles in year 1",
        },
    },
}

H1B_RESEARCH = {
    "source": "premium-research",
    "papers": [
        {
            "title": "Wage-Based Immigration Selection and STEM Labor Markets",
            "authors": "Peri, G. & Shih, K.",
            "year": 2025,
            "journal": "Journal of Labor Economics",
            "key_finding": (
                "Wage-based H-1B selection increases average immigrant worker "
                "productivity by 14% but reduces total H-1B utilization by 31%, "
                "with disproportionate impact on younger workers and smaller firms."
            ),
        },
        {
            "title": "OPT-to-H1B Transition Dynamics Under Policy Uncertainty",
            "authors": "Chen, L. & Mukhopadhyay, S.",
            "year": 2026,
            "journal": "Immigration Policy Review (preprint)",
            "key_finding": (
                "Policy uncertainty alone causes 18% of international STEM students "
                "to shift job search to Canada, UK, or Australia before graduation."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Scenario 2: Student Loan Forgiveness
# 🟡 MOCK: Hardcoded data. Replace with real econ/legal APIs.
# ---------------------------------------------------------------------------

LOAN_LEGAL_DATA = {
    "source": "premium-legal-db",
    "policy": "Student Loan Forgiveness Act 2026",
    "regulatory_impact": {
        "summary": (
            "Proposes $20K forgiveness for borrowers earning under $125K, with "
            "an additional $10K for Pell Grant recipients. Estimated to affect "
            "26.5M borrowers. Legal challenges expected under the Major Questions "
            "Doctrine following Biden v. Nebraska (2023) precedent."
        ),
        "legal_precedents": [
            {
                "case": "Biden v. Nebraska (2023)",
                "relevance": "Supreme Court struck down broad forgiveness under HEROES Act. New plan uses Higher Education Act §432(a) authority instead.",
            },
            {
                "case": "Department of Education v. Brown (2023)",
                "relevance": "Standing requirements may block some challenges — individual borrowers lack standing if they benefit from the program.",
            },
        ],
        "implementation_risk": "HIGH — injunction likely within 60 days of announcement based on Missouri v. Biden pattern",
    },
}

LOAN_ECON_MODEL = {
    "source": "premium-econ-models",
    "model": "Consumer Balance Sheet Impact Model v2.1",
    "policy": "Student Loan Forgiveness Act 2026",
    "projections": {
        "borrower_50k_debt": {
            "forgiveness_amount": 20000,
            "remaining_balance": 30000,
            "monthly_payment_reduction": "$112/mo",
            "disposable_income_increase_annual": "$1,344",
            "credit_score_impact": "+25-40 points within 6 months",
            "home_purchase_probability_increase": "+8.2% within 3 years",
        },
        "macro_effects": {
            "total_cost_to_treasury": "$520B over 10 years",
            "gdp_stimulus_estimate": "+0.1-0.2% in year 1",
            "inflation_impact": "Negligible (<0.02 pp CPI increase)",
        },
    },
}

LOAN_RESEARCH = {
    "source": "premium-research",
    "papers": [
        {
            "title": "Student Debt Relief and Labor Market Mobility",
            "authors": "Looney, A. & Yannelis, C.",
            "year": 2025,
            "journal": "Brookings Papers on Economic Activity",
            "key_finding": (
                "Borrowers receiving $20K+ in forgiveness show 23% higher rates "
                "of job switching within 12 months, with moves predominantly toward "
                "higher-paying positions — suggesting debt constrains labor mobility."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Scenario 3: Tariff Policy (Electronics from China)
# 🟡 MOCK: Hardcoded data. Replace with real trade data APIs.
# ---------------------------------------------------------------------------

TARIFF_LEGAL_DATA = {
    "source": "premium-legal-db",
    "policy": "Section 301 Tariff Expansion 2026",
    "regulatory_impact": {
        "summary": (
            "Expands Section 301 tariffs to 45% on consumer electronics (HS codes "
            "8471-8473, 8517, 8528) imported from China, up from current 25%. "
            "Includes semiconductors, PCBs, and finished devices. Small business "
            "exclusion process exists but approval rate is historically <8%."
        ),
        "legal_precedents": [
            {
                "case": "HMTX Industries v. United States (2024)",
                "relevance": "Federal Circuit upheld broad presidential authority under Section 301, limiting judicial review of tariff rates.",
            },
        ],
        "exclusion_process": (
            "Small businesses can apply for product-specific exclusions via USTR. "
            "Average processing time: 6-9 months. Historical approval rate: 7.8%. "
            "Exclusions are retroactive but time-limited (12 months)."
        ),
    },
}

TARIFF_ECON_MODEL = {
    "source": "premium-econ-models",
    "model": "Trade Impact Model — Small Business Edition v4.0",
    "policy": "Section 301 Tariff Expansion 2026",
    "projections": {
        "small_business_electronics_importer": {
            "current_tariff_rate": 0.25,
            "new_tariff_rate": 0.45,
            "cost_increase_per_container": "$18,200",
            "margin_compression": "-12 to -18 percentage points",
            "price_passthrough_to_consumer": "60-75% within 6 months",
            "supply_chain_alternatives": {
                "vietnam": {"lead_time_increase": "8-12 weeks", "cost_vs_china": "+6%"},
                "india": {"lead_time_increase": "12-16 weeks", "cost_vs_china": "+11%"},
                "mexico": {"lead_time_increase": "2-4 weeks", "cost_vs_china": "+3%"},
            },
        },
    },
}

TARIFF_RESEARCH = {
    "source": "premium-research",
    "papers": [
        {
            "title": "Tariff Incidence on Small Importers: Evidence from Section 301",
            "authors": "Amiti, M., Redding, S.J. & Weinstein, D.E.",
            "year": 2025,
            "journal": "American Economic Review",
            "key_finding": (
                "Small importers (<$5M revenue) absorb 2.3x more tariff cost as "
                "margin compression vs. large firms, which pass through 80%+ to "
                "consumers. 14% of small electronics importers exited the market "
                "within 18 months of the 2019 tariff escalation."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Data lookup by scenario + service type
# ---------------------------------------------------------------------------

PREMIUM_DATA = {
    "legal": {
        "h1b": H1B_LEGAL_DATA,
        "student_loan": LOAN_LEGAL_DATA,
        "tariff": TARIFF_LEGAL_DATA,
    },
    "econ_models": {
        "h1b": H1B_ECON_MODEL,
        "student_loan": LOAN_ECON_MODEL,
        "tariff": TARIFF_ECON_MODEL,
    },
    "research": {
        "h1b": H1B_RESEARCH,
        "student_loan": LOAN_RESEARCH,
        "tariff": TARIFF_RESEARCH,
    },
}


# ---------------------------------------------------------------------------
# Endpoints — Aperture sits in front of these
# 🟢 REAL: Endpoint structure is production-ready.
# 🟡 MOCK: Responses come from hardcoded dicts above.
#
# TO INTEGRATE REAL DATA:
#   Replace the dict lookups with async API calls. Example:
#
#   @app.get("/v1/legal/{scenario}")
#   async def get_legal_data(scenario: str):
#       # data = PREMIUM_DATA["legal"].get(scenario)  # ← old mock
#       data = await fetch_from_legal_api(scenario)     # ← new real
#       return data
#
#   Keep the response schema consistent so premium_agent.py works unchanged.
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "premium-data"}


@app.get("/v1/legal/{scenario}")
async def get_legal_data(scenario: str):
    """Regulatory impact assessment and legal precedent analysis."""
    # 🟡 MOCK: Returns hardcoded dict. Replace with real legal DB call.
    data = PREMIUM_DATA["legal"].get(scenario)
    if not data:
        return {"error": f"Unknown scenario: {scenario}", "available": list(PREMIUM_DATA["legal"].keys())}
    return data


@app.get("/v1/econ-models/{scenario}")
async def get_econ_model(scenario: str):
    """Proprietary econometric model projections."""
    # 🟡 MOCK: Returns hardcoded dict. Replace with FRED/BLS/custom model call.
    data = PREMIUM_DATA["econ_models"].get(scenario)
    if not data:
        return {"error": f"Unknown scenario: {scenario}", "available": list(PREMIUM_DATA["econ_models"].keys())}
    return data


@app.get("/v1/research/{scenario}")
async def get_research(scenario: str):
    """Premium research papers and datasets."""
    # 🟡 MOCK: Returns hardcoded dict. Replace with Semantic Scholar/SSRN call.
    data = PREMIUM_DATA["research"].get(scenario)
    if not data:
        return {"error": f"Unknown scenario: {scenario}", "available": list(PREMIUM_DATA["research"].keys())}
    return data
