import os
import json
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from policy_parser import parse_policy_pdf, parse_policy_text
from agent_engine import run_simulation, stream_agent_results
from contagion_v2 import propagate_sentiment_v2
from demographics import build_personas, load_grc_profiles
from levers import apply_lever, LEVER_DEFINITIONS
from mock_mode import mock_parse_provisions, mock_agent_response
from backtest import run_backtest
from real_data import get_enriched_grc_profiles, load_pop_ethnicity, load_income_distribution
from market import compute_agent_bet, compute_market_price, compute_market_by_grc, adjust_with_live_sentiment
from scraper import scrape_sg_sentiment
from config import get_config
from scenario_interpreter import interpret_scenario
from config_generator import generate_segment_config, stream_research_and_generate, get_stored_config

# Mock mode: enabled when no OpenAI key is set or key is the placeholder
_oai_key = os.getenv("OPENAI_API_KEY", "")
MOCK_MODE = not _oai_key or _oai_key.startswith("sk-...") or len(_oai_key) < 20

app = FastAPI(title="Polysim API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory store
simulations = {}

# Default agent count — configurable via query param
DEFAULT_AGENT_COUNT = 200


@app.get("/api/health")
async def health():
    cfg = get_config()
    return {
        "status": "ok",
        "project": "polysim",
        "mock_mode": MOCK_MODE,
        "region": cfg["name"],
        "default_agents": DEFAULT_AGENT_COUNT,
    }


@app.post("/api/upload")
async def upload_policy(file: UploadFile = File(...)):
    """Parse uploaded PDF or text file into structured provisions."""
    content = await file.read()
    if len(content) > 10_000_000:  # 10MB limit
        return {"error": "File too large (max 10MB)"}

    filename = file.filename or ""

    if MOCK_MODE:
        provisions = mock_parse_provisions(content.decode("utf-8", errors="ignore")[:200])
    elif filename.lower().endswith(".pdf"):
        provisions = await parse_policy_pdf(content)
    else:
        text = content.decode("utf-8", errors="ignore")
        provisions = await parse_policy_text(text)

    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {
        "provisions": provisions, "results": [], "status": "parsed",
        "scenario_frame": None, "region_config": None,
    }
    return {"policy_id": policy_id, "provisions": provisions}


@app.post("/api/upload-text")
async def upload_policy_text(body: dict):
    """Parse raw policy text. Send {"text": "your policy here"}."""
    text = body.get("text", "")
    if not text:
        return {"error": "No text provided"}
    if len(text) > 50000:
        return {"error": "Text too long (max 50000 chars)"}

    if MOCK_MODE:
        provisions = mock_parse_provisions(text[:200])
    else:
        provisions = await parse_policy_text(text)

    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {
        "provisions": provisions, "results": [], "status": "parsed",
        "scenario_frame": None, "region_config": None,
    }
    return {"policy_id": policy_id, "provisions": provisions}


@app.post("/api/interpret-scenario")
async def interpret_scenario_endpoint(body: dict):
    """
    Convert any NL scenario into structured simulation input.
    Send {"text": "...", "region": "optional region name"}.
    Returns interpreted frame + policy_id ready for simulation.
    """
    text = body.get("text", "").strip()
    if not text:
        return {"error": "No scenario text provided"}

    cfg = get_config()
    region_name = body.get("region") or cfg.get("name", "the region")

    frame = await interpret_scenario(text, region_name=region_name)

    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {
        "provisions": frame["provisions"],
        "results": [],
        "status": "parsed",
        "scenario_frame": frame,
        "region_config": None,
    }
    return {"policy_id": policy_id, "provisions": frame["provisions"], "frame": frame}


@app.post("/api/configure-region")
async def configure_region(body: dict):
    """
    Generate a demographic segment config from a NL description (non-streaming).
    Send {"description": "..."}. Returns config override.
    """
    description = body.get("description", "").strip()
    if not description:
        return {"error": "No description provided"}

    config = await generate_segment_config(description)
    config_id = str(uuid.uuid4())
    simulations[f"config:{config_id}"] = config
    return {"config_id": config_id, "config": config}


@app.post("/api/configure-region/stream")
async def configure_region_stream(request: Request):
    """
    Streaming SSE endpoint — agentic TinyFish research + GPT-4o synthesis.
    Send {"description": "..."}. Streams research events as SSE.

    Event types: plan | search_start | search_result | narrate | synthesis_start | complete | error
    """
    body = await request.json()
    description = body.get("description", "").strip()
    if not description:
        async def err():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No description provided'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    async def event_stream():
        async for event in stream_research_and_generate(description):
            yield f"data: {json.dumps(event)}\n\n"
            # Small flush pause so client receives events incrementally
            await asyncio.sleep(0)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
        },
    )


@app.post("/api/apply-config/{policy_id}")
async def apply_config(policy_id: str, body: dict):
    """
    Attach a region config override to an existing simulation.
    Send {"config_id": "..."} or {"config": {...}}.
    """
    if policy_id not in simulations:
        return {"error": "Policy not found"}

    if "config_id" in body:
        cid = body["config_id"]
        # Check both in-memory stores (legacy simulations dict + new config store)
        config = get_stored_config(cid) or simulations.get(f"config:{cid}")
        if not config:
            return {"error": "Config not found"}
    elif "config" in body:
        config = body["config"]
    else:
        return {"error": "Provide config_id or config"}

    simulations[policy_id]["region_config"] = config
    return {"ok": True}


@app.get("/api/demographics")
async def get_demographics(ge_year: int = 2025):
    """Return enriched GRC profiles with real Census + election data."""
    try:
        profiles = get_enriched_grc_profiles(ge_year)
    except Exception:
        profiles = load_grc_profiles()
    return {"grcs": profiles, "ge_year": ge_year}


@app.get("/api/backtest")
async def backtest(ge_year: int = 2025, agents: int = 200):
    """
    Run backtest against actual election results.
    Supports GE2020 and GE2025. Returns market price + per-constituency accuracy.
    """
    agents = max(50, min(500, agents))
    result = run_backtest(ge_year=ge_year, use_mock=MOCK_MODE, target_agents=agents)
    return result


@app.post("/api/gerrymander")
async def gerrymander_analysis(request: dict = None):
    """Analyze gerrymandering opportunities based on demographic + sentiment data."""
    if request is None:
        request = {}

    target_party = request.get("target_party", "PAP")
    ge_year = request.get("ge_year", 2025)
    profiles = get_enriched_grc_profiles(ge_year)
    ethnicity = load_pop_ethnicity()
    income = load_income_distribution()

    personas = build_personas(target_count=200)
    results = [mock_agent_response(p) for p in personas]
    for r in results:
        compute_agent_bet(r)
    for rnd in range(3):
        results = propagate_sentiment_v2(results, rnd)

    # Aggregate by GRC with market prices
    grc_support = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grc_support:
            grc_support[grc] = {"support_w": 0, "total_w": 0, "yes": 0, "no": 0}
        w = r["persona"].get("weight", 1)
        if r["sentiment"] == "support":
            grc_support[grc]["support_w"] += w
        grc_support[grc]["total_w"] += w
        grc_support[grc]["yes"] += r.get("yes_bet", 0)
        grc_support[grc]["no"] += r.get("no_bet", 0)

    analysis = []
    for grc_name, profile in profiles.items():
        support_data = grc_support.get(grc_name, {"support_w": 0, "total_w": 1, "yes": 0, "no": 1})
        predicted_support = support_data["support_w"] / support_data["total_w"] * 100
        mkt_total = support_data["yes"] + support_data["no"]
        market_price = support_data["yes"] / mkt_total if mkt_total > 0 else 0.5

        ge_key = f"ge{ge_year}"
        ge_data = profile.get(ge_key, {})
        actual_pap = 0
        if ge_data.get("results"):
            pap = next((p for p in ge_data["results"] if p["party"] == "PAP"), None)
            if pap:
                actual_pap = pap["vote_percentage"] * 100

        margin = ge_data.get("margin", 1.0) * 100
        vulnerability = "safe" if margin > 20 else ("swing" if margin > 10 else "vulnerable")

        leverage_factors = []
        if profile.get("chinese", 0) > 0.75:
            leverage_factors.append("high Chinese concentration — stable PAP base")
        if profile.get("malay", 0) > 0.18:
            leverage_factors.append("significant Malay population — sensitive to housing/cost policies")
        if profile.get("indian", 0) > 0.14:
            leverage_factors.append("significant Indian population — employment concerns")

        suggestion = None
        if target_party == "PAP":
            if vulnerability == "vulnerable" and predicted_support < 55:
                suggestion = f"Consider merging with adjacent safe constituency. Current margin: {margin:.1f}%"
            elif vulnerability == "safe" and predicted_support > 70:
                suggestion = f"Surplus votes ({predicted_support:.0f}%) could be redistributed to shore up swing seats."
        else:
            if vulnerability == "swing":
                suggestion = f"Target for opposition concentration. Margin only {margin:.1f}%."

        analysis.append({
            "constituency": grc_name,
            "seats": profile.get("seats", 5),
            "predicted_support_pct": round(predicted_support, 1),
            "market_price": round(market_price, 4),
            f"actual_pap_{ge_year}_pct": round(actual_pap, 1),
            f"margin_{ge_year}_pct": round(margin, 1),
            "vulnerability": vulnerability,
            "chinese_pct": round(profile.get("chinese", 0) * 100, 1),
            "malay_pct": round(profile.get("malay", 0) * 100, 1),
            "leverage_factors": leverage_factors,
            "redistricting_suggestion": suggestion,
        })

    analysis.sort(key=lambda x: x.get(f"margin_{ge_year}_pct", 100))

    vulnerable_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "vulnerable")
    swing_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "swing")
    safe_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "safe")

    return {
        "target_party": target_party,
        "ge_year": ge_year,
        "analysis": analysis,
        "summary": {
            "total_constituencies": len(analysis),
            "vulnerable_seats": vulnerable_seats,
            "swing_seats": swing_seats,
            "safe_seats": safe_seats,
            "key_battlegrounds": [a["constituency"] for a in analysis if a["vulnerability"] != "safe"][:5],
        }
    }


@app.websocket("/ws/simulate/{policy_id}")
async def simulate(websocket: WebSocket, policy_id: str):
    """
    Stream simulation: agents -> contagion (market rounds) -> market prediction.

    Query params (via URL):
    - agents: number of agents to simulate (default 100, max 500)
    """
    await websocket.accept()

    if policy_id not in simulations:
        await websocket.send_json({"type": "error", "message": "Policy not found"})
        await websocket.close()
        return

    sim = simulations[policy_id]
    provisions = sim["provisions"]
    scenario_frame = sim.get("scenario_frame")
    region_config = sim.get("region_config")

    # Parse agent count from query string (or use default)
    qs = websocket.query_params
    agent_count = min(500, max(20, int(qs.get("agents", DEFAULT_AGENT_COUNT))))
    personas = build_personas(target_count=agent_count, config=region_config)
    total_agents = len(personas)

    try:
        # Send config info
        await websocket.send_json({
            "type": "config",
            "data": {"total_agents": total_agents, "contagion_rounds": 3}
        })

        # Phase 1: Stream individual agent results
        all_results = []
        if MOCK_MODE:
            for persona in personas:
                result = mock_agent_response(persona)
                compute_agent_bet(result)
                all_results.append(result)
                await websocket.send_json({"type": "agent_result", "data": result})
                await asyncio.sleep(0.03)
        else:
            async for result in stream_agent_results(
                personas, provisions,
                scenario_frame=scenario_frame,
                region_config=region_config,
            ):
                compute_agent_bet(result)
                all_results.append(result)
                await websocket.send_json({"type": "agent_result", "data": result})

        sim["results"] = all_results

        # Compute initial market price (pre-contagion)
        initial_market = compute_market_price(all_results)
        await websocket.send_json({
            "type": "market_update",
            "round": 0,
            "data": initial_market,
        })

        # Phase 1.5: TinyFish live sentiment adjustment (if available)
        live_adjustment = 0.0
        if not MOCK_MODE:
            try:
                policy_topic = provisions[0]["title"] if provisions else "government policy"
                live_sentiments = await scrape_sg_sentiment(policy_topic)
                if live_sentiments:
                    adjusted_price = adjust_with_live_sentiment(
                        initial_market["market_price"], live_sentiments
                    )
                    live_adjustment = adjusted_price - initial_market["market_price"]
                    await websocket.send_json({
                        "type": "live_sentiment",
                        "data": {
                            "sources_scraped": len(live_sentiments),
                            "price_adjustment": round(live_adjustment, 4),
                            "adjusted_price": adjusted_price,
                            "sentiments": live_sentiments[:5],  # send top 5
                        }
                    })
            except Exception:
                pass  # TinyFish is optional

        # Phase 2: Contagion / market rounds (3 rounds)
        price_history = [{"round": 0, "market_price": initial_market["market_price"]}]

        for round_num in range(3):
            all_results = propagate_sentiment_v2(all_results, round_num)
            grc_agg = aggregate_by_grc(all_results)
            round_market = compute_market_price(all_results)

            # Apply live sentiment adjustment if we got one
            if live_adjustment != 0:
                decay = 0.7 ** (round_num + 1)  # live signal decays over rounds
                round_market["market_price"] = min(0.99, max(0.01,
                    round_market["market_price"] + live_adjustment * decay
                ))
                round_market["implied_probability_pct"] = round(round_market["market_price"] * 100, 1)

            price_history.append({
                "round": round_num + 1,
                "market_price": round_market["market_price"],
            })

            await websocket.send_json({
                "type": "contagion_round",
                "round": round_num,
                "data": grc_agg,
                "market": round_market,
            })
            await asyncio.sleep(0.5)

        # Phase 3: Final market prediction
        final_market = compute_market_price(all_results)
        vote = compute_vote_prediction(all_results)

        await websocket.send_json({
            "type": "vote_prediction",
            "data": {
                **vote,
                "market": final_market,
                "price_history": price_history,
            }
        })
        await websocket.send_json({"type": "complete"})

    except WebSocketDisconnect:
        pass


@app.post("/api/adjust/{policy_id}")
async def adjust(policy_id: str, lever: str, value: float):
    """Apply lever adjustment, return new sim ID for re-run."""
    if policy_id not in simulations:
        return {"error": "Policy not found"}
    if lever not in LEVER_DEFINITIONS:
        return {"error": f"Unknown lever: {lever}"}

    defn = LEVER_DEFINITIONS[lever]
    value = max(defn["min"], min(defn["max"], value))

    new_provisions = apply_lever(simulations[policy_id]["provisions"], lever, value)
    new_id = str(uuid.uuid4())
    simulations[new_id] = {"provisions": new_provisions, "results": [], "status": "adjusted"}
    return {"policy_id": new_id, "provisions": new_provisions}


def aggregate_by_grc(results: list) -> dict:
    """Aggregate agent results by GRC with market prices."""
    grcs = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grcs:
            grcs[grc] = {"support": 0, "neutral": 0, "reject": 0, "total": 0,
                         "yes_bets": 0, "no_bets": 0, "agents": []}
        w = r["persona"].get("weight", 1)
        grcs[grc][r["sentiment"]] += w
        grcs[grc]["total"] += w
        grcs[grc]["yes_bets"] += r.get("yes_bet", 0)
        grcs[grc]["no_bets"] += r.get("no_bet", 0)
        grcs[grc]["agents"].append(r)

    for grc, data in grcs.items():
        t = data["total"] or 1
        data["support_pct"] = round(data["support"] / t * 100, 1)
        data["neutral_pct"] = round(data["neutral"] / t * 100, 1)
        data["reject_pct"] = round(data["reject"] / t * 100, 1)
        bet_total = data["yes_bets"] + data["no_bets"]
        data["market_price"] = round(data["yes_bets"] / bet_total, 4) if bet_total > 0 else 0.5
    return grcs


def compute_vote_prediction(results: list) -> dict:
    """Vote aggregation + market model from agent results."""
    votes = {"for": 0, "against": 0, "undecided": 0, "total": 0}
    for r in results:
        w = r["persona"].get("weight", 1)
        vi = r.get("vote_intent", "undecided")
        votes[vi] = votes.get(vi, 0) + w
        votes["total"] += w
    t = votes["total"] or 1
    return {
        "for_pct": round(votes["for"] / t * 100, 1),
        "against_pct": round(votes["against"] / t * 100, 1),
        "undecided_pct": round(votes["undecided"] / t * 100, 1),
        "total_agents": len(results),
        "call": "PASS" if votes["for"] / t > 0.5 else "FAIL",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
