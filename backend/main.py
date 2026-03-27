import os, json, uuid, asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from policy_parser import parse_policy_pdf
from agent_engine import run_simulation, stream_agent_results
from contagion import propagate_sentiment
from demographics import build_personas, load_grc_profiles
from levers import apply_lever

app = FastAPI(title="Polisim API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory store
simulations = {}


@app.get("/api/health")
async def health():
    return {"status": "ok", "project": "polisim"}


@app.post("/api/upload")
async def upload_policy(file: UploadFile = File(...)):
    """Parse uploaded PDF into structured provisions."""
    content = await file.read()
    provisions = await parse_policy_pdf(content)
    policy_id = str(uuid.uuid4())
    simulations[policy_id] = {"provisions": provisions, "results": [], "status": "parsed"}
    return {"policy_id": policy_id, "provisions": provisions}


@app.get("/api/demographics")
async def get_demographics():
    """Return GRC profiles and demographic segments."""
    profiles = load_grc_profiles()
    return {"grcs": profiles}


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
