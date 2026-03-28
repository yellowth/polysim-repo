import asyncio, json
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

Based ONLY on your profile, evaluate the policy provisions below.
Respond naturally as this person would -- use casual Singapore English.

Respond in JSON only:
{{
  "sentiment": "support" | "neutral" | "reject",
  "confidence": 0.0-1.0,
  "reason": "<1-2 sentences in first person, Singlish OK>",
  "vote_intent": "for" | "against" | "undecided",
  "key_provision": "<which provision # affects you most>"
}}"""


async def simulate_agent(persona: dict, provisions: list[dict]) -> dict:
    """Run a single agent evaluation."""
    provisions_text = "\n".join(
        f"{p['id']}. {p['title']}: {p['summary']}" for p in provisions
    )
    try:
        response = await _get_client().chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT.format(**persona)},
                {"role": "user", "content": f"POLICY PROVISIONS:\n{provisions_text}"}
            ],
            max_tokens=200,
            temperature=0.7,
        )
        result = json.loads(response.choices[0].message.content)
        result["persona"] = persona
        # Convert sentiment to numeric score for contagion
        score_map = {"support": 1.0, "neutral": 0.0, "reject": -1.0}
        result["score"] = score_map.get(result["sentiment"], 0.0)
        return result
    except Exception as e:
        return {
            "sentiment": "neutral", "confidence": 0.0,
            "reason": f"Error: {str(e)}", "vote_intent": "undecided",
            "key_provision": "none", "persona": persona, "score": 0.0
        }


async def stream_agent_results(personas: list[dict], provisions: list[dict]):
    """Yield agent results as they complete, with concurrency limit."""
    semaphore = asyncio.Semaphore(15)

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
