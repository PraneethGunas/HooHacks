# PolicyPulse — Shared Development Guide

## Project Overview

PolicyPulse is a multi-agent economic policy simulation engine for HooHacks 2026. A user submits a policy proposal (e.g., "Raise the federal minimum wage to $15/hr"), and a pipeline of specialized AI agents retrieves real economic data from government APIs, reasons through sector-specific impacts using structured cognitive frameworks, debates and stress-tests each other's claims, and produces a unified impact report with a Sankey visualization of economic flows.

This is NOT a chatbot that summarizes articles. Each agent calls real government data APIs, performs calculations, and produces structured epistemic objects (claims with evidence, confidence levels, and assumptions) that other agents can formally interrogate.

**Target tracks:** Best AI, Best Data Science, Capital One, Deloitte, SZNS Solutions

---

## Team & Module Ownership

| Person | Module | Directory |
|--------|--------|-----------|
| Rudra | Agent Orchestration (LangGraph state machine + ReAct agents) | `backend/agents/` |
| Praneeth | Backend API (FastAPI + WebSocket) + Pydantic schemas + Lightning/L402 | `backend/`, `backend/lightning/` |
| Pratham | Infra (Docker Compose) + Performance (async parallel execution) + **Stage 0 ADK Classifier** | `docker/`, `backend/` (perf tuning), `backend/agents/classifier.py` |
| Samank | Frontend (React + D3.js Sankey) + SSE live streaming UI | `frontend/` |

---

## Core Agent Architecture (FIXED)

This architecture is locked. All 7 agents, 5 stages, data schemas, and pipeline flow below are the design contract.

### Agent Roster

| Agent | Purpose | Stage |
|-------|---------|-------|
| **Classifier** | Routes user query; extracts policy parameters. **🟢 IMPLEMENTED** — powered by Google ADK (SZNS Solutions sponsor track) | 0 — Preprocessing |
| **Analyst Agent** | Parses policy, gathers baseline data, finds precedents, produces briefing packet | 1 — Research |
| **Labor Agent** | Employment, wages, workforce impacts | 2 — Sector Analysis |
| **Housing Agent** | Housing demand, rents, geographic mobility | 2 — Sector Analysis |
| **Consumer Agent** | Price pass-through, purchasing power, spending | 2 — Sector Analysis |
| **Business Agent** | Firm margins, closures, automation, regional disparities | 2 — Sector Analysis |
| **Debate Agent** | Adversarially challenges weakest claims across all sector reports | 3 — Adversarial Review |
| **Synthesis Agent** | Aggregates revised reports into unified output with Sankey flow data | 4 — Synthesis |

### Pipeline Flow

```
User Input: "Raise minimum wage to $15/hr"
       │
       ▼
┌──────────────┐
│  CLASSIFIER   │  Google ADK — gemini-2.5-flash (cheap/fast)
│  (Stage 0)    │  → ClassifierOutput: task_type, policy_params,
│  🟢 BUILT     │    confidence, cleaned_query
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   ANALYST     │  Parses policy → gathers baseline data → finds research
│   AGENT       │  & precedents → produces structured briefing packet
│  (Stage 1)    │  12-18 tool calls (FRED, BLS, Semantic Scholar, etc.)
└──────┬───────┘
       │  Briefing packet distributed to all 4 sector agents
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  LABOR   │  │ HOUSING  │  │ CONSUMER │  │ BUSINESS │
│  AGENT   │  │  AGENT   │  │  AGENT   │  │  AGENT   │
│(Stage 2) │  │(Stage 2) │  │(Stage 2) │  │(Stage 2) │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │   PARALLEL — ALL FOUR RUN SIMULTANEOUSLY   │
     └──────────────┴──────────────┴──────────────┘
                    │
                    │  4 SectorReports (structured JSON)
                    ▼
            ┌──────────────┐
            │    DEBATE     │  Adversarial critic: targets weakest claims
            │    AGENT      │  3-5 AgentChallenges
            │   (Stage 3)   │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │   REVISION    │  Challenged agents respond:
            │    ROUND      │  CONCEDE / DEFEND / REVISE
            │  (Stage 3b)   │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │  SYNTHESIS    │  Agreement map + Disagreement map
            │    AGENT      │  + Challenge survival record
            │   (Stage 4)   │  + Unified report + Sankey data
            └──────┬───────┘
                   │
                   ▼
            Final Report + Sankey Visualization Data
```

### Sector Agent Feedback Loop

The four sectors create a closed feedback loop:

```
  Labor ←→ Business  (firms respond to labor costs)
  Labor ←→ Consumer  (workers are also consumers)
  Consumer ←→ Housing (spending patterns include rent)
  Business ←→ Consumer (firms pass costs to consumers)
```

---

## Data Schemas (FIXED)

These are the structured types that flow between agents. Agents reason over each other's structured claims, not raw text.

### Stage 0 Output (Classifier)

```
ClassifierOutput                         — from backend/agents/schemas.py
├── task_type: PolicyTaskType enum       — minimum_wage | trade_tariff | immigration
│                                           tax_policy | housing_regulation | healthcare
│                                           education | environmental | other
├── policy_params: dict[str, str]        — {action, value, scope, timeline}
├── confidence: str                      — high | medium | low
├── cleaned_query: str                   — normalised input for downstream agents
└── reasoning: str                       — one-sentence classification explanation
```

### Core Epistemic Objects

```
CausalClaim
├── claim: string              — The assertion
├── cause: string              — What drives this effect
├── effect: string             — What changes
├── mechanism: string          — HOW cause → effect (MANDATORY)
├── confidence: enum           — EMPIRICAL | THEORETICAL | SPECULATIVE
├── evidence: list[string]     — Citations from retrieved data
├── assumptions: list[string]  — What was taken as given
└── sensitivity: string|null   — "If X changes, this conclusion breaks"

SectorReport
├── sector: string
├── direct_effects: list[CausalClaim]
├── second_order_effects: list[CausalClaim]
├── feedback_loops: list[CausalClaim]
├── cross_sector_dependencies: list[string]
├── dissent: string|null
└── tool_calls_made: list[ToolCallRecord]

AgentChallenge
├── target_agent: string
├── target_claim: CausalClaim
├── challenge_type: enum       — assumption_conflict | confidence_inflation
│                                 missing_mechanism | blind_spot
├── counter_evidence: list[string]
└── proposed_revision: string|null

AgentRebuttal
├── original_claim: CausalClaim
├── challenge: AgentChallenge
├── response: enum             — concede | defend | revise
├── revised_claim: CausalClaim|null
└── new_evidence: list[string]

SynthesisReport
├── policy_summary: object
├── agreed_findings: list[AgreedFinding]
├── disagreements: list[Disagreement]
├── challenge_survival: list[ChallengeOutcome]
├── unified_impact: object
├── sankey_data: object
└── metadata: object
```

### Confidence Levels

| Level | Definition | Required Evidence |
|-------|-----------|-------------------|
| **EMPIRICAL** | Backed by data the agent retrieved | Direct data from FRED/BLS/Census OR peer-reviewed studies with citation |
| **THEORETICAL** | Follows from economic models, no direct data | Must cite the model/theory and name assumptions |
| **SPECULATIVE** | Agent's reasoning, flagged as uncertain | Must be explicitly marked. Cannot appear in final report without caveat |

---

## ADK Classifier (Stage 0) — SZNS Solutions Sponsor Track

**🟢 IMPLEMENTED** — `backend/agents/classifier.py`

Uses Google's Agent Development Kit (ADK) with `gemini-2.5-flash` to classify the raw user query and extract structured parameters before the LangGraph pipeline runs. No tool calls — pure reasoning/extraction (~2 seconds).

### Key Files

| File | Purpose |
|------|---------|
| `backend/agents/classifier.py` | ADK Agent + Runner + `run_classifier()` async entry point |
| `backend/agents/schemas.py` | `ClassifierOutput` + `PolicyTaskType` Pydantic models (top of file) |

### How to Wire Into Pipeline

```python
from backend.agents.classifier import run_classifier

# In POST /api/query handler, before invoking LangGraph:
classifier_out = await run_classifier(user_query)
# classifier_out.task_type      → route to relevant sector emphasis
# classifier_out.cleaned_query  → use as canonical query for AnalystState
# classifier_out.policy_params  → available upfront for all downstream agents
```

### Graceful Degradation

If `google-adk` is not installed or the API call fails, `run_classifier()` returns a minimal `ClassifierOutput` with `task_type="other"` and the original query unchanged — the pipeline never hard-crashes on Stage 0.

### Classifier Config

```env
GEMINI_API_KEY=AIza...                   # Required for ADK
CLASSIFIER_MODEL_NAME=gemini-2.5-flash   # Override in .env if needed
```

### Testing

```bash
python3 test_classifier.py   # smoke test in project root
```

---

## Agent Tools

### Analyst Agent Tools

| Tool | Underlying API | Purpose |
|------|---------------|---------|
| `fred_search` | FRED API | Discover relevant economic data series |
| `fred_get_series` | FRED API | Pull numerical time series data |
| `bls_get_data` | BLS API v2 | Employment/wage/price breakdowns |
| `search_academic_papers` | Semantic Scholar | Peer-reviewed economics research |
| `search_openalex` | OpenAlex API | Broader academic search |
| `search_cbo_reports` | Tavily (scoped to cbo.gov) | CBO official policy scoring |
| `fetch_document_text` | HTTP GET + BeautifulSoup | Read full text of a report/paper URL |
| `web_search_news` | Tavily API | Recent news, political context |

### Sector Agent Tools

| Agent | Tools |
|-------|-------|
| **Labor** | `fred_get_series`, `bls_get_data`, `search_academic_papers`, `fetch_document_text`, `calculate_elasticity`, `run_scenario_analysis` |
| **Housing** | `fred_get_series`, `census_query`, `search_academic_papers`, `calculate_elasticity`, `run_scenario_analysis` |
| **Consumer** | `fred_get_series`, `bls_get_data`, `bea_get_data`, `search_academic_papers`, `calculate_elasticity`, `run_scenario_analysis` |
| **Business** | `fred_get_series`, `census_query`, `bls_get_data`, `search_academic_papers`, `run_scenario_analysis` |

### Computation Tools (Shared by Sector Agents)

| Tool | Purpose |
|------|---------|
| `calculate_elasticity` | Log-log regression for elasticity between two variables. Returns estimate, CI, R², p-value |
| `run_scenario_analysis` | Given base value, shock %, and elasticity with uncertainty → base/bull/bear projections |

### Debate Agent Tools

`search_academic_papers`, `fetch_document_text`, `calculate_elasticity`

### Synthesis Agent Tools

None — works purely on agent outputs.

---

## Lightning / L402 Premium Data Layer

**✅ Lightning stack is fully operational on regtest.** L402 end-to-end flow confirmed working.

The L402 protocol enables AI agents to autonomously pay for premium data using Bitcoin Lightning micropayments. When free government APIs (FRED, BLS, etc.) provide baseline data, the Premium Data Agent can access gated sources — paid legal databases, proprietary economic models, premium research — by paying fractions of a cent per request.

**This is a core differentiator for the SZNS Solutions and Sixgen/CCI sponsor tracks.** It demonstrates real cryptographic auth (macaroons + invoice verification) and autonomous agent payments.

### How It Works

```
Agent needs premium data
       │
       ▼
┌──────────────────┐
│  HTTP GET         │  Request premium endpoint via Aperture
│  aperture:8081    │
└──────┬───────────┘
       │  HTTP 402 Payment Required
       │  WWW-Authenticate: L402 macaroon="...", invoice="lnbc..."
       ▼
┌──────────────────┐
│  lnget (auto)     │  Pay Lightning invoice from buyer wallet
│  litd-buyer node  │  Amount: 10-25 sats
└──────┬───────────┘
       │  Payment preimage returned
       ▼
┌──────────────────┐
│  Retry request    │  Authorization: L402 macaroon:preimage
│  with macaroon    │
└──────┬───────────┘
       │  200 OK — premium data returned
       ▼
  Agent continues with enriched data
```

### Lightning Architecture

```
bitcoind (regtest) → litd-buyer (agent wallet, Lightning Terminal)
                   → litd-seller (Aperture's node, Lightning Terminal)
                                    ↓
                               aperture (L402 proxy, port 8081)
                                    ↓
                               premium-data (FastAPI, port 8082)
```

We use **lightning-agent-tools** from Lightning Labs end-to-end. No custom Lightning code.

| Component | Tool / Service | Role |
|-----------|---------------|------|
| **litd** | `lightninglabs/lightning-terminal:v0.15.0-alpha` | Lightning Terminal — lnd + loop + pool + tapd bundled. Two nodes: buyer (agent wallet) and seller (Aperture's node) |
| **Aperture** | Built from source (arm64) | L402 reverse proxy — gates premium endpoints behind invoices, mints/verifies macaroons |
| **lnget** | Built from source in backend container | L402 client — auto-handles 402 detection, invoice payment, token caching, spending limits |
| **bitcoind** | `lncm/bitcoind:v27.0` | Regtest Bitcoin node — mine own blocks, zero external dependencies |

### Lightning Key Files

| File | Purpose |
|------|---------|
| `docker/docker-compose.lightning.yml` | Full Lightning stack compose file |
| `docker/litd/buyer-lit.conf` | litd config for buyer (regtest, bitcoind backend) |
| `docker/litd/seller-lit.conf` | litd config for seller (regtest, bitcoind backend) |
| `docker/Dockerfile.aperture` | Builds Aperture from source via `git clone` + `go build` (arm64) |
| `docker/Dockerfile.bootstrap` | Bootstrap image: lncm/bitcoind + lncli from litd image + jq |
| `docker/Dockerfile.backend` | Backend: Python + Go + lnget (cloned & built from source) |
| `docker/Dockerfile.premium-data` | Lightweight FastAPI container for mock premium endpoints |
| `docker/aperture/aperture.yaml` | Aperture L402 proxy config — routes to premium-data, prices in sats |
| `scripts/bootstrap-regtest.sh` | One-shot: funds wallet, opens channel, bakes macaroons, generates lnget config |
| `backend/lightning/l402_client.py` | Python wrapper around `lnget` subprocess calls |
| `backend/lightning/premium_agent.py` | Premium Data Agent — orchestrates L402 fetches, emits SSE events |
| `backend/lightning/mock_services/premium_data.py` | 3 mock premium endpoints with curated data for 3 demo scenarios |
| `scripts/test_l402_flow.py` | End-to-end test suite for the L402 flow |

### Mock Premium Data Services

| Service | What It Returns | Gated By |
|---------|----------------|----------|
| `premium-legal-db` | Regulatory impact assessments, legal precedent analysis | L402 (10 sats) |
| `premium-econ-models` | Proprietary econometric model projections | L402 (25 sats) |
| `premium-research` | Full-text premium research papers / datasets | L402 (15 sats) |

These are real FastAPI services behind Aperture — the data is curated/pre-loaded for demo scenarios, but the L402 payment flow is cryptographically real.

### Integration with Agent Pipeline

The Premium Data Agent sits between Stage 1 (Analyst) and Stage 2 (Sector Agents):

```
Stage 1: Analyst (free APIs: FRED, BLS, etc.)
       │
       ▼
  Premium Data Agent (L402 payments for gated sources)
       │
       ▼
Stage 2: Sector Agents (receive enriched briefing packet)
```

### SSE Events for Lightning Payments

The frontend shows Lightning payments happening in real time:

```json
{
  "type": "lightning_payment",
  "data": {
    "service": "premium-legal-db",
    "invoice_amount_sats": 10,
    "status": "paying" | "paid" | "failed",
    "macaroon_received": true,
    "payment_hash": "abc123...",
    "duration_ms": 450
  }
}
```

### Lightning Common Issues & Fixes

**arm64 / Apple Silicon:**
- `lightninglabs/lightning-terminal:v0.15.0-alpha` pulls fine on arm64
- `lncm/bitcoind:v27.0` has confirmed arm64 support
- **DO NOT use `lncm/lnd`** — tops out at v0.13.4, way too old. Use litd image for lncli instead
- Both Aperture and lnget are cloned and built from source (`git clone` + `go build`) — both have `replace` directives in go.mod that break `go install`

**litd (Lightning Terminal):**
- Config at `/root/.lit/lit.conf` (NOT `litd.conf`)
- Use top-level `network=regtest` (NOT `lnd.bitcoin.regtest=true` — causes conflicts)
- `autopilot.disable=true` required for regtest
- `lnd-mode=integrated` means litd manages lnd internally
- `lnd.noseedbackup=true` enables auto wallet creation

**Aperture:**
- Config field names have NO hyphens: `lndhost`, `tlspath`, `macdir` (NOT `lnd-host`, etc.)
- `insecure: true` disables TLS for internal Docker networking

**lnget:**
- Config field names: `tls_cert`, `macaroon`, `network` (NOT `tls_cert_path`, etc.)
- Requires lnd v0.19.0+ (litd v0.15.0-alpha provides v0.19.1-beta)
- Volume mount must NOT be read-only (`:ro`) — lnget writes logs and token cache

**Bootstrap:**
- Runs as one-shot container after both litd nodes are healthy
- Generates lnget config at `/lnget-config/config.yaml` → mounted into backend at `/root/.lnget/`
- Bakes `invoice.macaroon` for Aperture (least privilege)

### Lightning Testing

```bash
# Start the Lightning stack
docker compose -f docker/docker-compose.lightning.yml up --build

# Wait for "Bootstrap complete!", then:

# 1. Direct premium data (bypass L402)
curl http://localhost:8082/v1/legal/h1b

# 2. Via Aperture (should get 402)
curl -v http://localhost:8081/v1/legal/h1b

# 3. Full L402 flow (from inside backend container)
docker compose -f docker/docker-compose.lightning.yml exec backend lnget --max-cost=500 -k http://aperture:8081/v1/legal/h1b

# 4. Python test suite
python scripts/test_l402_flow.py
```

### What's Mocked vs Real (Quick Reference)

| Component | Status | File | Owner |
|-----------|--------|------|-------|
| L402 payment flow (lnget) | 🟢 REAL | `l402_client.py` | Praneeth |
| Lightning nodes (litd) | 🟢 REAL (regtest) | `docker-compose.lightning.yml` | Praneeth/Pratham |
| Aperture L402 proxy | 🟢 REAL | `aperture.yaml` | Praneeth |
| Bootstrap (wallet, channel) | 🟢 REAL (regtest) | `bootstrap-regtest.sh` | Praneeth |
| Premium data content | 🟡 MOCK (3 scenarios) | `mock_services/premium_data.py` | Replace with real APIs |
| Scenario detection | 🟡 MOCK (keyword match) | `premium_agent.py` | Rudra (LLM classify) |
| API routes | 🔴 TODO | `main.py` | Rudra |
| LLM API keys | 🔴 TODO (empty) | `config.py` | Rudra |
| SSE streaming | 🟢 READY (events defined) | `premium_agent.py` | Samank (consume) |
| Aperture prices | 🟡 DEMO VALUES | `aperture.yaml` | Praneeth |

Each file has detailed `INTEGRATION GUIDE` comments explaining what's mocked, what's real, and how to replace mocks with real implementations.

### What NOT to Change (Lightning)

- Don't add gRPC/protobuf Python dependencies — we use lnget exclusively
- The premium data content in `mock_services/premium_data.py` is curated for 3 demo scenarios (h1b, student_loan, tariff) — keep it deep and specific
- Don't remove `insecure: true` from aperture.yaml — needed for internal Docker networking

### Lightning References

- [lightning-agent-tools](https://github.com/lightninglabs/lightning-agent-tools) — Lightning Labs toolkit
- [L402 for Agents blog post](https://lightning.engineering/posts/2026-03-11-L402-for-agents/)

---

## External Data APIs

| API | Key Required | Cost | Rate Limit |
|-----|-------------|------|------------|
| **FRED** (Federal Reserve) | Yes (free) | $0 | 120 req/min |
| **BLS** (Bureau of Labor Statistics) | Recommended (free) | $0 | 500/day |
| **Census Bureau** | Optional (free) | $0 | 500/day |
| **BEA** (Bureau of Economic Analysis) | Yes (free) | $0 | 1000/day |
| **Semantic Scholar** | Optional (free) | $0 | 100/5min |
| **OpenAlex** | No | $0 | 10/sec |
| **Tavily** | Yes | Free tier: 1000/mo | 1000/month |

### Required API Keys

```env
FRED_API_KEY=xxx           # fred.stlouisfed.org
BLS_API_KEY=xxx            # bls.gov/developers
TAVILY_API_KEY=tvly-xxx    # tavily.com
ANTHROPIC_API_KEY=xxx      # or OPENAI_API_KEY / GOOGLE_API_KEY for LLM
```

Total data API cost: **$0**. LLM costs are the only expense.

### LLM Provider Setup

`.env.example` supports all three LLM providers. Set `LLM_PROVIDER` to switch:

```env
LLM_PROVIDER=openai        # "openai" | "anthropic" | "google"

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Default models (override as needed)
OPENAI_MODEL=gpt-4o
OPENAI_CLASSIFIER_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-opus-4-6
ANTHROPIC_CLASSIFIER_MODEL=claude-haiku-4-5-20251001
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_CLASSIFIER_MODEL=gemini-2.5-flash
```

Only the key for the selected provider needs to be filled in. The backend reads `LLM_PROVIDER` to route all LLM calls — no code changes needed to switch models.

---

## Tech Decisions

**Fixed:**
- **Stage 0 Classifier:** Google ADK (`google-adk`) — SZNS Solutions sponsor track
- **Agent Orchestration:** LangGraph (state machine + ReAct agents via `create_react_agent`)
- **Agent Communication:** Pydantic models (CausalClaim, SectorReport, AgentChallenge, etc.)
- **Sector Agent Execution:** Async parallel (all 4 run simultaneously)

**Flexible (adapt as needed):**
- **Backend:** FastAPI (Python 3.11+), async everywhere
- **Frontend:** React + D3.js for Sankey visualization (framework TBD)
- **Streaming:** SSE or WebSocket for real-time agent reasoning display
- **LLM:** Gemini / GPT-4o / Claude for agent reasoning + cheap model for Classifier
- **Infrastructure:** Docker Compose
- **Database:** TBD — may not need one if all data comes from live APIs

---

## Frontend Integration Events

The backend streams intermediate results so the user sees agents working in real time:

| Event | Data | UI Element |
|-------|------|-----------|
| `classifier_complete` | Task type + extracted params | Parsed policy card |
| `analyst_tool_call` | Tool name + query | "Searching FRED for minimum wage data..." |
| `analyst_complete` | Briefing packet summary | Briefing card with key stats |
| `sector_agent_started` | Agent name | 4 agent cards appear |
| `sector_agent_tool_call` | Agent + tool + query | Per-agent live feed |
| `sector_agent_complete` | SectorReport summary | Agent card fills with findings |
| `lightning_payment` | Service + amount + status | Lightning bolt animation + sat counter |
| `debate_challenge` | AgentChallenge | Challenge cards with red highlighting |
| `revision_complete` | AgentRebuttal | Concede/defend/revise per challenge |
| `synthesis_complete` | SynthesisReport + Sankey data | Final report + animated Sankey |

---

## Execution Targets

| Metric | Target |
|--------|--------|
| Total pipeline runtime | 30-60 seconds |
| Stage 0 (Classifier, ADK) | ~2 seconds |
| Stage 1 (Analyst) | 10-15 seconds |
| Stage 2 (Sector Agents, parallel) | 8-12 seconds each |
| Stage 3 (Debate + Revision) | 8-12 seconds |
| Stage 4 (Synthesis) | 5-8 seconds |
| Total API calls per run | 40-70 |
| Total LLM calls per run | 15-25 |

---

## Key Design Principles

1. **Structured epistemic objects, not raw text.** Agents pass CausalClaims with confidence levels and assumptions — enabling formal interrogation.
2. **Mandatory mechanism specification.** Agents cannot say "X leads to Y" without explaining HOW.
3. **API-first data access.** Live government APIs (FRED, BLS, Census) for structured data.
4. **Adversarial quality control.** Debate Agent stress-tests all claims. Surviving claims are marked as such.
5. **Full audit trail.** Every tool call, claim, challenge, and rebuttal is logged and traceable.

---

## Development Conventions

- **Python:** Type hints everywhere. Pydantic models for all inter-agent data. `async def` for I/O.
- **Frontend:** TypeScript strict mode. Components get their own file.
- **Environment:** All secrets in `.env` (never committed). Use `.env.example` as template.
- **Commits:** Short descriptive messages. Prefix with module: `agents:`, `backend:`, `frontend:`, `infra:`, `tools:`.
- **Branches:** Feature branches, merge to `main` when stable.

---

## Quick Start

```bash
cp .env.example .env
# Fill in: FRED_API_KEY, BLS_API_KEY, TAVILY_API_KEY, LLM API key

# Docker (full stack including Lightning)
docker compose -f docker/docker-compose.lightning.yml up --build

# Backend only (dev)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend only (dev)
cd frontend && npm install && npm run dev
```

---

## Notes

- Project structure directories are suggested — adapt as needed, but keep module boundaries clean
- API contract between frontend and backend is TBD — will be defined as implementation progresses
- Lightning/L402 is a core differentiator — at least one real payment flow must work for the demo
- When in doubt, prioritize UI polish over backend completeness — judges experience the frontend

---

*HooHacks 2026 — Team: Praneeth Gunasekaran | Rudra Desai | Pratham Jangra | Samank Gupta*
