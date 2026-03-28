"""
Intermediary scenario agent — converts any NL scenario into structured simulation input.

Accepts any question or scenario (political, economic, geopolitical, social)
and outputs structured provisions + outcome framing that the simulation pipeline
can consume without modification.
"""
import json
from openai import AsyncOpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


INTERPRETER_PROMPT = """You are an expert at translating any scenario or question into a structured prediction market format.

Given a natural language scenario, output a binary YES/NO framing plus 2-5 evaluable "provisions" (dimensions/aspects of the scenario that agents can assess).

The simulation models how different demographic segments (by age, income, housing, background) would respond based on self-interest and utility. Agents reason about how the scenario affects THEM personally.

Respond in JSON only:
{
  "title": "<short title, max 8 words>",
  "yes_definition": "<precise: what constitutes the YES outcome>",
  "no_definition": "<precise: what constitutes the NO outcome>",
  "context": "<2-3 sentences of neutral background framing agents will receive>",
  "time_horizon": "short-term" | "medium-term" | "long-term",
  "domain": "political" | "economic" | "social" | "geopolitical" | "personal" | "other",
  "provisions": [
    {
      "id": 1,
      "title": "<aspect title>",
      "summary": "<1-2 sentences: what this aspect means and its practical implications for individuals>",
      "affected_groups": ["<group1>", "<group2>"],
      "parameters": {}
    }
  ],
  "stakes_by_segment": {
    "<segment description>": "<what they gain or lose>"
  }
}

Guidelines:
- YES/NO must be mutually exclusive and collectively exhaustive
- Provisions should let agents assess personal impact (economic, social, practical)
- Write summaries so a non-expert agent can reason about self-interest
- For open-ended questions (e.g. "best approach to X"), frame as: YES = approach A is optimal, NO = it is not
- stakes_by_segment should cover 3-5 meaningful demographic groups"""


async def interpret_scenario(text: str, region_name: str = "the region") -> dict:
    """
    Convert any NL scenario into structured simulation input.

    Returns dict with title, yes_definition, no_definition, provisions, stakes_by_segment.
    On failure, wraps the raw text as a single provision so the pipeline always gets valid input.
    """
    user_message = (
        f"SCENARIO:\n{text}\n\n"
        f"Context: You are modeling this for {region_name}. "
        f"Consider the local population and their practical concerns."
    )

    try:
        response = await _get_client().chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": INTERPRETER_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1200,
            temperature=0.3,
        )
        result = json.loads(response.choices[0].message.content)

        # Normalize provisions
        for i, p in enumerate(result.get("provisions", [])):
            p.setdefault("id", i + 1)
            p.setdefault("affected_groups", [])
            p.setdefault("parameters", {})

        result["raw_scenario"] = text
        return result

    except Exception as e:
        # Graceful fallback — always return usable provisions
        return {
            "title": text[:60].rstrip() + ("…" if len(text) > 60 else ""),
            "yes_definition": "The scenario outcome is positive / favorable",
            "no_definition": "The scenario outcome is negative / unfavorable",
            "context": text,
            "time_horizon": "medium-term",
            "domain": "other",
            "provisions": [
                {
                    "id": 1,
                    "title": "Scenario Assessment",
                    "summary": text,
                    "affected_groups": ["all segments"],
                    "parameters": {},
                }
            ],
            "stakes_by_segment": {},
            "raw_scenario": text,
            "_error": str(e),
        }
