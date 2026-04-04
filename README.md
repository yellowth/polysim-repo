# Polysim

Prediction-market-style policy and scenario simulation for Singapore-focused demographic agents.

The current app lets a user:

1. Optionally generate a custom segment configuration from a natural-language description.
2. Provide input as a free-form scenario, pasted policy text, or uploaded `PDF`/`TXT`/`MD`.
3. Parse that input into structured provisions.
4. Build weighted personas from constituency profiles plus demographic config.
5. Run agent evaluations in mock mode or via OpenAI.
6. Convert agent opinions into bets, compute a market price, apply three contagion rounds, and stream results over WebSocket.
7. Inspect constituency sentiment, agent quotes, vote breakdown, and price evolution in the frontend.

## Audit Summary

This README reflects the code as it exists now, not the earlier design intent.

Key audit findings:

- The app now has a three-stage UI flow: region/segment config, scenario/policy input, then simulation.
- Backend support exists for scenario interpretation and streaming region-config generation, but the older docs did not cover those paths.
- Persona generation usually returns roughly `120%` of the requested target count. For example, `build_personas(100)` currently returns `120`, and `build_personas(200)` returns `240`.
- The repository currently ships `33` constituency profiles in [`data/grc_profiles.json`](/Users/tian/GitHub/polisim/polisim-repo/data/grc_profiles.json).
- Region config overrides change demographic segments and age weights, but they do not fully swap geography. Persona loading still reads the active global profiles file from [`backend/config.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config.py), and the frontend map remains Singapore-specific.
- TinyFish base URL is hardcoded to `https://api.tinyfish.ai` in [`backend/scraper.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scraper.py); `TINYFISH_BASE_URL` in [`.env.example`](/Users/tian/GitHub/polisim/polisim-repo/.env.example) is not currently consumed.
- The frontend uses absolute `http://localhost:8000` and `ws://localhost:8000` URLs in active components instead of the Vite proxy config.
- [`backend/contagion.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion.py) and [`frontend/src/components/PolicyUpload.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/PolicyUpload.jsx) are legacy files that are present in-tree but not used by the main app flow.

## Current Architecture

### Frontend

- React 18 + Vite + Tailwind.
- Main app entry: [`frontend/src/App.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/App.jsx).
- Simulation state and WebSocket handling: [`frontend/src/hooks/useSimulation.js`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/hooks/useSimulation.js).
- Key UI stages:
  - [`frontend/src/components/RegionConfigPanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/RegionConfigPanel.jsx): streaming SSE research/config generation.
  - [`frontend/src/components/ScenarioInput.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/ScenarioInput.jsx): scenario interpretation, text parsing, file upload.
  - [`frontend/src/components/SimulationProgress.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/SimulationProgress.jsx): simulation progress and live agent feed.
  - [`frontend/src/components/MapView.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/MapView.jsx): Singapore constituency map from static GeoJSON.
  - [`frontend/src/components/SidePanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/SidePanel.jsx): scenario frame, provisions, live sentiment, constituency detail, levers, final prediction.

### Backend

- FastAPI app entry: [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py).
- In-memory simulation store keyed by `policy_id`.
- Main pipeline modules:
  - [`backend/policy_parser.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/policy_parser.py): policy text/PDF to provisions.
  - [`backend/scenario_interpreter.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scenario_interpreter.py): natural-language scenario to structured binary framing plus provisions.
  - [`backend/config_generator.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config_generator.py): optional segment config generation with streamed SSE events.
  - [`backend/demographics.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/demographics.py): weighted persona construction.
  - [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py): per-persona evaluation via OpenAI.
  - [`backend/mock_mode.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/mock_mode.py): deterministic offline behavior when OpenAI is unavailable.
  - [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py): conviction bet sizing and market price calculation.
  - [`backend/contagion_v2.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion_v2.py): O(n) group-based sentiment propagation.
  - [`backend/real_data.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/real_data.py): CSV/JSON enrichment for constituency and election data.
  - [`backend/backtest.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/backtest.py): historical benchmark path.
  - [`backend/scraper.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scraper.py): TinyFish sentiment/news/demo-data integration.
  - [`backend/levers.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/levers.py): post-parse provision mutations.

## End-to-End Logic

### Stage A: Optional segment configuration

1. The frontend calls `POST /api/configure-region/stream` with a free-form description.
2. [`backend/config_generator.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config_generator.py) either:
   - plans TinyFish research, streams search/narration events, and synthesizes a config with OpenAI, or
   - falls back to OpenAI-only generation if TinyFish is unavailable.
3. The resulting config is stored in memory and returned with a `config_id`.
4. The frontend later applies that config to a specific simulation with `POST /api/apply-config/{policy_id}`.

### Stage B: Input parsing

The app supports three input paths:

- `POST /api/upload`
  - Accepts uploaded file bytes.
  - Enforces a `10MB` limit.
  - In mock mode, uses `mock_parse_provisions`.
  - Otherwise parses PDFs with `pdfplumber` and sends extracted text to OpenAI.
- `POST /api/upload-text`
  - Accepts raw text up to `50,000` characters.
  - Uses mock parser or OpenAI parser.
- `POST /api/interpret-scenario`
  - Converts arbitrary text into:
    - `title`
    - `yes_definition`
    - `no_definition`
    - `context`
    - `time_horizon`
    - `domain`
    - `provisions`
    - `stakes_by_segment`

Each input path creates a new in-memory simulation entry.

### Stage C: Simulation

1. The frontend opens `WS /ws/simulate/{policy_id}?agents=N`.
2. The backend resolves provisions, optional scenario frame, and optional region config override.
3. Personas are built with `build_personas(target_count=agent_count, config=region_config)`.
4. The backend streams:
   - `config`
   - `agent_result` messages for each evaluated persona
   - an initial `market_update`
   - optional `live_sentiment`
   - three `contagion_round` updates
   - final `vote_prediction`
   - `complete`

The active frontend currently calls `sim.connect(policyId)` without an override, so the user-facing simulation path requests `100` agents by default even though the backend constant `DEFAULT_AGENT_COUNT` is `200`.

## Persona Model

Persona generation lives in [`backend/demographics.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/demographics.py).

Current behavior:

- Constituency profiles load from [`data/grc_profiles.json`](/Users/tian/GitHub/polisim/polisim-repo/data/grc_profiles.json) through the active config.
- Segmentation loops over `race × age × constituency`.
- Income tiers are sampled from age-specific distributions.
- Housing is sampled from income-specific distributions.
- Occupation is deterministically chosen from the tier’s occupation list.
- Concerns are sampled per race/segment.
- Risk appetite is derived from age, income tier, and housing unless a generated custom-segment config overrides it.
- Each persona receives a `weight` used later for aggregation.

Important caveats:

- `build_personas` accepts a config override, but `load_grc_profiles()` still reads from the global active config, so custom region generation does not yet swap out constituency data files.
- For generated custom segment configs, segment labels are stored in the `race` field and distributed equally because constituency profiles do not contain matching per-segment census shares.
- Trimming only occurs when the raw persona count exceeds `target_count * 1.5`; otherwise the overshoot remains.

## Market and Contagion Model

### Market

[`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py) turns each agent into a bettor.

- `conviction_bet = risk_appetite × confidence × weight`
- `support` maps to all `YES`
- `reject` maps to all `NO`
- `neutral` splits `40% YES / 60% NO`
- `market_price = total_yes / (total_yes + total_no)`

Returned market metadata includes:

- implied probability
- volume
- yes/no volume
- active bettors
- spread
- confidence label

### Contagion

[`backend/contagion_v2.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion_v2.py) is the active contagion engine.

It computes weighted group means for:

- constituency
- race/segment
- race/segment by age
- housing
- global sentiment

Then each agent blends:

- its own current score
- neighborhood/group influence
- age-weighted social-media/global influence

The damping factor and group weights come from [`backend/config.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config.py).

Legacy note:

- [`backend/contagion.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion.py) is the older pairwise implementation and is not used by the active API path.

## API Reference

### Implemented HTTP endpoints

| Method | Endpoint | Current behavior |
| --- | --- | --- |
| `GET` | `/api/health` | Returns status, project name, mock mode, active region name, and backend default agent count. |
| `POST` | `/api/upload` | Parses uploaded `PDF`/`TXT`/`MD` file into provisions. |
| `POST` | `/api/upload-text` | Parses raw text into provisions. |
| `POST` | `/api/interpret-scenario` | Converts a free-form scenario into binary framing plus provisions. |
| `POST` | `/api/configure-region` | Non-streaming config generation helper. |
| `POST` | `/api/configure-region/stream` | SSE stream for research and config synthesis. |
| `POST` | `/api/apply-config/{policy_id}` | Attaches a generated or inline config override to an existing simulation. |
| `GET` | `/api/demographics` | Returns enriched constituency profiles for the requested election year. |
| `GET` | `/api/backtest` | Runs a historical backtest in mock mode or real mode depending on OpenAI availability. |
| `POST` | `/api/gerrymander` | Returns constituency vulnerability and redistricting-style heuristics. |
| `POST` | `/api/adjust/{policy_id}` | Applies a lever mutation to provisions and returns a new simulation id. |

### Implemented WebSocket endpoint

| Method | Endpoint | Current behavior |
| --- | --- | --- |
| `WS` | `/ws/simulate/{policy_id}?agents=N` | Streams simulation progress, market state, contagion rounds, and final vote prediction. |

### WebSocket message types

- `config`
- `agent_result`
- `market_update`
- `live_sentiment`
- `contagion_round`
- `vote_prediction`
- `complete`
- `error`

## Data Files

Primary shipped data:

- [`data/grc_profiles.json`](/Users/tian/GitHub/polisim/polisim-repo/data/grc_profiles.json): base constituency profiles with `pop`, ethnicity mix, seats, center, and incumbent party.
- [`data/ge_results.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/ge_results.csv): election results from `1955` through `2025`.
- [`data/voter_turnout.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/voter_turnout.csv): turnout rows from `1955` through `2025`.
- [`data/pop_age_sex.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/pop_age_sex.csv)
- [`data/pop_ethnicity.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/pop_ethnicity.csv)
- [`data/households_dwelling.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/households_dwelling.csv)
- [`data/income_by_area.csv`](/Users/tian/GitHub/polisim/polisim-repo/data/income_by_area.csv)
- [`data/sg_demographics.json`](/Users/tian/GitHub/polisim/polisim-repo/data/sg_demographics.json)
- [`frontend/public/sg_electoral_boundaries.geojson`](/Users/tian/GitHub/polisim/polisim-repo/frontend/public/sg_electoral_boundaries.geojson): frontend map geometry.

Current profile/election facts verified from repo contents:

- `grc_profiles.json`: `33` profiles
- `ge_results.csv`: includes election rows for `1955, 1959, 1963, 1968, 1972, 1976, 1980, 1984, 1988, 1991, 1997, 2001, 2006, 2011, 2015, 2020, 2025`
- `voter_turnout.csv`: includes turnout rows for the same year set

## Running the App

### Railway (backend API)

This repo is a monorepo (`frontend/`, `policy-extract/`, `backend/`). Railway’s **Railpack** auto-builder can fail with “Error creating build plan with Railpack” because it sees multiple stacks.

1. Keep the service **Root Directory** at the **repository root** (clear the field or use `/`). The root [`Dockerfile`](Dockerfile) copies `backend/` and `data/` and runs uvicorn; Railway uses Docker and skips Railpack.
2. Do **not** set Root Directory to `backend` only — the API expects [`data/`](data/) next to `backend/` on disk.
3. Add env vars from [`.env.example`](.env.example) (e.g. `OPENAI_API_KEY` if not using mock mode).
4. Point the frontend at the public URL: build with `VITE_API_URL=https://<your-service>.up.railway.app` (see `frontend/.env.example`).

### Quick start

```bash
cd polisim-repo
cp .env.example .env
./demo.sh
```

### Manual start

```bash
cd polisim-repo

# backend
source venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# frontend
cd ../frontend
npm run dev
```

### Environment variables

## Demo Cache

For judge/demo flows, the repo now ships a small local TinyFish seed cache plus bundled demo policy samples:

- [`data/demo_policy_samples.json`](/Users/tian/GitHub/polisim/polisim-repo/data/demo_policy_samples.json): five pre-parsed demo policies/snippets
- [`data/demo_tinyfish_cache.json`](/Users/tian/GitHub/polisim/polisim-repo/data/demo_tinyfish_cache.json): cache-first TinyFish sentiment payloads keyed by demo topic

Useful paths:

- `GET /api/demo-samples` lists bundled demo topics/snippets.
- `POST /api/demo-samples/{sample_id}` creates a simulation directly from a bundled sample, bypassing parse latency.
- `python backend/prewarm_demo_cache.py` refreshes the local sentiment cache from live TinyFish for all bundled samples when `TINYFISH_API_KEY` is configured.

The simulation WebSocket now checks the local TinyFish cache first, then falls back to a live TinyFish fetch and writes successful responses back into the same JSON cache file.

Expected by the code:

- `OPENAI_API_KEY`
- `TINYFISH_API_KEY`

Important note:

- `TINYFISH_BASE_URL` appears in [`.env.example`](/Users/tian/GitHub/polisim/polisim-repo/.env.example), but the current scraper implementation does not read it.

### Mock mode

Mock mode is enabled when `OPENAI_API_KEY` is missing, obviously placeholder-like, or shorter than `20` characters.

In mock mode:

- uploads and pasted text use `mock_parse_provisions`
- agent evaluation uses `mock_agent_response`
- TinyFish live-sentiment scraping is skipped by the simulation path

## Backtesting and Evaluation

### Backtest

```bash
cd polisim-repo
source venv/bin/activate
cd backend
python3 backtest.py 2025
```

Current mock GE2025 backtest observed from the repository code on `2026-03-28`:

- matched constituencies: `32`
- total generated personas: `240` when `target_agents=200`
- `MAE`: `23.5`
- correct calls: `23/32`
- call accuracy: `71.9%`
- correlation: `-0.139`

These numbers are not guaranteed stable because they depend on shipped data and current implementation details.

### Eval script

```bash
cd polisim-repo
source venv/bin/activate
python3 eval/benchmark.py
```

[`eval/benchmark.py`](/Users/tian/GitHub/polisim/polisim-repo/eval/benchmark.py) checks:

- demographic differentiation by race
- demographic differentiation by age
- vote total coherence
- market validity
- backtest thresholds

## File Guide

### Active files

- [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py): API entry point and simulation orchestration.
- [`backend/config.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config.py): active Singapore config and contagion defaults.
- [`backend/demographics.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/demographics.py): persona builder.
- [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py): OpenAI-backed persona evaluation.
- [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py): bets and market aggregation.
- [`backend/contagion_v2.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion_v2.py): active contagion model.
- [`backend/policy_parser.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/policy_parser.py): provision extraction.
- [`backend/scenario_interpreter.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scenario_interpreter.py): free-form scenario framing.
- [`backend/config_generator.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config_generator.py): streaming config generation.
- [`frontend/src/App.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/App.jsx): stage orchestration.
- [`frontend/src/hooks/useSimulation.js`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/hooks/useSimulation.js): simulation state.

### Present but secondary or legacy

- [`backend/contagion.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion.py): older contagion implementation.
- [`frontend/src/components/PolicyUpload.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/PolicyUpload.jsx): older upload component not used by the current app.
- [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py) exports `compute_market_by_grc` and `compute_price_history`, but the main WebSocket path currently computes history inline and uses local aggregation in [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py).
- [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py) exports `run_simulation`, but the main app streams per-agent results through `stream_agent_results`.

## Known Limitations

- Region generation is currently closer to “custom segmentation over Singapore geography” than fully geography-agnostic simulation.
- The frontend map and electoral-boundary mapping are Singapore-specific and manually keyed.
- Some frontend calls bypass Vite proxying by using absolute localhost URLs.
- Generated segment configs reuse the `race` field to carry arbitrary segment labels.
- Simulation and config state are in-memory only and disappear on restart.
- The app does not persist uploads, results, or generated configs.
- `demo.sh` installs dependencies on every run.

## Documentation Scope

This README is intended to describe the current implementation. Design ideas, extension guidance, and deeper rationale now live in [`DESIGN.md`](/Users/tian/GitHub/polisim/polisim-repo/DESIGN.md).
