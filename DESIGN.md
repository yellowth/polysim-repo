# Polysim — Design & Architecture Q&A

Deep technical answers to architectural questions about how Polysim works, why it works this way, and how to extend it.

---

## 1. Do the agents properly represent Singapore's population?

### Previous (broken)
- Only 40 agents, 2 age bands (30-44, 60+), hardcoded income/housing per age
- Skipped 21-29 and 45-59 entirely — missing young voters and mid-career PMEs
- "Others" race (3-5% of population) completely excluded
- Income was deterministic: 30-44 always got middle income, 60+ always got low
- Housing was deterministic: middle income always got HDB 4-5, low always got HDB 1-3

### Current (fixed)
- **100-500 agents** (configurable via `?agents=N` query param)
- **All 4 age bands**: 21-29, 30-44, 45-59, 60+ with Census-based weights (18%, 28%, 26%, 28%)
- **All 4 races**: Chinese, Malay, Indian, Others — with diversity-preserving trim so minority groups aren't cut
- **Income diversity**: Each age band has a Census-derived income distribution (e.g., 21-29: 35% low, 45% middle, 15% upper-middle, 5% high)
- **Housing diversity**: Income-correlated housing distribution (e.g., low income: 60% HDB 1-3, 35% HDB 4-5, 4% Condo, 1% Landed)
- **31 constituencies**: All GE2025 GRCs and SMCs represented
- **Population weighting**: Each persona carries a `weight` field = `GRC_population × race_pct × age_weight / personas_in_segment`, so aggregation reflects actual demographic proportions

### How persona generation works (`demographics.py`)
```
For each GRC (31):
  For each race (4):
    Skip if race_pct < 2% in this GRC
    For each age band (4):
      Compute segment share = race_pct × age_weight
      Generate N personas (proportional to GRC population budget)
      Each persona gets:
        - Income tier: randomly drawn from Census distribution for that age band
        - Housing type: randomly drawn from income-correlated distribution
        - Occupation: deterministic from income tier (hash-based)
        - Risk appetite: 40% age + 35% income + 25% housing
        - Weight: population representation
```

The determinism is seeded on `md5(grc + race + age + index)` so results are reproducible.

### How to verify
```bash
cd polisim-repo && source venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'backend')
from demographics import build_personas
personas = build_personas(100)
print(f'Total: {len(personas)}')
for key in ['race', 'age', 'income', 'housing']:
    vals = {}
    for p in personas:
        vals[p[key]] = vals.get(p[key], 0) + 1
    print(f'{key}: {vals}')
"
```

---

## 2. How to backtest against GE2025 election results?

### Data
GE2025 results are already in `data/ge_results.csv` (32 constituencies, all parties, vote counts and percentages). GRC profiles in `data/grc_profiles.json` are mapped to GE2025 electoral boundaries.

### Running the backtest

**Via API:**
```bash
curl "http://localhost:8000/api/backtest?ge_year=2025&agents=200"
```

**Via CLI:**
```bash
cd polisim-repo && source venv/bin/activate
cd backend && python3 backtest.py 2025
```

**Via code:**
```python
from backtest import run_backtest
result = run_backtest(ge_year=2025, use_mock=True, target_agents=200)
```

### What it does (`backtest.py`)
1. Load GE2025 results from CSV → build `{constituency: PAP_vote_pct}` lookup
2. Build 200 personas from `demographics.py`
3. Run mock (or real LLM) agent evaluation for each persona
4. Compute market bets per agent
5. Apply 3 rounds of contagion propagation
6. Aggregate predicted support % per GRC
7. Compare against actual PAP vote share
8. Compute metrics: MAE, correlation, correct winner calls, market price

### Constituency matching
Previous: fragile substring matching that could cross-match ("Jurong" matching "Jurong Central" AND "Jurong East-Bukit Batok").

Current: Two-pass matching in `real_data._match_constituency()`:
1. **Exact**: normalize both names (strip GRC/SMC, uppercase, replace hyphens with spaces) and compare
2. **Fuzzy**: one-contains-the-other with similarity threshold >50% (length ratio)

### Current results (mock mode)

| Metric | GE2020 | GE2025 |
|--------|--------|--------|
| MAE | 16.5% | 19.3% |
| Correct calls | 9/14 (64.3%) | 12/18 (66.7%) |
| Correlation | 0.235 | -0.011 |
| Matched constituencies | 14 | 18 |

The mock model uses static sentiment weights — it doesn't reason about actual policy provisions. With real LLM calls, predictions should improve significantly because agents evaluate actual provisions through their demographic lens.

### How to improve accuracy
1. **Use real LLM calls** (`use_mock=False`) — agents reason about actual policy positions
2. **Increase agent count** — 500+ agents gives better GRC coverage
3. **Calibrate sentiment weights** in `mock_mode.py` to match historical voting patterns more closely
4. **Add GRC-specific context** to agent prompts (incumbent party, local issues, past voting patterns)
5. **Integrate live sentiment** from TinyFish to ground agents in real public opinion

---

## 3. How does the contagion model work?

### The model: Group-based O(n) propagation

Instead of comparing every agent pair (O(n²) — 10,000 comparisons for 100 agents), we compute **group means** and then blend each agent's score with their group influences.

### Step by step (each round)

**Step 1: Compute group means (O(n))**
```
For each agent:
  Add weighted score to:
    - GRC group (e.g., "Ang Mo Kio GRC")
    - Race group (e.g., "Chinese")
    - Race×Age group (e.g., "Chinese, 30-44")
    - Housing group (e.g., "HDB 4-5 Room")
  Also compute global mean (for social media effect)
```

**Step 2: Compute per-agent influence (O(n × 5))**
```
For each agent:
  weighted_influence =
    0.10 × GRC_group_mean           (neighborhood effect)
  + 0.15 × Race_group_mean          (ethnic community ties)
  + 0.10 × Race×Age_group_mean      (family-like bonds)
  + 0.08 × Housing_group_mean       (class solidarity)
  + social_media_weight × GLOBAL_mean  (cross-GRC info flow)

  social_media_weight varies by age:
    21-29: 0.12 (high social media exposure)
    30-44: 0.08
    45-59: 0.04
    60+:   0.02 (low exposure)
```

**Step 3: Blend own score with group influence**
```
new_score = 0.7 × own_score + 0.3 × normalized_influence
```

The 0.7 "damping factor" means agents are 70% stubborn — they mostly keep their own opinion, but 30% shifts toward their social circles each round.

**Step 4: Update labels and market bets**
```
score > 0.33  → "support"
score < -0.33 → "reject"
else          → "neutral"

Recalculate conviction_bet with slightly boosted confidence
(social proof increases conviction, capped at +5% per round)
```

### Why group-based?
- The influence model uses **categorical features** (race, GRC, housing, age band) — these are naturally group-based
- O(n) per round vs O(n²) — scales to 500+ agents without performance issues
- Each agent still evolves uniquely because they belong to different combinations of groups
- The "ripple effect" is preserved: sentiment shifts cascade round-by-round as group means update

### In prediction market terms
Each contagion round is a "market round" where information propagates:
- Round 0: Agents form initial opinions (individual bets placed)
- Round 1: Local information (GRC, race) propagates — "my neighbors think..."
- Round 2: Broader information cascades (housing class, wider race community)
- Round 3: Market approaches equilibrium (social media amplifies consensus)

### Configurable parameters
All in `backend/config.py` → `contagion` dict:
```python
"contagion": {
    "damping": 0.70,       # agent stubbornness (0.5 = very influenceable, 0.9 = very stubborn)
    "rounds": 3,           # number of propagation rounds
    "group_weights": {
        "grc": 0.10,       # neighborhood
        "race": 0.15,      # ethnic community
        "race_age": 0.10,  # family bonds
        "housing": 0.08,   # class solidarity
    },
    "social_media_by_age": {
        "21-29": 0.12,     # young = high social media
        ...
    },
}
```

---

## 4. Where is TinyFish used? How does live data adjust probabilities?

### Where TinyFish is integrated (`scraper.py`)

Three scraping functions:

| Function | Source | Returns |
|----------|--------|---------|
| `scrape_sg_sentiment(topic)` | Reddit r/singapore + HardwareZone EDMW | `[{source, text, sentiment, engagement}]` |
| `scrape_policy_news(topic)` | Channel NewsAsia | `[{title, date, summary, url}]` |
| `scrape_demographics_live()` | SingStat population page | `{total_population, citizens, ...}` |

### How live sentiment adjusts probabilities

During WebSocket simulation (`main.py`), after initial agent evaluation:

1. TinyFish scrapes Reddit and HWZ for posts related to the policy topic
2. Each post has a `sentiment` (positive/negative/neutral) and `engagement` score
3. The live sentiment becomes an "external market signal" — like real trades entering the prediction market from outside
4. **Adjustment formula** (`market.py:adjust_with_live_sentiment`):
   ```
   signal = Σ(engagement × sentiment_score) / Σ(engagement)
   // signal normalized to [-1, 1]

   adjusted_price = 0.85 × agent_market_price + 0.15 × (signal + 1) / 2
   ```
5. The 15% live weight means TinyFish can shift the market price by up to ±7.5%
6. This adjustment **decays** over contagion rounds: `live_adjustment × 0.7^round`
   - Round 1: 70% of live adjustment applied
   - Round 2: 49%
   - Round 3: 34%
   - Rationale: as the agent market reaches equilibrium, the external signal matters less

### When TinyFish is NOT available
Falls back gracefully — `scraper.py` returns empty lists, `main.py` skips the adjustment. The simulation works entirely on simulated agents.

### Frontend display
The `SidePanel.jsx` shows a "Live Sentiment" card when TinyFish data arrives, with:
- Number of sources scraped
- Price adjustment (e.g., "+2.3%")
- Top 3 scraped posts with sentiment indicators

---

## 5. How to extend for different geographical regions?

### Architecture: Region as a config dict

All Singapore-specific data lives in `backend/config.py` in a single `SINGAPORE` dict. To add a new region:

### Step 1: Create a config dict

```python
# In config.py
HONG_KONG = {
    "name": "Hong Kong",
    "currency": "HKD",
    "races": ["Chinese", "Filipino", "Indonesian", "South Asian", "Others"],
    "age_bands": ["18-29", "30-44", "45-59", "60+"],
    "income_tiers": [
        {"label": "<HK$15K", "tier": "low", "range": (0, 15000)},
        {"label": "HK$15-30K", "tier": "middle", "range": (15000, 30000)},
        ...
    ],
    "housing_types": ["Public Rental", "HOS", "Private Flat", "Village House"],
    "occupations": { ... },
    "concerns": { ... },
    "risk_appetite_by_age": { ... },
    "income_distribution_by_age": { ... },
    "housing_distribution_by_income": { ... },
    "age_band_weights": { ... },
    "profiles_file": "hk_constituency_profiles.json",
    "contagion": { ... },
}

ACTIVE_REGION = HONG_KONG  # ← switch here
```

### Step 2: Create constituency data

Place `data/hk_constituency_profiles.json`:
```json
{
  "Hong Kong Island": {
    "pop": 1200000,
    "chinese": 0.92,
    "filipino": 0.03,
    ...
    "seats": 6,
    "center": [22.28, 114.15]
  },
  ...
}
```

### Step 3: Update frontend map

In `MapView.jsx`:
- Change `SG_CENTER` to new coordinates
- Load a different GeoJSON for constituency boundaries
- Update `ED_TO_PROFILE` mapping

### Step 4 (optional): Add election data

Place CSV files in `/data/` following the same format as `ge_results.csv` and `voter_turnout.csv`. Update `config.py` → `ge_results_file`.

### What's region-agnostic (no changes needed)
- `market.py` — prediction market model works for any geography
- `contagion_v2.py` — reads group weights from config
- `agent_engine.py` — persona prompt is generic
- `main.py` — all endpoints work with any region config
- Frontend components (except MapView) — work with any GRC names

---

## 6. Scaling to more agents

### Current scaling

| Agents | Mock mode | Real LLM | Memory |
|--------|-----------|----------|--------|
| 100 | <1s | ~10s | ~5MB |
| 200 | <2s | ~15s | ~10MB |
| 500 | <5s | ~30s | ~25MB |

### How it scales
- **Demographics**: O(GRCs × races × ages) to generate, O(n) to trim
- **Agent evaluation**: Bounded concurrency (10-30 concurrent OpenAI calls, auto-scaled)
- **Contagion**: O(n) per round (group-based, not pairwise)
- **Market computation**: O(n) per price calculation

### Bottleneck
OpenAI API latency, not compute. With 500 agents at 30 concurrent calls, that's ~17 batches × 2s per call ≈ 34s. Mock mode is instant.

### WebSocket param
```javascript
// Frontend
sim.connect(policyId, 200);  // request 200 agents

// Or direct WebSocket URL
ws://localhost:8000/ws/simulate/{id}?agents=200
```

---

## 7. Prediction Market Model

### Why market > polling

| Polling | Prediction Market |
|---------|------------------|
| "Do you support this?" | "How much would you bet on this passing?" |
| Equal weight to every response | Self-interested: conviction × risk appetite |
| No cost to lying | "Skin in the game" — bet reveals true belief |
| Aggregates to simple % | Market clearing price = implied probability |
| Static snapshot | Price evolves as information cascades |

### How it works (`market.py`)

**Each agent has:**
- `risk_appetite` (0.0–1.0): derived from demographics
  ```
  risk = 0.40 × age_factor + 0.35 × income_factor + 0.25 × housing_factor
  ```
  Example: 25yo PME in condo → risk 0.75. 65yo retiree in HDB 3-room → risk 0.30.

- `conviction_bet` = risk_appetite × confidence × population_weight
  - This is how many virtual tokens the agent stakes

- `yes_bet` / `no_bet`: direction of the bet
  - Support → all tokens on YES
  - Reject → all tokens on NO
  - Neutral → split 40% YES / 60% NO (slight status quo bias)

**Market clearing price:**
```
price = Σ(yes_bets) / Σ(yes_bets + no_bets)
```
This is the implied probability of the policy passing. If price = 0.72, the market says 72% chance of passing.

**Price evolution:**
- Round 0: Initial bets placed (pre-contagion)
- Round 1-3: Social contagion shifts sentiments and confidence → bets update → price moves
- Each round, confidence gets a small social-proof boost (capped at +5%)
- TinyFish live sentiment acts as external trades (±15% weight, decaying)

**Frontend display:**
- Hero metric: market clearing price (e.g., "74.9%")
- Price evolution mini-chart (bar chart across rounds)
- Volume: total tokens in the market
- Per-GRC market prices on the map sidebar
- Individual agent bet amounts in the live feed

### Extending to real monetary bets

The virtual token system maps directly to real currency:
1. Replace `weight` with an actual budget (e.g., SGD 100 per agent)
2. `conviction_bet` becomes real SGD staked
3. Market price becomes a tradeable contract price
4. Settlement: if policy passes, YES bettors get paid; if fails, NO bettors get paid
5. The contagion model becomes information cascading in a real prediction market

This is exactly how platforms like Polymarket, Kalshi, and Metaculus work — Polysim simulates the same mechanism with AI agents instead of real traders.

### Vote as a bet

In the Polysim framing, every vote is a bet:
- **Currency**: marginal utility (not SGD)
- **Stake**: how much the policy outcome affects your life
- **Risk appetite**: willingness to commit (young + rich = bolder)
- **Social contagion**: information propagation that shifts the market
- **Equilibrium**: the price where buy/sell pressure balances = predicted outcome

This reframes "61% support" as "market price $0.61" — same data, stronger signal, better story.

---

## 8. TinyFish integration details

### What TinyFish does
Cloud browser automation. Accepts a URL + natural language goal, runs a real Chromium browser, returns structured JSON. No CSS selectors needed.

### Current usage in Polysim

| Function | Source | Profile | Goal |
|----------|--------|---------|------|
| `scrape_sg_sentiment` | Reddit r/singapore | stealth | Extract top 10 posts about {topic} with sentiment |
| `scrape_sg_sentiment` | HWZ EDMW | stealth | Extract up to 10 threads about {topic} with sentiment |
| `scrape_policy_news` | CNA search | lite | Extract top 5 news articles about {topic} |
| `scrape_demographics_live` | SingStat | lite | Extract population statistics |

### How it connects to the simulation

1. User uploads policy → provisions extracted
2. WebSocket simulation starts
3. Agents evaluate provisions (Phase 1)
4. **TinyFish scrapes live sentiment** about the first provision's title (Phase 1.5)
5. Live sentiment adjusts market price by up to ±7.5%
6. Contagion rounds proceed with live adjustment applied (decaying each round)
7. Frontend shows live sentiment card with scraped sources

### Fallback behavior
- No TINYFISH_API_KEY → returns `{"fallback": True}`, simulation proceeds without adjustment
- API rate limit (429) → returns fallback
- Timeout (60s) → returns fallback
- In mock mode → TinyFish is skipped entirely

### Configuration
```
TINYFISH_API_KEY=tf_...        # in .env
TINYFISH_BASE_URL=https://api.tinyfish.ai  # in .env (optional)
```

---

## 9. Eval / benchmarking

### Running the full eval suite

```bash
cd polisim-repo && source venv/bin/activate
python3 eval/benchmark.py
```

### What it checks

| Check | Metric | Pass threshold |
|-------|--------|---------------|
| Demographic differentiation (race) | Variance in mean sentiment across 4 races | > 0.05 |
| Demographic differentiation (age) | Variance in mean sentiment across 4 ages | > 0.05 |
| Vote coherence | for% + against% + undecided% = 100% | Within 1% |
| Market model validity | Price between 0.01-0.99, volume > 0, bettors >= 5 | All true |
| Backtest accuracy (GE2025) | MAE < 25%, correct calls > 50% | Both true |

### Current benchmark results (mock mode)

```
Demographic Differentiation
  Races: 4 | Race spread: 0.467 PASS
  Ages:  4 | Age spread:  0.450 PASS

Vote Coherence: PASS

Market Model
  Price: 0.8833 (88.3%) | Volume: 554383 | Bettors: 120
  Valid: PASS

Backtest GE2025
  MAE: 19.3% PASS
  Correct calls: 12/18 (66.7%) PASS
  Correlation: -0.011
```
