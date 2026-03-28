# Polysim Design Notes

This file records the current implementation model, the main logic threads through the codebase, and the important caveats uncovered during the audit.

## System Model

Polysim currently behaves as a staged simulation workbench:

1. Optional segment research/config generation.
2. Input parsing from scenario text, pasted policy text, or uploaded document.
3. Persona construction from Singapore constituency profiles plus demographic config.
4. Agent evaluation in mock mode or via OpenAI.
5. Market-price computation from conviction-weighted bets.
6. Three contagion rounds with group-based influence.
7. Final vote summary and constituency-level drilldown in the UI.

The design intent is broader than Singapore policy analysis, but the current implementation is still materially anchored to Singapore geography and data files.

## Logic Threads

### 1. Config-generation thread

Frontend entry:

- [`frontend/src/components/RegionConfigPanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/RegionConfigPanel.jsx)

Backend path:

- `POST /api/configure-region/stream` in [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py)
- `stream_research_and_generate()` in [`backend/config_generator.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config_generator.py)

Flow:

1. The user enters a segment/geography description.
2. The backend either plans TinyFish web research or falls back to OpenAI-only synthesis.
3. SSE events stream plan, search start, search results, narration, synthesis start, and completion.
4. The frontend stores the resulting `config_id`.
5. Later, `POST /api/apply-config/{policy_id}` attaches that config to a parsed simulation.

Design caveat:

- The generated config adjusts segments, concerns, risk appetite, and age weights.
- It does not currently change the constituency file loaded by persona generation, so this is not yet a full geography swap.

### 2. Input-parsing thread

Frontend entry:

- [`frontend/src/components/ScenarioInput.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/ScenarioInput.jsx)

Backend paths:

- `/api/upload`
- `/api/upload-text`
- `/api/interpret-scenario`

Code:

- [`backend/policy_parser.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/policy_parser.py)
- [`backend/scenario_interpreter.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scenario_interpreter.py)
- [`backend/mock_mode.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/mock_mode.py)

Flow variants:

- File upload:
  - bytes are read in FastAPI
  - PDFs go through `pdfplumber`
  - extracted text is truncated and sent to OpenAI
- Text upload:
  - raw text is truncated and sent to OpenAI
- Scenario interpretation:
  - arbitrary natural language is reframed as a binary market question plus provisions

Fallback behavior:

- In mock mode, uploads and pasted text use deterministic fake provisions.
- Scenario interpretation has an internal fallback that wraps the raw scenario as a single provision if the OpenAI call fails.

### 3. Persona-construction thread

Entry:

- `build_personas()` in [`backend/demographics.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/demographics.py)

Dependencies:

- [`backend/config.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config.py)
- [`data/grc_profiles.json`](/Users/tian/GitHub/polisim/polisim-repo/data/grc_profiles.json)

Flow:

1. Load constituency profiles.
2. Compute each constituency’s persona budget from population share.
3. Loop over segment label (`race`) and age band.
4. Sample income tier from age-based weights.
5. Sample housing type from income-tier weights.
6. Pick occupation deterministically.
7. Build a weight for population-representative aggregation.
8. Compute risk appetite from config curves, unless a generated custom config overrides it.

Current implementation details worth preserving:

- Segment determinism is driven by `md5(grc_name-race-age-index)`.
- The persona count commonly overshoots target by around `20%`.
- Custom segment configs reuse the `race` field for arbitrary segment labels.

### 4. Agent-evaluation thread

Entry:

- `stream_agent_results()` in [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py)

Flow:

1. Prompt variables are built from persona fields plus optional constituency context and optional scenario framing.
2. OpenAI `gpt-4o` is called with JSON output enforced.
3. Results are normalized for sentiment, confidence, and vote intent.
4. `score` is derived from sentiment.
5. Each result streams back as soon as the task completes.

Concurrency model:

- concurrency scales with agent count
- minimum `10`
- maximum `30`

Fallback path:

- Mock mode bypasses the LLM and returns deterministic values keyed off persona attributes.

### 5. Market thread

Entry:

- [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py)

Flow:

1. `compute_agent_bet()` maps each agent to `conviction_bet`, `yes_bet`, and `no_bet`.
2. `compute_market_price()` aggregates total yes/no volume and derives implied probability.
3. In the active WebSocket path, the initial market price is emitted before contagion.

Design intent:

- Weight is doing two jobs at once:
  - population representation
  - capital sizing in the market

That is acceptable for the current prototype, but it means the “market” is still a weighted simulation layer, not an independent liquidity model.

### 6. Live-sentiment thread

Entry:

- `scrape_sg_sentiment()` in [`backend/scraper.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scraper.py)

Flow:

1. After initial market computation, the backend optionally scrapes Reddit and HardwareZone for the first provision title.
2. Sentiment items are converted to engagement-weighted positive/negative/neutral signals.
3. `adjust_with_live_sentiment()` mixes that signal into the market price at `15%` weight.
4. During contagion rounds, the initial live adjustment decays by `0.7 ** round`.

Important implementation note:

- The code hardcodes `https://api.tinyfish.ai`.
- `.env.example` advertises `TINYFISH_BASE_URL`, but the implementation does not read it.

### 7. Contagion thread

Entry:

- `propagate_sentiment_v2()` in [`backend/contagion_v2.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion_v2.py)

Flow:

1. Compute weighted group means for constituency, segment, segment-by-age, and housing.
2. Compute a weighted influence score for each agent.
3. Blend influence with the agent’s current score using damping.
4. Recompute sentiment label, vote intent, confidence, and bet fields.
5. Send a `contagion_round` update to the frontend.

Why this matters:

- This is the active replacement for the older pairwise contagion model in [`backend/contagion.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion.py).
- The v2 model is the reason the simulation scales much better than the older O(n²) approach.

### 8. Aggregation and presentation thread

Backend:

- `aggregate_by_grc()` and `compute_vote_prediction()` in [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py)

Frontend:

- [`frontend/src/hooks/useSimulation.js`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/hooks/useSimulation.js)
- [`frontend/src/components/MapView.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/MapView.jsx)
- [`frontend/src/components/SidePanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/SidePanel.jsx)
- [`frontend/src/components/VotePrediction.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/VotePrediction.jsx)

Flow:

1. Agent results accumulate live in the hook.
2. Constituency sentiment is incrementally built during initial streaming, then replaced with backend aggregate snapshots during contagion rounds.
3. The map colors each constituency by support share.
4. The sidebar shows:
   - scenario frame
   - provisions
   - optional live sentiment
   - selected constituency breakdown
   - agent quotes
   - levers
   - final market prediction

## Audit Notes

### Documentation mismatches corrected

- The old docs did not describe scenario interpretation or streamed config generation.
- The old docs described older backtest numbers and a smaller matched-constituency set than the current code/data produce.
- The old docs implied full region portability; the current code only partially supports that.
- The old docs implied a single default agent count, but the current user path effectively defaults to `100` from the frontend while the backend constant is `200`.

### In-tree but not on the active path

- [`frontend/src/components/PolicyUpload.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/PolicyUpload.jsx)
- [`backend/contagion.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion.py)

### Active helpers that are not central to the primary UI flow

- `compute_market_by_grc()` in [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py)
- `compute_price_history()` in [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py)
- `run_simulation()` in [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py)
- the non-streaming `/api/configure-region` path in [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py)

### Architecture limits

- Generated segment configs do not alter map geometry.
- Persona loading still depends on the active global config’s `profiles_file`.
- The frontend’s absolute API URLs make the app less portable outside localhost.
- State is process-local and ephemeral.

## Backtest Notes

Backtest implementation:

- [`backend/backtest.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/backtest.py)

Current observed mock GE2025 output during the audit:

- total personas: `240` with `target_agents=200`
- matched constituencies: `32`
- `MAE`: `23.5`
- correct calls: `23/32`
- accuracy: `71.9%`
- correlation: `-0.139`

These numbers are a property of the current repo state, not a stable contract.

## Extension Guidance

### If the next goal is true geography portability

The minimum clean-up path is:

1. Make `load_grc_profiles()` accept the passed config override instead of only reading `get_config()`.
2. Move GeoJSON/source mapping into region config instead of hardcoding it in [`frontend/src/components/MapView.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/MapView.jsx).
3. Stop overloading the `race` field for arbitrary segments.
4. Replace absolute frontend API URLs with relative `/api` and `/ws`.

### If the next goal is better reproducibility

1. Persist simulations/configs instead of using in-memory dicts.
2. Version benchmark outputs in a checked-in artifact.
3. Expose the actual requested agent count and actual generated persona count separately in the API/UI.

## File-level Reference

- [`backend/main.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/main.py): orchestration and API surface.
- [`backend/config_generator.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/config_generator.py): research-and-generate segment configs.
- [`backend/scenario_interpreter.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/scenario_interpreter.py): free-form scenario framing.
- [`backend/demographics.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/demographics.py): persona generation.
- [`backend/agent_engine.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/agent_engine.py): agent evaluation.
- [`backend/market.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/market.py): betting model.
- [`backend/contagion_v2.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/contagion_v2.py): active contagion engine.
- [`backend/real_data.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/real_data.py): real-data enrichment and constituency matching.
- [`backend/backtest.py`](/Users/tian/GitHub/polisim/polisim-repo/backend/backtest.py): benchmark path.
- [`frontend/src/App.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/App.jsx): top-level stage flow.
- [`frontend/src/hooks/useSimulation.js`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/hooks/useSimulation.js): client simulation state.
- [`frontend/src/components/RegionConfigPanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/RegionConfigPanel.jsx): config-generation UI.
- [`frontend/src/components/ScenarioInput.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/ScenarioInput.jsx): input UI.
- [`frontend/src/components/MapView.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/MapView.jsx): geography visualization.
- [`frontend/src/components/SidePanel.jsx`](/Users/tian/GitHub/polisim/polisim-repo/frontend/src/components/SidePanel.jsx): narrative/result detail view.
