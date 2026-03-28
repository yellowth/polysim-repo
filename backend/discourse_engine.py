"""
Discourse Engine — agents post, reply, and react to each other over rounds.

Replaces silent group-mean contagion with visible LLM-driven communication.
Network ties (GRC, race, age, housing) determine message visibility.
Each round: active agents see a feed of recent messages from their network,
then post or reply. Exposure shifts their score.
"""
import asyncio
import random
import json
import time
from openai import AsyncOpenAI
from market import compute_agent_bet
from discourse_debug import dlog, dlog_exception, dlog_warning

client = None


def _get_client():
    global client
    if client is None:
        client = AsyncOpenAI()
    return client


# ── Network tie strength (probability of seeing a message from that group) ───
TIE_WEIGHTS = {
    "same_grc": 0.85,
    "same_race": 0.60,
    "same_age": 0.40,
    "same_housing": 0.35,
    "global": 0.10,
}


def _tie_strength(author_persona: dict, reader_persona: dict) -> float:
    """How likely reader sees author's message (0-1). Higher = stronger tie."""
    score = TIE_WEIGHTS["global"]
    if author_persona["grc"] == reader_persona["grc"]:
        score = max(score, TIE_WEIGHTS["same_grc"])
    if author_persona["race"] == reader_persona["race"]:
        score = max(score, TIE_WEIGHTS["same_race"])
    if author_persona["age"] == reader_persona["age"]:
        score = max(score, TIE_WEIGHTS["same_age"])
    if author_persona.get("housing") == reader_persona.get("housing"):
        score = max(score, TIE_WEIGHTS["same_housing"])
    return score


def _build_feed(agent: dict, all_messages: list[dict], max_items: int = 6) -> list[dict]:
    """Build a personalized feed for this agent based on network ties."""
    reader = agent["persona"]
    scored = []
    for msg in all_messages:
        if msg["agent_id"] == id(agent):
            continue
        tie = _tie_strength(msg["persona"], reader)
        if random.random() < tie:
            scored.append((tie, msg))

    scored.sort(key=lambda x: (-x[0], -x[1].get("timestamp", 0)))
    return [m for _, m in scored[:max_items]]


DISCOURSE_PROMPT = """You are a {race} {age}-year-old living in {grc}, working as {occupation}.
Income: {income} | Housing: {housing} | Concerns: {concerns}

Your current position: {sentiment} (confidence {confidence:.0%})
Your reasoning: {reason}

You are in a public discussion about this policy. Here is what others are saying:

{feed_text}

Based on your background and what you've read:
1. Write a short post (1-2 sentences, casual/natural voice — like a forum comment)
2. Optionally reply to one specific message if it resonates or frustrates you
3. Say whether reading these changed your mind at all

Respond in JSON only:
{{
  "post": "your forum-style comment",
  "reply_to": null or "quote the message you're responding to (first few words)",
  "reply": null or "your reply to that message",
  "action": "post" | "reply" | "agree" | "disagree" | "lurk",
  "sentiment_shift": "more_supportive" | "more_opposed" | "unchanged" | "less_certain",
  "new_confidence": 0.0-1.0,
  "influence_reason": "1 sentence on what moved or didn't move you"
}}"""


def _format_feed(feed: list[dict]) -> str:
    if not feed:
        return "(No messages in your feed yet — you're among the first to speak.)"
    lines = []
    for msg in feed:
        p = msg["persona"]
        tag = f"{p['race']} {p['age']} from {p['grc']}"
        sentiment_emoji = {"support": "👍", "reject": "👎", "neutral": "🤷"}.get(msg.get("sentiment", ""), "")
        lines.append(f"[{tag}] {sentiment_emoji} \"{msg['text']}\"")
        if msg.get("reply_text"):
            lines.append(f"  ↳ replied: \"{msg['reply_text']}\"")
    return "\n".join(lines)


SHIFT_MAP = {
    "more_supportive": 0.15,
    "more_opposed": -0.15,
    "less_certain": 0.0,
    "unchanged": 0.0,
}


def _apply_sentiment_shift(agent: dict, shift: str, new_confidence: float) -> dict:
    """Update agent score/sentiment based on discourse outcome."""
    updated = {**agent}
    delta = SHIFT_MAP.get(shift, 0.0)
    updated["score"] = max(-1.0, min(1.0, updated["score"] + delta))

    if updated["score"] > 0.33:
        updated["sentiment"] = "support"
        updated["vote_intent"] = "for"
    elif updated["score"] < -0.33:
        updated["sentiment"] = "reject"
        updated["vote_intent"] = "against"
    else:
        updated["sentiment"] = "neutral"
        updated["vote_intent"] = "undecided"

    updated["confidence"] = max(0.1, min(0.95, new_confidence))
    compute_agent_bet(updated)
    return updated


async def _agent_discourse_turn(
    agent: dict, feed: list[dict], round_num: int, use_mock: bool = False
) -> dict:
    """One agent reads their feed and produces a discourse action."""
    persona = agent["persona"]
    feed_text = _format_feed(feed)

    if use_mock:
        actions = ["post", "reply", "agree", "disagree", "lurk"]
        action = random.choice(actions)
        shifts = ["unchanged", "more_supportive", "more_opposed", "less_certain"]
        shift = random.choices(shifts, weights=[0.5, 0.2, 0.2, 0.1])[0]
        templates = [
            f"As a {persona['age']} {persona['race']}, I {'support' if agent['sentiment'] == 'support' else 'am concerned about'} this policy.",
            f"This affects {persona['grc']} residents like me directly. We need to think carefully.",
            f"My {persona['occupation']} perspective: the impact on {persona['concerns']} is what matters.",
            f"I've been following this discussion. {'Makes sense to me.' if agent['sentiment'] == 'support' else 'Not convinced yet.'}",
        ]
        return {
            "post": random.choice(templates),
            "reply_to": feed[0]["text"][:30] if feed and action == "reply" else None,
            "reply": f"I {'agree' if action == 'agree' else 'disagree'} — from my experience as a {persona['occupation']}." if action in ("reply", "agree", "disagree") else None,
            "action": action,
            "sentiment_shift": shift,
            "new_confidence": max(0.1, min(0.95, agent["confidence"] + random.uniform(-0.1, 0.1))),
            "influence_reason": "Discussion reinforced my existing views." if shift == "unchanged" else "Hearing from others in my community shifted my thinking.",
        }

    prompt_vars = {
        **persona,
        "sentiment": agent["sentiment"],
        "confidence": agent["confidence"],
        "reason": agent.get("reason", "No specific reason yet."),
        "feed_text": feed_text,
    }

    try:
        system_content = DISCOURSE_PROMPT.format(**prompt_vars)
    except Exception as e:
        dlog_exception("discourse prompt format (missing persona field?)", e)
        return {
            "post": f"I'm still thinking about this as a {persona.get('race', '?')} {persona.get('age', '?')} in {persona.get('grc', '?')}.",
            "reply_to": None,
            "reply": None,
            "action": "lurk",
            "sentiment_shift": "unchanged",
            "new_confidence": agent["confidence"],
            "influence_reason": "Prompt formatting failed for this persona.",
        }

    try:
        response = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_content},
            ],
            max_tokens=300,
            temperature=0.8,
        )
        raw = response.choices[0].message.content
        if not raw or not raw.strip():
            dlog_warning("discourse LLM returned empty content idx=%s", "unknown")
            raise ValueError("empty completion")
        result = json.loads(raw)
        result["action"] = result.get("action", "post")
        result["sentiment_shift"] = result.get("sentiment_shift", "unchanged")
        result["new_confidence"] = max(0.1, min(0.95, float(result.get("new_confidence", agent["confidence"]))))
        return result
    except Exception as e:
        dlog_exception("discourse LLM turn failed", e)
        return {
            "post": f"I'm still thinking about this as a {persona['race']} {persona['age']} in {persona['grc']}.",
            "reply_to": None, "reply": None, "action": "lurk",
            "sentiment_shift": "unchanged",
            "new_confidence": agent["confidence"],
            "influence_reason": "Couldn't form a clear response this round.",
        }


async def run_discourse_round(
    results: list[dict],
    all_messages: list[dict],
    round_num: int,
    activity_rate: float = 0.4,
    use_mock: bool = False,
):
    """
    One discourse round. A subset of agents read their feed and post.
    Yields (event_type, data) tuples for WebSocket streaming.
    """
    active_count = max(3, int(len(results) * activity_rate))
    active_indices = random.sample(range(len(results)), min(active_count, len(results)))
    dlog(
        "discourse round=%s pool_messages=%s active_agents=%s mock=%s",
        round_num,
        len(all_messages),
        len(active_indices),
        use_mock,
    )

    semaphore = asyncio.Semaphore(15)
    tasks = []

    for idx in active_indices:
        agent = results[idx]
        feed = _build_feed(agent, all_messages)

        async def process(agent=agent, feed=feed, idx=idx):
            async with semaphore:
                return idx, await _agent_discourse_turn(agent, feed, round_num, use_mock)

        tasks.append(asyncio.create_task(process()))

    yielded = 0
    for coro in asyncio.as_completed(tasks):
        idx, discourse_result = await coro
        agent = results[idx]
        persona = agent["persona"]

        msg = {
            "agent_id": id(agent),
            "persona": persona,
            "sentiment": agent["sentiment"],
            "text": discourse_result.get("post", ""),
            "reply_to": discourse_result.get("reply_to"),
            "reply_text": discourse_result.get("reply"),
            "action": discourse_result.get("action", "post"),
            "round": round_num,
            "timestamp": time.time(),
        }
        all_messages.append(msg)

        shift = discourse_result.get("sentiment_shift", "unchanged")
        new_conf = discourse_result.get("new_confidence", agent["confidence"])
        results[idx] = _apply_sentiment_shift(agent, shift, new_conf)

        yielded += 1
        yield "discourse_message", {
            "round": round_num,
            "agent": {
                "race": persona["race"],
                "age": persona["age"],
                "grc": persona["grc"],
                "occupation": persona.get("occupation", ""),
                "housing": persona.get("housing", ""),
            },
            "post": discourse_result.get("post", ""),
            "reply_to": discourse_result.get("reply_to"),
            "reply": discourse_result.get("reply"),
            "action": discourse_result.get("action", "post"),
            "sentiment": results[idx]["sentiment"],
            "previous_sentiment": agent["sentiment"],
            "sentiment_shift": shift,
            "confidence": results[idx]["confidence"],
            "influence_reason": discourse_result.get("influence_reason", ""),
            "score": results[idx]["score"],
        }

    dlog("discourse round=%s finished discourse_messages_emitted=%s", round_num, yielded)
