"""Agent simulation engine — GPT-4o evaluates any scenario as each persona."""
import asyncio
import json
from openai import AsyncOpenAI
from demographics import load_grc_profiles
from config import get_config

client = None


def _get_client():
    global client
    if client is None:
        client = AsyncOpenAI()
    return client


AGENT_SYSTEM_PROMPT = """You are simulating a {region_name} resident evaluating a scenario or policy.

YOUR PROFILE:
- Age: {age}, Background: {race}
- Monthly Household Income: {income}
- Housing: {housing}
- Location: {grc}
- Occupation: {occupation}
- Family Status: {family_status}
- Key Concerns: {concerns}
- Risk Appetite: {risk_description}

{constituency_context}{scenario_frame}

Based ONLY on your profile, evaluate the provisions below.
You are SELF-INTERESTED — assess how this scenario affects YOU and people like you.
Think about your financial situation, family needs, and community.
Respond naturally as this person would.

Respond in JSON only:
{{
  "sentiment": "support" | "neutral" | "reject",
  "confidence": 0.0-1.0,
  "reason": "<2-3 sentences in first person — explain WHY this matters to you personally>",
  "vote_intent": "for" | "against" | "undecided",
  "key_provision": "<which provision # affects you most>"
}}"""

RISK_DESCRIPTIONS = {
    (0.0, 0.3): "conservative — you avoid risk, prefer stability and guaranteed outcomes",
    (0.3, 0.5): "cautious — you're careful, prefer safe bets",
    (0.5, 0.7): "moderate — you'll take calculated risks if the upside is clear",
    (0.7, 1.01): "bold — comfortable with risk, willing to bet on upside",
}


def _risk_description(risk_appetite: float) -> str:
    for (lo, hi), desc in RISK_DESCRIPTIONS.items():
        if lo <= risk_appetite < hi:
            return desc
    return "moderate"


def _build_constituency_context(persona: dict, grc_profiles: dict) -> str:
    """Build a short context string about the agent's constituency."""
    grc_name = persona.get("grc", "")
    profile = grc_profiles.get(grc_name, {})
    if not profile:
        return ""

    party = profile.get("mp_party", "")
    if party:
        return f"CONSTITUENCY: Your area ({grc_name}) is currently represented by {party}.\n\n"
    return ""


def _build_scenario_frame(scenario_frame: dict | None) -> str:
    """Build scenario framing block for agent prompts."""
    if not scenario_frame:
        return ""
    title = scenario_frame.get("title", "")
    yes_def = scenario_frame.get("yes_definition", "")
    no_def = scenario_frame.get("no_definition", "")
    context = scenario_frame.get("context", "")

    parts = []
    if context:
        parts.append(f"SCENARIO CONTEXT: {context}")
    if yes_def and no_def:
        parts.append(f"OUTCOME FRAMING:\n- YES means: {yes_def}\n- NO means: {no_def}")
    return "\n".join(parts) + "\n\n" if parts else ""


async def simulate_agent(
    persona: dict,
    provisions: list[dict],
    scenario_frame: dict | None = None,
    region_config: dict | None = None,
    grc_profiles: dict | None = None,
    max_retries: int = 2,
) -> dict:
    """Run a single agent evaluation with retry logic."""
    provisions_text = "\n".join(
        f"{p['id']}. {p['title']}: {p['summary']}" for p in provisions
    )

    cfg = region_config or get_config()
    region_name = cfg.get("name", "the region")
    risk_appetite = persona.get("risk_appetite", 0.5)

    constituency_context = _build_constituency_context(persona, grc_profiles or {})
    scenario_frame_text = _build_scenario_frame(scenario_frame)

    prompt_vars = {
        **persona,
        "region_name": region_name,
        "risk_description": _risk_description(risk_appetite),
        "constituency_context": constituency_context,
        "scenario_frame": scenario_frame_text,
    }

    for attempt in range(max_retries + 1):
        try:
            response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT.format(**prompt_vars)},
                    {"role": "user", "content": f"PROVISIONS TO EVALUATE:\n{provisions_text}"},
                ],
                max_tokens=400,
                temperature=0.7,
            )
            result = json.loads(response.choices[0].message.content)
            result["persona"] = persona
            result["risk_appetite"] = risk_appetite

            # Validate and normalize
            result["sentiment"] = result.get("sentiment", "neutral")
            if result["sentiment"] not in ("support", "neutral", "reject"):
                result["sentiment"] = "neutral"
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            result["vote_intent"] = result.get("vote_intent", "undecided")
            if result["vote_intent"] not in ("for", "against", "undecided"):
                result["vote_intent"] = "undecided"

            score_map = {"support": 1.0, "neutral": 0.0, "reject": -1.0}
            result["score"] = score_map.get(result["sentiment"], 0.0)
            return result

        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return {
                "sentiment": "neutral", "confidence": 0.0,
                "reason": f"Error: {str(e)}", "vote_intent": "undecided",
                "key_provision": "none", "persona": persona, "score": 0.0,
                "risk_appetite": risk_appetite,
            }


async def stream_agent_results(
    personas: list[dict],
    provisions: list[dict],
    scenario_frame: dict | None = None,
    region_config: dict | None = None,
):
    """Yield agent results as they complete, with concurrency limit."""
    # Load GRC profiles once for constituency context injection
    grc_profiles = load_grc_profiles()

    # Scale concurrency with agent count, cap at 30
    concurrency = min(30, max(10, len(personas) // 5))
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(persona):
        async with semaphore:
            return await simulate_agent(
                persona, provisions,
                scenario_frame=scenario_frame,
                region_config=region_config,
                grc_profiles=grc_profiles,
            )

    tasks = [asyncio.create_task(bounded(p)) for p in personas]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result


async def run_simulation(
    personas: list[dict],
    provisions: list[dict],
    scenario_frame: dict | None = None,
    region_config: dict | None = None,
) -> list[dict]:
    """Run all agents and return complete results."""
    results = []
    async for r in stream_agent_results(personas, provisions, scenario_frame, region_config):
        results.append(r)
    return results
