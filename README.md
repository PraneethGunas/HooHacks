<p align="center">
  <h1 align="center">PolicyPulse</h1>
  <p align="center">
    <strong>AI-powered personal policy impact analysis — backed by real government data and autonomous Lightning micropayments</strong>
  </p>
  <p align="center">
    <a href="#architecture">Architecture</a> &nbsp;·&nbsp;
    <a href="#lightning--l402">Lightning / L402</a> &nbsp;·&nbsp;
    <a href="#quick-start">Quick Start</a> &nbsp;·&nbsp;
    <a href="#evaluation-framework">Evals</a> &nbsp;·&nbsp;
    <a href="#team">Team</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/HooHacks-2026-blue?style=flat-square" alt="HooHacks 2026" />
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js" />
    <img src="https://img.shields.io/badge/LangGraph-Agents-orange?style=flat-square" alt="LangGraph" />
    <img src="https://img.shields.io/badge/Lightning-L402-yellow?style=flat-square&logo=bitcoin&logoColor=white" alt="Lightning" />
    <img src="https://img.shields.io/badge/Google%20ADK-Gemini-4285F4?style=flat-square&logo=google&logoColor=white" alt="Google ADK" />
  </p>
</p>

---

## Overview

PolicyPulse is a multi-agent AI system that transforms vague policy questions into personalized, evidence-based impact analyses. Users ask how a new tariff, visa rule, or student loan plan affects *them* — and a pipeline of 7 specialized AI agents retrieves live government data, reasons through sector-specific impacts with structured epistemic frameworks, and delivers a unified report with interactive Sankey visualizations.

**What makes this different:** AI agents that autonomously pay for premium data using Bitcoin Lightning micropayments via the L402 protocol. When free public sources aren't sufficient, the agent's pre-funded Lightning wallet pays fractions of a cent to access gated databases — and the user watches it happen in real time.

> Built in 24 hours at **HooHacks 2026**, University of Virginia.
> Targeting: **Best AI** · **Best Data Science** · **Capital One** · **Deloitte** · **SZNS Solutions**

### Example Queries

| Scenario | Question |
|----------|----------|
| Immigration | *"How will the new H1B visa policy affect international students graduating in 2026?"* |
| Student Debt | *"How will the proposed student loan forgiveness plan affect a 2026 graduate with $50K in debt?"* |
| Trade | *"How will the new tariff policy affect a small business importing electronics from China?"* |

---

## Architecture

PolicyPulse runs a 4-stage pipeline of 7 agents. Each agent produces structured **epistemic objects** — causal claims with mechanisms, confidence tiers (Empirical / Theoretical / Speculative), evidence citations, and named assumptions — that downstream agents can formally interrogate.

```
User Input
  │
  ▼
┌────────────────────────────────────────────────────────────────────┐
│  STAGE 0 · CLASSIFICATION                                         │
│  Google ADK (gemini-2.5-flash) → policy type, parameters, routing │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│  STAGE 1 · RESEARCH                                                │
│  Analyst Agent — 12-18 tool calls across FRED, BLS, Semantic       │
│  Scholar, CBO, OpenAlex, Tavily → structured briefing packet       │
│                                                                    │
│  Premium Data Agent — L402 Lightning micropayments for gated       │
│  legal, econometric, and research databases                        │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│  STAGE 2 · SECTOR ANALYSIS  (parallel execution)                   │
│                                                                    │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Labor  │  │ Housing │  │ Consumer │  │ Business │            │
│  │  Agent  │  │  Agent  │  │  Agent   │  │  Agent   │            │
│  └─────────┘  └─────────┘  └──────────┘  └──────────┘            │
│                                                                    │
│  Cross-sector feedback loop:                                       │
│  Labor ↔ Business · Labor ↔ Consumer · Consumer ↔ Housing         │
│  Business ↔ Consumer                                               │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│  STAGE 3 · SYNTHESIS                                               │
│  Agreement/disagreement mapping · confidence-tiered claims ·       │
│  Sankey flow data · income-tier impact matrix · distributional     │
│  verdict (BILATERAL vs PURE_COST mode detection)                   │
└────────────────────────────────────────────────────────────────────┘
                           ▼
                  Final Report + Sankey Visualization
```

### Confidence Framework

Every claim in the system carries an explicit confidence tier:

| Tier | Definition | Evidence Required |
|------|-----------|-------------------|
| **Empirical** | Backed by retrieved data | Direct data from FRED/BLS/Census or peer-reviewed studies with citation |
| **Theoretical** | Follows from economic models | Must cite the model/theory and name assumptions |
| **Speculative** | Agent reasoning, flagged as uncertain | Explicitly marked; cannot appear in final report without caveat |

---

## Lightning / L402

PolicyPulse uses the [L402 protocol](https://lightning.engineering/posts/2026-03-11-L402-for-agents/) to enable AI agents to autonomously pay for premium data. The entire payment flow is **cryptographically real** on Bitcoin regtest — LND nodes, Aperture reverse proxy, and [lnget](https://github.com/lightninglabs/lightning-agent-tools) from Lightning Labs.

```
┌─────────────┐    HTTP 402 + invoice     ┌──────────────┐
│  Agent       │ ◄──────────────────────── │   Aperture   │
│  (lnget)     │                           │  L402 Proxy  │
│              │ ── Lightning payment ───► │              │
│              │                           │              │
│              │ ── macaroon:preimage ───► │              │ ──► Premium Data API
│              │ ◄── 200 OK + data ─────── │              │
└─────────────┘                           └──────────────┘
```

| Premium Service | Data Returned | Invoice |
|-----------------|--------------|---------|
| Legal DB | Regulatory impact assessments, legal precedent analysis | 10 sats |
| Econ Models | Proprietary econometric model projections | 25 sats |
| Research | Full-text premium research papers and datasets | 15 sats |

The frontend shows each payment in real time — invoice amount, payment status, macaroon receipt, and the data flowing into the agent's analysis.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16 · React 19 · Tailwind CSS 4 · D3.js Sankey diagrams |
| **Backend** | FastAPI · Python 3.11+ · Server-Sent Events (SSE) |
| **Agent Framework** | LangGraph state machine · ReAct agents · Pydantic structured outputs |
| **Stage 0 Classifier** | Google Agent Development Kit (ADK) · gemini-2.5-flash |
| **Data Sources** | FRED · BLS · Census Bureau · BEA · Semantic Scholar · OpenAlex · Tavily |
| **Lightning** | LND via litd v0.15.0-alpha · Aperture L402 proxy · lnget client |
| **Evaluation** | ADK eval framework · 9 evalsets · rubric + trajectory + hallucination scoring |
| **Infrastructure** | Docker Compose · bitcoind (regtest) · litd buyer/seller nodes |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for full stack / Lightning)

### 1. Environment Setup

```bash
cp .env.example .env
```

All government data APIs are free to register:

| Variable | Registration |
|----------|-------------|
| `FRED_API_KEY` | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `BLS_API_KEY` | [bls.gov/developers](https://www.bls.gov/developers/) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) |
| `LLM_PROVIDER` | Set to `openai`, `anthropic`, or `google` — then fill in the corresponding API key |

### 2. Development (Backend + Frontend)

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### 3. Full Stack with Lightning

```bash
docker compose -f docker/docker-compose.lightning.yml up --build
```

Wait for `Bootstrap complete!` in the logs — the bootstrap container funds the agent wallet, opens a payment channel between buyer and seller LND nodes, and generates the lnget configuration.

### 4. Verify Lightning

```bash
# Direct premium data (bypass L402)
curl http://localhost:8082/v1/legal/h1b

# Via Aperture (returns HTTP 402)
curl -v http://localhost:8081/v1/legal/h1b

# Full L402 flow (from backend container)
docker compose -f docker/docker-compose.lightning.yml exec backend \
  lnget --max-cost=500 -k http://aperture:8081/v1/legal/h1b
```

---

## Project Structure

```
policypulse/
├── backend/
│   ├── agents/                     # LangGraph agent definitions
│   │   ├── classifier.py           #   Stage 0 — Google ADK classifier
│   │   ├── prompts.py              #   Analyst agent system prompts (v2)
│   │   ├── schemas.py              #   Pydantic models: CausalClaim, SectorReport, etc.
│   │   ├── consumer/               #   Consumer & Prices sector agent
│   │   ├── housing/                #   Housing sector agent
│   │   └── synthesis/              #   Synthesis agent (cross-sector aggregation)
│   ├── pipeline/                   # Pipeline orchestration
│   │   ├── orchestrator.py         #   Entry point — wires all stages together
│   │   ├── sector.py               #   Parallel sector agent execution
│   │   ├── synthesis.py            #   Synthesis + frontend schema conversion
│   │   └── llm.py                  #   LLM provider abstraction layer
│   ├── lightning/                  # L402 Lightning integration
│   │   ├── l402_client.py          #   Python wrapper around lnget subprocess
│   │   ├── premium_agent.py        #   Premium Data Agent + SSE event emitter
│   │   └── mock_services/          #   3 curated premium data endpoints
│   ├── tools/                      # Agent tool implementations (FRED, BLS, etc.)
│   ├── main.py                     # FastAPI application + SSE streaming
│   └── config.py                   # Settings and API key management
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── QueryInput.tsx      #   Policy question input with context fields
│       │   ├── AgentFeed.tsx       #   Real-time agent activity stream
│       │   ├── ResultsPanel.tsx    #   Impact report with confidence tiers
│       │   ├── SankeyDiagram.tsx   #   D3.js economic flow visualization
│       │   └── LightningRow.tsx    #   Lightning payment animation
│       ├── hooks/
│       │   └── usePipeline.ts      #   SSE connection + pipeline state management
│       └── types/
│           └── pipeline.ts         #   TypeScript types mirroring backend schemas
│
├── evals/                          # ADK evaluation framework
│   ├── evalsets/                   #   9 test scenarios (3 agents × 3 policy types)
│   ├── configs/                    #   Rubric + trajectory scoring criteria
│   ├── wrappers/                   #   ADK-compatible agent wrappers
│   ├── run_all_evals.py            #   Main eval runner (live agent calls)
│   ├── eval_tool_trajectory.py     #   Tool call pattern evaluator
│   ├── eval_from_docs.py           #   Offline output quality evaluator
│   └── eval_logger.py              #   Timestamped results logger + index
│
├── docker/
│   ├── docker-compose.yml          #   Core services
│   ├── docker-compose.lightning.yml#   Full stack including Lightning
│   ├── Dockerfile.backend          #   Python + Go (lnget built from source)
│   ├── Dockerfile.aperture         #   L402 proxy (built from source, arm64)
│   ├── Dockerfile.bootstrap        #   Regtest wallet + channel setup
│   ├── Dockerfile.premium-data     #   Mock premium API container
│   ├── aperture/                   #   Aperture L402 proxy configuration
│   └── litd/                       #   LND node configs (buyer + seller)
│
├── scripts/
│   ├── bootstrap-regtest.sh        #   One-shot: fund wallet, open channel, gen config
│   └── test_l402_flow.py           #   End-to-end L402 integration test
│
├── tests/                          #   Agent + tool unit tests
└── .env.example                    #   Environment variable template
```

---

## Evaluation Framework

PolicyPulse includes a comprehensive evaluation harness built on Google ADK patterns. It validates agent behavior across 3 policy types (**Labor Cost**, **Regulatory Cost**, **Transfer**) for 3 agents (**Analyst**, **Consumer**, **Housing**) — 9 evalsets total.

Each evaluation scores three dimensions:

| Dimension | What It Measures |
|-----------|-----------------|
| **Rubric Scoring** | Structural correctness — policy classification, income_effect flag, transmission channels, confidence levels, downstream directives |
| **Tool Trajectory** | Behavioral correctness — phase ordering, call diversity, error recovery, tool appropriateness for the policy type |
| **Hallucination Detection** | Absence of fabricated claims — e.g., no phantom wage effects for cost-only policies like tariffs |

```bash
python evals/run_all_evals.py                 # Run all 9 evalsets (live)
python evals/run_all_evals.py --agent=analyst  # Single agent
python evals/eval_from_docs.py                 # Offline quality check
python evals/eval_tool_trajectory.py           # Tool pattern analysis
```

Results are logged as timestamped JSON to `evals/results/` with an index for tracking score trends across runs.

---

## Real-Time Streaming

The backend streams every pipeline step to the frontend via Server-Sent Events, so users watch the analysis unfold live:

| SSE Event | Frontend Behavior |
|-----------|-------------------|
| `classifier_complete` | Parsed policy card appears with extracted type and parameters |
| `analyst_tool_call` | Activity feed shows "Searching FRED for minimum wage data..." |
| `sector_agent_started` | Four agent cards animate in simultaneously |
| `sector_agent_tool_call` | Per-agent live tool call feed |
| `lightning_payment` | Lightning bolt animation with satoshi counter and payment status |
| `synthesis_complete` | Full impact report renders with animated Sankey diagram |

---

## Team

<table>
  <tr>
    <td align="center"><strong>Praneeth Gunasekaran</strong><br/>Backend API · Lightning/L402<br/>Pipeline Orchestration</td>
    <td align="center"><strong>Rudra Desai</strong><br/>Agent Architecture · LangGraph<br/>Prompt Engineering · Evals</td>
    <td align="center"><strong>Pratham Jangra</strong><br/>Infrastructure · Performance<br/>Docker · ADK Classifier</td>
    <td align="center"><strong>Samank Gupta</strong><br/>Frontend · D3.js Sankey<br/>UI/UX · Demo Polish</td>
  </tr>
</table>

---

<p align="center">
  Built with caffeine and conviction at <strong>HooHacks 2026</strong>, University of Virginia.
</p>
