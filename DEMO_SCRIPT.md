# Polisim Demo Script

This repo currently has two different "demo" concepts:

- `demo.sh` starts the backend and frontend locally.
- This file is the presenter script for showing the product clearly.

## What The Product Actually Demos

Polisim is strongest when presented as:

1. A policy or scenario is turned into structured provisions.
2. A weighted population of Singapore personas evaluates it.
3. Those views are converted into a prediction-market-style price.
4. Live public sentiment can shift the starting market.
5. Three contagion rounds show how opinion spreads socially.
6. The UI ends with a final pass/fail call plus constituency drilldown.

That is the real demo. Do not frame the current app as a general-purpose geography simulator yet. The active UI is still Singapore-first.

## Review Of Existing `demo.sh`

Current strengths:

- It bootstraps backend and frontend with one command.
- It creates `.env` from `.env.example` if missing.
- It prints the correct local URLs after startup.

Current gaps:

- It is a launcher, not a speaking script.
- It installs dependencies on every run, which adds delay and demo risk.
- It does not check whether API keys are valid.
- It does not tell the presenter which user path is most reliable.
- It does not use the bundled demo samples even though the backend ships them.

Conclusion: keep `demo.sh` as a convenience runner, but do not treat it as the actual demo narrative.

## Recommended Demo Path

Use this order in a live demo:

1. Start from the `Any Scenario` tab.
2. Use a housing or transport scenario because the data and UI are Singapore-centric.
3. Show the AI interpretation screen first.
4. Run the simulation.
5. Narrate the pipeline in this order:
   - TinyFish sentiment scan
   - agent stream
   - initial market price
   - contagion rounds
   - final call
6. Click 1-2 constituencies on the map.
7. Change one lever and rerun once.

Avoid starting with region configuration unless you specifically want to show unfinished exploratory functionality. That stage is disabled in the active frontend anyway.

## Demo Setup

From repo root:

```bash
cd /Users/tian/GitHub/polisim/polisim-repo
./demo.sh
```

Open:

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

Before presenting, check:

- `GET /api/health` returns `status: ok`
- whether `mock_mode` is `true` or `false`

Talking point:

- If `mock_mode` is `false`, agent reasoning uses OpenAI.
- If `mock_mode` is `true`, the full product flow still works, but agent opinions are deterministic mock outputs.

## Primary 4-5 Minute Demo Script

### 1. Open

Say:

> Polisim is a policy simulation market. Instead of asking one model for a single answer, we generate a representative population, let agents evaluate the proposal from their own incentives, convert those opinions into market bets, then watch how the price changes after social contagion.

### 2. Enter A Scenario

In `Any Scenario`, paste:

```text
Singapore increases first-time buyer housing grants, adds extra BTO launches in non-mature estates, and gives young families more ballot priority over the next 12 months.
```

Say:

> I can start from messy natural language. The system reframes it into a prediction question and extracts the provisions agents will evaluate.

Click `Interpret Scenario`.

### 3. Show The Interpretation

Pause on the interpretation card.

Say:

> The first step is not simulation. It is structuring the problem: a title, a yes/no market frame, and concrete provisions. That gives every downstream agent the same policy object to reason over.

Point out:

- title
- YES definition
- NO definition
- extracted provisions

Click `Run Simulation`.

### 4. Narrate The Live Simulation

As the run starts, say:

> Now the backend builds weighted personas from Singapore constituency and demographic data, then streams each evaluation back as soon as it completes.

When the TinyFish card appears, say:

> Before the market settles, we can also pull live public sentiment and use it as a bounded adjustment to the initial price.

When agent cards begin streaming, say:

> Each card is one synthetic voter-trader with a constituency, demographic profile, sentiment, confidence, and implied bet size.

When the first market price appears, say:

> This is the first clearing price before social contagion. At this point we have a market from individual judgment alone.

When contagion rounds start, say:

> Then we run three contagion rounds. Agents are not independent anymore; they are influenced by constituency, segment, housing, and age-linked social exposure. This is where second-order opinion shifts show up.

### 5. Land The Result

When the final call appears, say:

> The output is not just a headline probability. I can inspect where the support is concentrated geographically and demographically, and which pockets resist the policy.

Click one stronger constituency and one weaker constituency on the map.

Say:

> That lets us drill from national market price down to constituency-level composition and the underlying agent rationales.

### 6. Show One Counterfactual

Use one lever adjustment and rerun.

Suggested narration:

> The useful product behavior is not only prediction. It is counterfactual testing. I can modify a lever in the policy package and rerun the same population to see whether support strengthens or weakens.

## Backup Script If Interpretation Is Slow

Use the `Paste Policy` tab and paste a short policy block from [`data/demo_policy_samples.json`](/Users/tian/GitHub/polisim/polisim-repo/data/demo_policy_samples.json).

Best samples:

- `housing-grant-boost`
- `fare-freeze`
- `preschool-subsidy`

Why these are safer:

- they are concrete
- they map cleanly to Singapore household concerns
- they produce intuitive constituency reactions

## Backup Script If APIs Fail

If OpenAI or TinyFish is unavailable:

1. Keep the same flow.
2. Explicitly say the app is in offline/mock mode.
3. Emphasize product architecture and interaction design, not model quality.

Use this line:

> The live demo is running in fallback mode, so the reasoning quality is simplified, but the full system pipeline is still the same: policy parsing, persona generation, market formation, contagion, and geographic drilldown.

## What To Avoid Saying

Avoid these claims because the current code does not fully support them:

- "This already supports any geography end to end."
- "The map changes with custom region config."
- "This is using real live data at every step."
- "The displayed agent count is exactly the requested count."

## Clear One-Sentence Pitch

Use this if you need a tight close:

> Polisim turns a policy proposal into a live market of simulated citizens, then shows how support moves across demographics and constituencies before and after social contagion.
