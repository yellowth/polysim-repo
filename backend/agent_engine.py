"""Agent simulation engine — GPT-4o evaluates policy as each persona."""
import asyncio
import json
from openai import AsyncOpenAI

client = None


def _get_client():
    global client
    if client is None:
        client = AsyncOpenAI()
    return client


AGENT_SYSTEM_PROMPT = """You are simulating a Singapore resident evaluating a government policy.

YOUR PROFILE:
- Age: {age}, Race: {race}
- Monthly Household Income: {income}
- Housing: {housing}
- Constituency: {grc}
- Occupation: {occupation}
- Family Status: {family_status}
- Key Concerns: {concerns}
- Risk Appetite: {risk_description}

Based ONLY on your profile, evaluate the policy provisions below.
You are SELF-INTERESTED — assess how this policy affects YOU and people like you.
Think about your financial situation, family needs, and community.
Respond naturally as this person would — use casual Singapore English.

Respond in JSON only:
{{
  "sentiment": "support" | "neutral" | "reject",
  "confidence": 0.0-1.0,
  "reason": "<2-3 sentences in first person, Singlish OK — explain WHY this matters to you>",
  "vote_intent": "for" | "against" | "undecided",
  "key_provision": "<which provision # affects you most>"
}}"""

RISK_DESCRIPTIONS = {
    (0.0, 0.3): "conservative — you avoid risk, prefer stability and guaranteed outcomes",
    (0.3, 0.5): "cautious — you're careful with money, prefer safe bets",
    (0.5, 0.7): "moderate — you'll take calculated risks if the upside is clear",
    (0.7, 1.01): "bold — you're comfortable with risk and willing to bet on upside",
}


def _risk_description(risk_appetite: float) -> str:
    for (lo, hi), desc in RISK_DESCRIPTIONS.items():
        if lo <= risk_appetite < hi:
            return desc
    return "moderate"


async def simulate_agent(persona: dict, provisions: list[dict], max_retries: int = 2) -> dict:
    """Run a single agent evaluation with retry logic."""
    provisions_text = "\n".join(
        f"{p['id']}. {p['title']}: {p['summary']}" for p in provisions
    )

    risk_appetite = persona.get("risk_appetite", 0.5)
    prompt_persona = {**persona, "risk_description": _risk_description(risk_appetite)}

    for attempt in range(max_retries + 1):
        try:
            response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT.format(**prompt_persona)},
                    {"role": "user", "content": f"POLICY PROVISIONS:\n{provisions_text}"}
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

            # Convert sentiment to numeric score for contagion
            score_map = {"support": 1.0, "neutral": 0.0, "reject": -1.0}
            result["score"] = score_map.get(result["sentiment"], 0.0)
            return result

        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))  # backoff
                continue
            return {
                "sentiment": "neutral", "confidence": 0.0,
                "reason": f"Error: {str(e)}", "vote_intent": "undecided",
                "key_provision": "none", "persona": persona, "score": 0.0,
                "risk_appetite": risk_appetite,
            }


async def stream_agent_results(personas: list[dict], provisions: list[dict]):
    """Yield agent results as they complete, with concurrency limit."""
    # Scale concurrency with agent count, cap at 30
    concurrency = min(30, max(10, len(personas) // 5))
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(persona):
        async with semaphore:
            return await simulate_agent(persona, provisions)

    tasks = [asyncio.create_task(bounded(p)) for p in personas]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result


async def run_simulation(personas: list[dict], provisions: list[dict]) -> list[dict]:
    """Run all agents and return complete results."""
    results = []
    async for r in stream_agent_results(personas, provisions):
        results.append(r)
    return results
