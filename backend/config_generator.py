"""
Region/segment config generator — agentic research via TinyFish + GPT-4o synthesis.

Flow:
  1. GPT-4o plans which URLs to research for the given description
  2. TinyFish runs each URL with a structured extraction goal (live web data)
  3. GPT-4o narrates each result as it arrives (streamed to frontend)
  4. GPT-4o synthesizes all research into a segment config dict
  5. Falls back to GPT-4o knowledge-only if TinyFish is unavailable
"""
import json
import os
from openai import AsyncOpenAI
from scraper import tinyfish_run, TINYFISH_API_KEY
from config import SINGAPORE

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


# ── Prompts ──────────────────────────────────────────────────────────────────

PLANNER_PROMPT = """You are a demographic research planner.

Given a description of a population or segmentation approach, plan 2-4 targeted web searches to gather real demographic data.

Choose URLs from reliable sources: Wikipedia demographic pages, government census sites, UN data, World Bank. Prefer pages that have structured tables of demographic data.

Respond in JSON only:
{
  "plan": "<one sentence explaining your research strategy>",
  "searches": [
    {
      "label": "<short label for this search, e.g. 'US state populations'>",
      "url": "<full URL to visit>",
      "goal": "<precise extraction goal — what structured data to pull from this page, in what JSON format>"
    }
  ]
}

Rules:
- 2-4 searches maximum (quality > quantity)
- Each goal must specify the exact JSON format to return
- Prefer Wikipedia for quick structured data
- For country/state demographics: population size, ethnic/cultural breakdown, income levels
- For class/ideological segments: use general knowledge search on Wikipedia or similar"""

NARRATOR_PROMPT = """You are narrating a live demographic research process to a non-technical user.

Given a research result, write 1-2 sentences explaining what was found and why it matters for the simulation.
Be specific about the data (mention numbers if present). Keep it conversational, under 40 words.
If the search failed, briefly explain and note you'll use knowledge-based estimates instead."""

SYNTHESIZER_PROMPT = """You are an expert demographer generating simulation segment configurations.

Based on the research results below, generate demographic segment definitions for a prediction market simulation.

The segments replace standard demographic groupings. They should capture meaningful splits affecting how people respond to scenarios.

Respond in JSON only:
{
  "name": "<region or context name>",
  "description": "<one sentence describing what was configured>",
  "segments": [
    {
      "key": "<snake_case>",
      "label": "<display label>",
      "weight": <0.0-1.0, population share — all must sum to 1.0>,
      "risk_appetite": <0.0-1.0>,
      "concerns": ["<concern 1>", "<concern 2>", "<concern 3>", "<concern 4>"],
      "description": "<who this segment is, with a specific data point if available>"
    }
  ],
  "age_band_adjustments": {
    "<age_band>": <multiplier — omit to keep defaults>
  },
  "confidence_note": "<note data quality, which figures are from live research vs estimates>"
}

Rules:
- 2-8 segments, weights sum to 1.0
- Use real numbers from research where available
- confidence_note must distinguish live data from estimates"""

FALLBACK_SYNTHESIZER_PROMPT = """You are an expert demographer and social scientist.

Generate demographic segment definitions for a prediction market simulation based on your knowledge.

Respond in JSON only:
{
  "name": "<region or context name>",
  "description": "<one sentence>",
  "segments": [
    {
      "key": "<snake_case>",
      "label": "<display label>",
      "weight": <0.0-1.0>,
      "risk_appetite": <0.0-1.0>,
      "concerns": ["<concern 1>", "<concern 2>", "<concern 3>"],
      "description": "<who this segment is>"
    }
  ],
  "age_band_adjustments": {},
  "confidence_note": "Based on GPT-4o training data — no live web research (TinyFish unavailable)"
}

All weights must sum to 1.0. Include 2-8 segments."""


# ── Streaming research generator ──────────────────────────────────────────────

async def stream_research_and_generate(description: str):
    """
    Async generator that yields SSE-compatible event dicts.

    Events:
      {"type": "plan",          "message": str, "searches": list, "has_tinyfish": bool}
      {"type": "search_start",  "index": int, "label": str, "url": str}
      {"type": "search_result", "index": int, "label": str, "snippet": str, "success": bool, "raw": dict}
      {"type": "narrate",       "index": int, "text": str}
      {"type": "synthesis_start"}
      {"type": "complete",      "config_id": str, "config": dict}
      {"type": "error",         "message": str}
    """
    has_tinyfish = bool(TINYFISH_API_KEY)

    # ── Step 1: Plan research ──────────────────────────────────────────────────
    if has_tinyfish:
        try:
            plan_response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": f"Plan research for:\n{description}"},
                ],
                max_tokens=800,
                temperature=0.2,
            )
            plan = json.loads(plan_response.choices[0].message.content)
        except Exception as e:
            yield {"type": "error", "message": f"Planning failed: {e}"}
            return

        searches = plan.get("searches", [])
        yield {
            "type": "plan",
            "message": plan.get("plan", ""),
            "searches": searches,
            "has_tinyfish": True,
        }

        # ── Step 2: TinyFish runs each search ──────────────────────────────────
        research_results = []
        for i, search in enumerate(searches):
            yield {
                "type": "search_start",
                "index": i,
                "label": search["label"],
                "url": search["url"],
            }

            raw = await tinyfish_run(
                url=search["url"],
                goal=search["goal"],
                browser_profile="lite",
            )

            success = not raw.get("fallback") and not raw.get("error")
            snippet = _make_snippet(raw, search["label"])

            yield {
                "type": "search_result",
                "index": i,
                "label": search["label"],
                "snippet": snippet,
                "success": success,
                "raw": raw if success else {},
                "error": raw.get("error") if not success else None,
            }

            if not success:
                # Real error — don't narrate fake "I'll use estimates", just report
                yield {
                    "type": "narrate",
                    "index": i,
                    "text": f"TinyFish could not retrieve this page: {raw.get('error', 'unknown error')}",
                    "is_error": True,
                }
                research_results.append({"search": search, "result": None, "success": False})
                continue

            # ── GPT-4o narrates what it actually found ─────────────────────────
            try:
                narration_resp = await _get_client().chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": NARRATOR_PROMPT},
                        {"role": "user", "content":
                            f"Search: {search['label']}\n"
                            f"URL: {search['url']}\n"
                            f"Result: {json.dumps(raw)[:800]}"
                        },
                    ],
                    max_tokens=80,
                    temperature=0.4,
                )
                narration = narration_resp.choices[0].message.content.strip()
            except Exception:
                narration = "Data retrieved."

            yield {"type": "narrate", "index": i, "text": narration}
            research_results.append({"search": search, "result": raw, "success": True})

        # ── Step 3: Synthesize ─────────────────────────────────────────────────
        successful = [r for r in research_results if r["success"]]
        failed_count = len(research_results) - len(successful)
        yield {
            "type": "synthesis_start",
            "live_results": len(successful),
            "failed": failed_count,
        }

        research_summary = json.dumps([
            {"label": r["search"]["label"], "data": r["result"]}
            for r in successful
        ], indent=2)[:4000]  # cap context size

        try:
            synth_response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYNTHESIZER_PROMPT},
                    {"role": "user", "content":
                        f"Original request: {description}\n\nResearch results:\n{research_summary}"
                    },
                ],
                max_tokens=1500,
                temperature=0.2,
            )
            generated = json.loads(synth_response.choices[0].message.content)
        except Exception as e:
            yield {"type": "error", "message": f"Synthesis failed: {e}"}
            return

    else:
        # ── No TinyFish: GPT-4o knowledge only ────────────────────────────────
        yield {
            "type": "plan",
            "message": "TinyFish not configured — using GPT-4o knowledge to generate segments.",
            "searches": [],
            "has_tinyfish": False,
        }
        yield {"type": "synthesis_start"}
        try:
            synth_response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": FALLBACK_SYNTHESIZER_PROMPT},
                    {"role": "user", "content": f"Generate segment config for:\n{description}"},
                ],
                max_tokens=1500,
                temperature=0.3,
            )
            generated = json.loads(synth_response.choices[0].message.content)
        except Exception as e:
            yield {"type": "error", "message": f"Generation failed: {e}"}
            return

    # ── Build final config and emit ────────────────────────────────────────────
    config = _build_config_override(generated, description)
    config_id = _store_config(config)
    yield {"type": "complete", "config_id": config_id, "config": config}


def _make_snippet(raw: dict, label: str) -> str:
    """Extract a human-readable snippet from a TinyFish result."""
    if raw.get("fallback") or raw.get("error"):
        return f"[No data — {raw.get('error', 'search failed')}]"

    # Try to find the most data-rich key
    for key in raw:
        val = raw[key]
        if isinstance(val, list) and val:
            item = val[0]
            if isinstance(item, dict):
                pairs = [f"{k}: {v}" for k, v in list(item.items())[:3]]
                return f"{len(val)} items found. First: {', '.join(pairs)}"
            return f"{len(val)} items: {str(val[:3])}"
        if isinstance(val, (int, float, str)) and key not in ("status", "error"):
            return f"{key}: {val}"

    text = json.dumps(raw)
    return text[:200] + ("…" if len(text) > 200 else "")


# ── Config storage ────────────────────────────────────────────────────────────

_config_store: dict[str, dict] = {}


def _store_config(config: dict) -> str:
    import uuid
    config_id = str(uuid.uuid4())
    _config_store[config_id] = config
    return config_id


def get_stored_config(config_id: str) -> dict | None:
    return _config_store.get(config_id)


# ── Config builder ────────────────────────────────────────────────────────────

def _build_config_override(generated: dict, description: str) -> dict:
    segments = generated.get("segments", [])
    if not segments:
        return {"_generated": False, "_description": description}

    # Normalize weights to sum to 1.0
    total_w = sum(s.get("weight", 0) for s in segments)
    if total_w > 0:
        for s in segments:
            s["weight"] = round(s["weight"] / total_w, 4)

    races = [s["label"] for s in segments]
    concerns = {
        s["label"]: s.get("concerns", ["cost of living", "security", "opportunity"])
        for s in segments
    }
    risk_by_segment = {s["label"]: s.get("risk_appetite", 0.5) for s in segments}

    age_band_weights = dict(SINGAPORE["age_band_weights"])
    for band, mult in generated.get("age_band_adjustments", {}).items():
        if band in age_band_weights:
            age_band_weights[band] = round(age_band_weights[band] * mult, 4)
    total_age = sum(age_band_weights.values())
    if total_age > 0:
        age_band_weights = {k: round(v / total_age, 4) for k, v in age_band_weights.items()}

    return {
        "name": generated.get("name", description[:40]),
        "races": races,
        "concerns": concerns,
        "age_band_weights": age_band_weights,
        "_custom_segments": True,
        "_segments_meta": segments,
        "_risk_by_segment": risk_by_segment,
        "_generated": True,
        "_description": description,
        "confidence_note": generated.get("confidence_note", ""),
    }


# ── Simple non-streaming fallback (used by /api/configure-region) ─────────────

async def generate_segment_config(description: str) -> dict:
    """Non-streaming version — collects all events and returns final config."""
    result = None
    async for event in stream_research_and_generate(description):
        if event["type"] == "complete":
            result = event
        elif event["type"] == "error":
            return {"_generated": False, "_error": event["message"], "_description": description}
    if result:
        return result.get("config", {})
    return {"_generated": False, "_description": description}
