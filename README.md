# Polysim — Prediction Market in Silico

> "14 million scenarios, only one you win."
> Upload a policy. Watch a simulated population bet on the outcome.

---

## ELI5: What This Does

You paste/upload a policy document (like "raise GST to 10%"). Polysim:

1. **Reads it** — GPT-4o extracts key provisions ("GST increase", "CPF change", etc.)
2. **Spawns 100+ AI agents** — each represents a real demographic slice of Singapore (Chinese nurse in Ang Mo Kio, aged 35; Malay retiree in Jurong, aged 68; Indian PME in Sengkang, aged 28; etc.)
3. **Each agent reads the policy and bets** — self-interested agents stake virtual tokens on whether the policy helps or hurts them. Risk appetite scales with demographics (young + rich = bolder bets).
4. **Social contagion / market rounds** — agents influence each other through social networks (same race/neighborhood/age = stronger ties). Information cascades over 3 market rounds, shifting positions.
5. **Market price emerges** — the clearing price (implied probability) is more reliable than raw polling because it weights conviction and skin-in-the-game.
6. **Dashboard shows results** — Singapore map lights up by constituency, agent quotes, per-GRC market prices, demographic breakdown, price evolution chart.

It's like running a prediction market before anyone places a real bet.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                    │
│  localhost:3000                                              │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Policy   │  │ Map View │  │ Side     │  │ Vote/Market │ │
│  │ Upload   │  │ (Leaflet)│  │ Panel    │  │ Prediction  │ │
│  └────┬─────┘  └────▲─────┘  └────▲─────┘  └──────▲──────┘ │
│       │              │             │                │        │
│       └──────────────┴─────────────┴────────────────┘        │
│                  useSimulation.js (WebSocket)                 │
└───────┬──────────────────────────────────────────────────────┘
        │ HTTP + WebSocket
┌───────┴──────────────────────────────────────────────────────┐
│                    BACKEND (Python FastAPI)                    │
│  localhost:8000                                              │
│                                                              │
│  main.py ─── Orchestrator                                    │
│  ├── config.py          ← Region config (extensible)         │
│  ├── policy_parser.py   ← PDF/text → provisions (GPT-4o)    │
│  ├── demographics.py    ← Build 100+ weighted personas       │
│  ├── agent_engine.py    ← GPT-4o per persona (with retry)   │
│  ├── market.py          ← Prediction market model            │
│  ├── contagion_v2.py    ← O(n) social influence propagation │
│  ├── mock_mode.py       ← Deterministic offline fallback     │
│  ├── levers.py          ← Policy parameter adjustments       │
│  ├── scraper.py         ← TinyFish live sentiment scraping   │
│  ├── real_data.py       ← Census 2020 + GE2020/2025 data    │
│  └── backtest.py        ← Validate vs real election results  │
│                                                              │
│  External: OpenAI GPT-4o · TinyFish API · pdfplumber        │
└──────────────────────────────────────────────────────────────┘
        │
┌───────┴──────────────────────────────────────────────────────┐
│  data/                                                        │
│  grc_profiles.json     (31 GRCs/SMCs, GE2025 boundaries)    │
│  ge_results.csv        (election results 1955–2025)          │
│  pop_age_sex.csv       (Census 2020 by planning area)        │
│  pop_ethnicity.csv     (Census 2020 by race)                 │
│  households_dwelling.csv (housing types by area)             │
│  income_by_area.csv    (income distribution)                 │
│  voter_turnout.csv     (turnout 1955–2025)                   │
│  sg_demographics.json  (national-level Census summary)       │
└──────────────────────────────────────────────────────────────┘
```

---

## File Guide

```
polisim-repo/
├── .env                    ← YOUR API KEYS (never commit)
├── .env.example            ← Template for .env
├── demo.sh                 ← One-command startup
│
├── backend/
│   ├── main.py             ← FastAPI server, all routes, WebSocket
│   ├── config.py           ← Region configuration (swap for other geographies)
│   ├── market.py           ← Prediction market model (bets, clearing price)
│   ├── policy_parser.py    ← PDF/text → provisions (GPT-4o, retry logic)
│   ├── agent_engine.py     ← 100+ agents × GPT-4o (risk_appetite, retry)
│   ├── demographics.py     ← Census-weighted personas (4 ages × 4 races × 4 incomes)
│   ├── contagion_v2.py     ← Social influence / market rounds (O(n))
│   ├── mock_mode.py        ← Deterministic fakes (16 demographic combos)
│   ├── levers.py           ← Policy parameter sliders
│   ├── scraper.py          ← TinyFish (Reddit, HWZ, CNA scraping)
│   ├── real_data.py        ← Census CSVs + GE2020/2025 results
│   └── backtest.py         ← Validate predictions vs real elections
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── hooks/useSimulation.js  ← WebSocket + market state
│   │   └── components/
│   │       ├── MapView.jsx         ← Leaflet choropleth (GE2025 boundaries)
│   │       ├── SidePanel.jsx       ← Provisions + market prices + live sentiment
│   │       ├── VotePrediction.jsx  ← Market clearing price + price chart
│   │       ├── SimulationProgress.jsx ← Dynamic agent count + market price
│   │       ├── PolicyUpload.jsx    ← Drag-and-drop upload
│   │       ├── AgentVoice.jsx      ← Agent quotes with bet amounts
│   │       ├── DemographicBreakdown.jsx
│   │       ├── LeverControls.jsx
│   │       └── Header.jsx
│   └── public/
│       └── sg_electoral_boundaries.geojson
│
├── data/                   ← All real, all open (Singapore Open Data Licence)
│   ├── grc_profiles.json   ← 31 constituencies (GE2025 boundaries)
│   ├── ge_results.csv      ← 1955–2025 election results
│   └── ...                 ← Census CSVs (see above)
│
└── eval/
    └── benchmark.py        ← Full validation suite
```

---

## How To Run

### Quick Start

```bash
cd polisim-repo

# 1. Set up .env
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY and optionally TINYFISH_API_KEY

# 2. Start both servers
./demo.sh
```

Open `http://localhost:3000`. Upload a PDF. Click "Run Simulation".

### Manual Start

```bash
# Terminal 1: Backend
cd polisim-repo && source venv/bin/activate
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd polisim-repo/frontend && npm run dev
```

### Mock Mode (No API Keys)

Remove `OPENAI_API_KEY` from `.env` (or set to placeholder). Everything works with deterministic Singapore-themed responses. Great for frontend iteration.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check, mock mode status, region |
| `POST` | `/api/upload` | Upload PDF/TXT/MD → parse provisions |
| `POST` | `/api/upload-text` | `{"text": "..."}` → parse provisions |
| `WS` | `/ws/simulate/{id}?agents=100` | Stream simulation (agents → market rounds → prediction) |
| `GET` | `/api/demographics?ge_year=2025` | GRC profiles + election data |
| `POST` | `/api/adjust/{id}?lever=X&value=Y` | Modify policy params, get new ID |
| `GET` | `/api/backtest?ge_year=2025&agents=200` | Validate vs real GE results |
| `POST` | `/api/gerrymander` | `{"target_party": "PAP", "ge_year": 2025}` |

### WebSocket Message Types

```
← {"type": "config",          "data": {"total_agents": 120, "contagion_rounds": 3}}
← {"type": "agent_result",    "data": {sentiment, confidence, reason, persona, conviction_bet, yes_bet, no_bet, ...}}
← {"type": "market_update",   "round": 0, "data": {market_price, implied_probability_pct, ...}}
← {"type": "live_sentiment",  "data": {sources_scraped, price_adjustment, sentiments: [...]}}
← {"type": "contagion_round", "round": 0-2, "data": {grc_aggregates}, "market": {market_price, ...}}
← {"type": "vote_prediction", "data": {for_pct, against_pct, call, market: {...}, price_history: [...]}}
← {"type": "complete"}
```

---

## Configuration & Customization

### Agent Count
WebSocket query param: `?agents=200` (default 100, max 500).
Or backtest endpoint: `?agents=300`.

### Region / Geography
Edit `backend/config.py`. All demographic data (races, age bands, income tiers, housing, occupations, concerns, risk appetite curves, contagion parameters) lives in a config dict. To simulate a different region:
1. Create a new config dict (e.g., `HONG_KONG`)
2. Place constituency profiles JSON in `/data/`
3. Set `ACTIVE_REGION = HONG_KONG`
4. Update frontend GeoJSON + map center in `MapView.jsx`

### Contagion Model
In `config.py` → `contagion` dict:
- `damping` (0.7): how much agents resist change (higher = more stubborn)
- `group_weights`: influence strength per group type
- `social_media_by_age`: cross-GRC information flow by age

### Policy Levers
`backend/levers.py` → `LEVER_DEFINITIONS`. Add new sliders and keyword-matching rules.

### Prediction Market Tuning
`backend/market.py`: bet sizing, neutral agent split, live sentiment weight (15%).
`backend/config.py`: `risk_appetite_by_age/income/housing` curves.

---

## Data Sources

| Dataset | Source | Coverage |
|---------|--------|----------|
| Electoral boundaries (GeoJSON) | ELD / data.gov.sg | 31 GE2025 constituencies |
| Population by age/sex | Census 2020 / SingStat | 389 planning areas |
| Population by ethnicity | Census 2020 / SingStat | 389 planning areas |
| Households by dwelling type | Census 2020 / SingStat | 31 planning areas |
| Income distribution | Census 2020 / SingStat | 31 planning areas |
| Election results | ELD | 1955–2025 (1610 rows) |
| Voter turnout | ELD | 1955–2025 (754 rows) |

All data is public under Singapore Open Data Licence. No API keys needed for access.

---

## Demo Script (2 min)

1. **Hook** (15s): "14 million scenarios, only one you win. Polysim is a prediction market in silico."
2. **Upload** (15s): Drop in a real policy PDF → provisions appear
3. **Simulate** (20s): Watch 100+ agents stream in, placing bets. Map lights up. Market price emerges.
4. **Backtest** (15s): "We retroactively called GE2025 results with 67% accuracy — without training on election data"
5. **Market** (15s): Show the price evolution chart. "This isn't a poll — it's a market. Polls lie; markets don't."
6. **Levers** (15s): Pull the income slider → watch the market price shift live
7. **Expand** (15s): "Policy is just the start. Marketing campaigns, M&A, product launches — anything that's a bet on how people react"
8. **Close** (5s): "Polysim. Run the bet before anyone votes."
