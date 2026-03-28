# 🐟 Polysim — Prediction Market in Silico

> "14 million scenarios, only one you win."
> Upload a policy → watch a simulated population react in real time.

---

## ELI5: What This Does

You paste/upload a policy document (like "raise GST to 10%"). Polysim:

1. **Reads it** → GPT-4o extracts the key provisions ("GST increase", "CPF change", etc.)
2. **Spawns 40 AI agents** → each represents a real demographic slice of Singapore (Chinese nurse in Ang Mo Kio, aged 35; Malay retiree in Jurong, aged 68; etc.)
3. **Each agent reads the policy and reacts** → "Wah this one help me lah" or "This one don't benefit me at all"
4. **Social contagion** → agents influence each other (same race/neighborhood/age = stronger ties), sentiment ripples across communities over 3 rounds
5. **Dashboard shows results** → Singapore map lights up green/amber/red per constituency, agent quotes, vote prediction, demographic breakdown

It's like running an election before the election happens.

---

## Architecture (How The Pieces Fit)

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)               │
│  localhost:3000                                          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Policy   │→ │ Map View │  │ Side     │  │ Lever   │ │
│  │ Upload   │  │ (Leaflet)│  │ Panel    │  │ Controls│ │
│  └────┬─────┘  └────▲─────┘  └────▲─────┘  └────┬────┘ │
│       │              │             │              │      │
│       ▼              └─────────────┘              │      │
│  useSimulation.js (WebSocket client)              │      │
└───────┬───────────────────────────────────────────┼──────┘
        │ HTTP POST /api/upload                     │ POST /api/adjust
        │ WS /ws/simulate/{id}                      │
        ▼                                           ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (Python FastAPI)               │
│  localhost:8000                                          │
│                                                          │
│  ┌──────────────┐   ┌───────────────┐   ┌─────────────┐ │
│  │ policy_      │   │ agent_        │   │ contagion   │ │
│  │ parser.py    │   │ engine.py     │   │ _v2.py      │ │
│  │ (GPT-4o)     │   │ (40× GPT-4o) │   │ (O(n) fast) │ │
│  └──────┬───────┘   └──────┬────────┘   └──────┬──────┘ │
│         │                  │                    │        │
│         ▼                  ▼                    ▼        │
│  ┌──────────────┐   ┌───────────────┐   ┌─────────────┐ │
│  │ demographics │   │ backtest.py   │   │ real_data   │ │
│  │ .py          │   │ (vs GE2020)   │   │ .py         │ │
│  └──────────────┘   └───────────────┘   └─────────────┘ │
│                                                          │
│  ┌──────────────┐   ┌───────────────┐                    │
│  │ scraper.py   │   │ levers.py     │                    │
│  │ (TinyFish)   │   │ (policy       │                    │
│  │              │   │  adjustments) │                    │
│  └──────────────┘   └───────────────┘                    │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│  data/ (local CSVs)  │    │  External APIs               │
│  • Census 2020       │    │  • OpenAI GPT-4o             │
│  • GE2020 results    │    │  • TinyFish (web scraping)   │
│  • GRC boundaries    │    │  • 🔌 MiroFish (plug in here)│
│  • Income data       │    │                              │
└──────────────────────┘    └──────────────────────────────┘
```

---

## File Guide (What's What)

```
polisim-repo/
├── .env                    ← YOUR API KEYS (never commit this)
├── .env.example            ← Template for .env
├── demo.sh                 ← One-command "start everything"
│
├── backend/
│   ├── main.py             ← FastAPI server, all routes, WebSocket handler
│   ├── policy_parser.py    ← PDF/text → structured provisions (GPT-4o)
│   ├── agent_engine.py     ← Spawn 40 agents, each calls GPT-4o
│   ├── demographics.py     ← Builds agent personas from SG demographic data
│   ├── contagion_v2.py     ← Social influence propagation (the "ripple effect")
│   ├── contagion.py        ← Old v1 (O(n²), kept for reference)
│   ├── mock_mode.py        ← Fake responses for testing without API keys
│   ├── levers.py           ← Policy parameter adjustments (sliders)
│   ├── scraper.py          ← TinyFish integration (live web scraping)
│   ├── real_data.py        ← Loads Census CSVs, GE results, income data
│   ├── backtest.py         ← Compare predictions vs actual GE2020 results
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 ← Main app (upload → simulate → display)
│   │   ├── hooks/useSimulation.js  ← WebSocket client, manages sim state
│   │   └── components/
│   │       ├── MapView.jsx         ← Leaflet map of Singapore GRCs
│   │       ├── SidePanel.jsx       ← Provisions + GRC detail + levers
│   │       ├── PolicyUpload.jsx    ← Drag-and-drop file upload
│   │       ├── AgentVoice.jsx      ← Agent quote bubbles
│   │       ├── DemographicBreakdown.jsx  ← Race/age sentiment bars
│   │       ├── LeverControls.jsx   ← Sliders to adjust policy params
│   │       ├── VotePrediction.jsx  ← Final PASS/FAIL vote call
│   │       ├── SimulationProgress.jsx ← Progress bar during sim
│   │       └── Header.jsx
│   └── public/
│       └── sg_electoral_boundaries.geojson  ← Real SG constituency map
│
├── data/
│   ├── grc_profiles.json          ← 15 GRCs with demographics + GE2020 data
│   ├── sg_demographics.json       ← National-level Census summary
│   ├── pop_age_sex.csv            ← Census: population by age/sex/planning area
│   ├── pop_ethnicity.csv          ← Census: population by race/planning area
│   ├── households_dwelling.csv    ← Census: housing types by planning area
│   ├── income_by_area.csv         ← Census: income distribution by area
│   ├── ge_results.csv             ← Election results 1955-2025
│   ├── voter_turnout.csv          ← Voter turnout 1955-2025
│   ├── ura_subzone_boundary.geojson  ← URA planning area boundaries
│   └── test_policy.pdf            ← Sample budget policy for testing
│
└── eval/
    └── benchmark.py               ← Validation scripts
```

---

## How To Run

### Quick Start (30 seconds)

```bash
cd polisim-repo

# 1. Make sure .env has your keys (already done if Clawdy set it up)
cat .env   # should show OPENAI_API_KEY and TINYFISH_API_KEY

# 2. Start both servers
./demo.sh
```

Open `http://localhost:3000`. Upload a PDF or text file. Click "Run Simulation". Done.

### Manual Start (if demo.sh doesn't work)

```bash
# Terminal 1: Backend
cd polisim-repo
source venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd polisim-repo/frontend
npm run dev
```

### Testing Without API Keys (Mock Mode)

If you remove the `OPENAI_API_KEY` from `.env` (or set it to something short), mock mode kicks in automatically. Everything works the same but with fake SG-themed responses instead of real GPT-4o calls. Great for frontend iteration.

---

## What Inputs Can I Provide?

### Via the UI (localhost:3000)
- **PDF** — any policy document, budget statement, white paper
- **TXT** — plaintext file with policy description
- **MD** — markdown file

### Via API (curl / Postman)

**Upload a file:**
```bash
curl -X POST http://localhost:8000/api/upload -F "file=@your_policy.pdf"
```

**Paste raw text (no file needed):**
```bash
curl -X POST http://localhost:8000/api/upload-text \
  -H 'Content-Type: application/json' \
  -d '{"text": "The government will raise GST from 9% to 10% in 2027."}'
```

**Run backtest (compare against real GE2020):**
```bash
curl http://localhost:8000/api/backtest
```

**Gerrymandering analysis:**
```bash
curl -X POST http://localhost:8000/api/gerrymander \
  -H 'Content-Type: application/json' \
  -d '{"target_party": "PAP"}'
```

**Adjust policy levers (re-run with different params):**
```bash
curl -X POST "http://localhost:8000/api/adjust/{policy_id}?lever=income_threshold&value=12000"
```

---

## What Can I Tweak?

### Agent Count
In `backend/demographics.py` → `build_personas(target_count=40)`. Change `40` to `100` or `200` for richer sim (costs more OpenAI tokens, takes longer).

### Agent Persona Template
In `backend/agent_engine.py` → `AGENT_SYSTEM_PROMPT`. This is the prompt each agent gets. You can change the tone, add more persona fields, adjust the response format.

### Contagion Strength
In `backend/contagion_v2.py` → `GROUP_WEIGHTS` dict and `DAMPING` constant. Higher damping (0.7→0.9) = agents more stubborn. Lower = more easily influenced by their community.

### GRC Profiles
`data/grc_profiles.json` — add/remove constituencies, change demographic weights. These drive persona generation.

### Policy Levers
`backend/levers.py` → `LEVER_DEFINITIONS`. Add new sliders (e.g., "retirement_age", "foreign_worker_levy") and define how they modify provisions.

### OpenAI Model
In `backend/agent_engine.py` and `backend/policy_parser.py` — change `model="gpt-4o"` to `"gpt-4o-mini"` (cheaper, faster, less nuanced) or `"gpt-4-turbo"`.

---

## Where MiroFish Plugs In

MiroFish is a multi-agent "swarm intelligence" engine that builds a parallel digital world from documents using GraphRAG. Here's where it connects:

### Option A: Replace the Agent Engine (Deepest Integration)

**Instead of** our simple 40-agent GPT-4o loop (`agent_engine.py`), MiroFish:
1. Takes the parsed provisions from `policy_parser.py`
2. Builds a knowledge graph of entities and relationships
3. Auto-generates agents with distinct personas, long-term memory, behavioral rules
4. Simulates interactions across social environments (Twitter-like, Reddit-like)
5. Returns emergent sentiment/outcomes

**Where to wire:** Replace the `stream_agent_results()` call in `main.py` (line ~67) with a MiroFish API call. The WebSocket handler just needs results in this shape:

```python
{
    "sentiment": "support" | "neutral" | "reject",
    "confidence": 0.8,
    "reason": "As a 35yo nurse...",
    "vote_intent": "for" | "against" | "undecided",
    "key_provision": "#2",
    "persona": {"race": "Chinese", "age": "30-44", "grc": "Ang Mo Kio GRC", ...},
    "score": 1.0   # 1.0=support, 0=neutral, -1=reject
}
```

### Option B: Replace the Contagion Model (Medium Integration)

**Instead of** our simple group-based contagion (`contagion_v2.py`), MiroFish handles the social simulation layer — agents interacting over rounds, building coalitions, shifting opinions organically.

**Where to wire:** Replace the `propagate_sentiment()` calls in `main.py` (lines ~73-80).

### Option C: Supplement with Sentiment Scraping (Lightest Integration)

**Use MiroFish** to scrape/analyze real public sentiment from forums, then seed our agents' initial attitudes with that data. This sits alongside TinyFish.

**Where to wire:** `backend/scraper.py` — add a `mirofish_scrape()` function, call it from the sim loop to ground agents in real-world sentiment.

### Data Format Contract

Whatever MiroFish returns, the frontend needs these fields per agent:
- `sentiment` (string: "support"/"neutral"/"reject")
- `reason` (string: 1-2 sentence quote)
- `persona.race`, `persona.age`, `persona.grc` (for map/breakdown display)
- `score` (float: -1 to 1, for contagion math)

---

## API Reference (All Endpoints)

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check + mock mode status |
| `POST` | `/api/upload` | Upload PDF/TXT/MD → parse provisions |
| `POST` | `/api/upload-text` | Paste raw text → parse provisions |
| `WS` | `/ws/simulate/{policy_id}` | Stream simulation (agents → contagion → vote) |
| `GET` | `/api/demographics` | GRC profiles with Census + GE2020 data |
| `POST` | `/api/adjust/{policy_id}` | Re-run with modified policy params |
| `GET` | `/api/backtest` | Compare predictions vs actual GE2020 |
| `POST` | `/api/gerrymander` | Redistricting/gerrymandering analysis |

### WebSocket Message Types (what the frontend receives)

```
→ {"type": "agent_result", "data": {...}}     # one per agent (40 total)
→ {"type": "contagion_round", "round": 0-2}   # sentiment propagation
→ {"type": "vote_prediction", "data": {...}}   # final vote call
→ {"type": "complete"}                         # simulation done
```

---

## Data Sources (All Real, All Open)

| Dataset | Source | Records |
|---------|--------|---------|
| Electoral boundaries (GeoJSON) | data.gov.sg / ELD | 31 constituencies |
| Population by age/sex | Census 2020 / SingStat | 389 planning areas |
| Population by ethnicity | Census 2020 / SingStat | 389 planning areas |
| Households by dwelling type | Census 2020 / SingStat | 31 planning areas |
| Income distribution | Census 2020 / SingStat | 31 planning areas |
| Election results | ELD | 1955-2025 (1610 rows) |
| Voter turnout | ELD | 1955-2025 (754 rows) |
| URA subzone boundaries | URA | 3.2MB GeoJSON |

---

## Hackathon Demo Script (2 min)

1. **Hook** (15s): "14 million scenarios, only one you win. Polysim is a prediction market without the market."
2. **Upload** (15s): Drop in a real policy PDF → provisions appear
3. **Simulate** (20s): Click Run → watch 40 agents stream in, map lights up, click a GRC
4. **Backtest** (15s): "We retroactively called Sengkang and Aljunied for the opposition"
5. **Gerrymander** (20s): "What if we redrew boundaries? Polysim finds the swing seats"
6. **Levers** (15s): Pull the income slider → watch sentiment shift live
7. **Expand** (15s): "Policy is just the start. Marketing campaigns, M&A, product launches — anything that's a bet on how people react"
8. **Close** (5s): "Polysim. We help you win."
