import os, json, uuid, asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from policy_parser import parse_policy_pdf, parse_policy_text
from agent_engine import run_simulation, stream_agent_results
from contagion_v2 import propagate_sentiment_v2 as propagate_sentiment, propagate_sentiment_v2
from demographics import build_personas, load_grc_profiles
from levers import apply_lever
from mock_mode import mock_parse_provisions, mock_agent_response
from backtest import run_backtest
from real_data import get_enriched_grc_profiles, load_pop_ethnicity, load_income_distribution

# Mock mode: enabled when no OpenAI key is set or key is the placeholder
_oai_key = os.getenv("OPENAI_API_KEY", "")
MOCK_MODE = not _oai_key or _oai_key == "sk-..." or len(_oai_key) < 20

app = FastAPI(title="Polysim API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory store
simulations = {}


@app.get("/api/health")
async def health():
    return {"status": "ok", "project": "polysim", "mock_mode": MOCK_MODE}


@app.post("/api/upload")
async def upload_policy(file: UploadFile = File(...)):
    """Parse uploaded PDF or text file into structured provisions."""
    content = await file.read()
    filename = file.filename or ""

    if MOCK_MODE:
        provisions = mock_parse_provisions(content.decode("utf-8", errors="ignore")[:200])
    elif filename.endswith(".pdf"):
        provisions = await parse_policy_pdf(content)
    else:
        # Treat as plaintext (.txt, .md, or any non-PDF)
        text = content.decode("utf-8", errors="ignore")
        provisions = await parse_policy_text(text)

    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {"provisions": provisions, "results": [], "status": "parsed"}
    return {"policy_id": policy_id, "provisions": provisions}


@app.post("/api/upload-text")
async def upload_policy_text(body: dict):
    """Parse raw policy text (no file upload needed). Send {"text": "your policy here"}."""
    text = body.get("text", "")
    if not text:
        return {"error": "No text provided"}

    if MOCK_MODE:
        provisions = mock_parse_provisions(text[:200])
    else:
        provisions = await parse_policy_text(text)

    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {"provisions": provisions, "results": [], "status": "parsed"}
    return {"policy_id": policy_id, "provisions": provisions}


@app.get("/api/demographics")
async def get_demographics():
    """Return enriched GRC profiles with real Census + GE2020 data."""
    try:
        profiles = get_enriched_grc_profiles()
    except Exception:
        profiles = load_grc_profiles()
    return {"grcs": profiles}


@app.get("/api/backtest")
async def backtest():
    """Run backtest against GE2020 actual results."""
    result = run_backtest(use_mock=MOCK_MODE)
    return result


@app.post("/api/gerrymander")
async def gerrymander_analysis(request: dict = None):
    """
    Analyze gerrymandering opportunities based on demographic + sentiment data.

    Accepts optional JSON body with:
    - target_party: "PAP" or "WP" (default: "PAP")
    - strategy: "maximize_seats" or "minimize_opposition" (default: "maximize_seats")

    Returns redistricting suggestions based on demographic composition analysis.
    """
    if request is None:
        request = {}

    target_party = request.get("target_party", "PAP")
    profiles = get_enriched_grc_profiles()
    ethnicity = load_pop_ethnicity()
    income = load_income_distribution()

    # Run sim to get current predicted sentiment
    personas = build_personas(target_count=200)
    results = [mock_agent_response(p) for p in personas]
    for rnd in range(3):
        results = propagate_sentiment_v2(results, rnd)

    # Aggregate support by GRC
    grc_support = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grc_support:
            grc_support[grc] = {"support_w": 0, "total_w": 0}
        w = r["persona"].get("weight", 1)
        if r["sentiment"] == "support":
            grc_support[grc]["support_w"] += w
        grc_support[grc]["total_w"] += w

    # Analyze each constituency
    analysis = []
    for grc_name, profile in profiles.items():
        support_data = grc_support.get(grc_name, {"support_w": 0, "total_w": 1})
        predicted_support = support_data["support_w"] / support_data["total_w"] * 100

        ge2020 = profile.get("ge2020", {})
        actual_pap = 0
        if ge2020.get("results"):
            pap = next((p for p in ge2020["results"] if p["party"] == "PAP"), None)
            if pap:
                actual_pap = pap["vote_percentage"] * 100

        # Vulnerability: close margins + diverse demographics = swing potential
        margin = ge2020.get("margin", 1.0) * 100
        vulnerability = "safe" if margin > 20 else ("swing" if margin > 10 else "vulnerable")

        # Gerrymandering leverage: areas where small boundary changes could flip outcomes
        leverage_factors = []
        if profile.get("chinese", 0) > 0.75:
            leverage_factors.append("high Chinese concentration — stable PAP base")
        if profile.get("malay", 0) > 0.18:
            leverage_factors.append("significant Malay population — sensitive to housing/cost policies")
        if profile.get("indian", 0) > 0.14:
            leverage_factors.append("significant Indian population — employment concerns")

        # Redistricting suggestion
        suggestion = None
        if target_party == "PAP":
            if vulnerability == "vulnerable" and predicted_support < 55:
                suggestion = f"Consider merging with adjacent safe constituency to dilute opposition strength. Current margin: {margin:.1f}%"
            elif vulnerability == "safe" and predicted_support > 70:
                suggestion = f"Surplus votes ({predicted_support:.0f}%) could be redistributed to shore up nearby swing seats."
        else:
            if vulnerability == "swing":
                suggestion = f"Target for opposition concentration. Margin only {margin:.1f}%."

        analysis.append({
            "constituency": grc_name,
            "seats": profile.get("seats", 5),
            "predicted_support_pct": round(predicted_support, 1),
            "actual_pap_2020_pct": round(actual_pap, 1),
            "margin_2020_pct": round(margin, 1),
            "vulnerability": vulnerability,
            "chinese_pct": round(profile.get("chinese", 0) * 100, 1),
            "malay_pct": round(profile.get("malay", 0) * 100, 1),
            "leverage_factors": leverage_factors,
            "redistricting_suggestion": suggestion,
        })

    # Sort by vulnerability (most swing first)
    analysis.sort(key=lambda x: x["margin_2020_pct"])

    # Overall strategy summary
    vulnerable_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "vulnerable")
    swing_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "swing")
    safe_seats = sum(a["seats"] for a in analysis if a["vulnerability"] == "safe")

    return {
        "target_party": target_party,
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
    """Stream simulation: agents -> contagion -> vote prediction."""
    await websocket.accept()

    if policy_id not in simulations:
        await websocket.send_json({"type": "error", "message": "Policy not found"})
        await websocket.close()
        return

    sim = simulations[policy_id]
    provisions = sim["provisions"]
    personas = build_personas()

    try:
        # Phase 1: Stream individual agent results
        all_results = []
        if MOCK_MODE:
            for persona in personas:
                result = mock_agent_response(persona)
                all_results.append(result)
                await websocket.send_json({"type": "agent_result", "data": result})
                await asyncio.sleep(0.05)  # simulate network delay
        else:
            async for result in stream_agent_results(personas, provisions):
                all_results.append(result)
                await websocket.send_json({"type": "agent_result", "data": result})

        sim["results"] = all_results

        # Phase 2: Contagion propagation (3 rounds)
        for round_num in range(3):
            all_results = propagate_sentiment(all_results, round_num)
            grc_agg = aggregate_by_grc(all_results)
            await websocket.send_json({
                "type": "contagion_round",
                "round": round_num,
                "data": grc_agg
            })
            await asyncio.sleep(0.6)  # dramatic effect for demo

        # Phase 3: Vote prediction
        vote = compute_vote_prediction(all_results)
        await websocket.send_json({"type": "vote_prediction", "data": vote})
        await websocket.send_json({"type": "complete"})

    except WebSocketDisconnect:
        pass


@app.post("/api/adjust/{policy_id}")
async def adjust(policy_id: str, lever: str, value: float):
    """Apply lever adjustment, return new sim ID for re-run."""
    if policy_id not in simulations:
        return {"error": "not found"}
    new_provisions = apply_lever(simulations[policy_id]["provisions"], lever, value)
    new_id = str(uuid.uuid4())
    simulations[new_id] = {"provisions": new_provisions, "results": [], "status": "adjusted"}
    return {"policy_id": new_id, "provisions": new_provisions}


def aggregate_by_grc(results: list) -> dict:
    """Aggregate agent results by GRC."""
    grcs = {}
    for r in results:
        grc = r["persona"]["grc"]
        if grc not in grcs:
            grcs[grc] = {"support": 0, "neutral": 0, "reject": 0, "total": 0, "agents": []}
        grcs[grc][r["sentiment"]] += r["persona"].get("weight", 1)
        grcs[grc]["total"] += r["persona"].get("weight", 1)
        grcs[grc]["agents"].append(r)
    # Convert to percentages
    for grc, data in grcs.items():
        t = data["total"] or 1
        data["support_pct"] = round(data["support"] / t * 100, 1)
        data["neutral_pct"] = round(data["neutral"] / t * 100, 1)
        data["reject_pct"] = round(data["reject"] / t * 100, 1)
    return grcs


def compute_vote_prediction(results: list) -> dict:
    """Simple vote aggregation from agent results."""
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
        "call": "PASS" if votes["for"] / t > 0.5 else "FAIL"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
