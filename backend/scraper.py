"""
TinyFish Web Agent integration for scraping Singapore demographic + sentiment data.
TinyFish is a browser automation API that accepts natural language goals
and returns structured JSON results from real Chromium browser sessions.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "")
# Official API host: https://docs.tinyfish.ai (POST /v1/automation/run)
TINYFISH_BASE_URL = os.getenv("TINYFISH_BASE_URL", "https://agent.tinyfish.ai").rstrip("/")
DEMO_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_tinyfish_cache.json"


def get_tinyfish_api_key() -> str:
    return os.getenv("TINYFISH_API_KEY", TINYFISH_API_KEY)


def get_tinyfish_base_url() -> str:
    return os.getenv("TINYFISH_BASE_URL", TINYFISH_BASE_URL).rstrip("/")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_topic(topic: str) -> str:
    return " ".join((topic or "").strip().lower().split())


def _load_demo_cache() -> dict[str, Any]:
    if not DEMO_CACHE_PATH.exists():
        return {"version": 1, "generated_at": None, "entries": {}}

    try:
        with DEMO_CACHE_PATH.open() as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "generated_at": None, "entries": {}}


def _save_demo_cache(cache: dict[str, Any]) -> None:
    cache["generated_at"] = _utc_now_iso()
    DEMO_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEMO_CACHE_PATH.open("w") as f:
        json.dump(cache, f, indent=2)


def get_cached_sg_sentiment(policy_topic: str) -> list[dict] | None:
    normalized = _normalize_topic(policy_topic)
    if not normalized:
        return None

    cache = _load_demo_cache()
    entries = cache.get("entries", {})

    direct = entries.get(normalized)
    if isinstance(direct, dict) and isinstance(direct.get("sentiments"), list):
        return direct["sentiments"]

    for entry in entries.values():
        if not isinstance(entry, dict):
            continue
        aliases = entry.get("aliases", [])
        if normalized in {_normalize_topic(x) for x in aliases if isinstance(x, str)}:
            sentiments = entry.get("sentiments")
            if isinstance(sentiments, list):
                return sentiments

    return None


def cache_sg_sentiment(
    policy_topic: str,
    sentiments: list[dict],
    *,
    aliases: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    mode: str = "live",
) -> None:
    normalized = _normalize_topic(policy_topic)
    if not normalized or not sentiments:
        return

    cache = _load_demo_cache()
    entries = cache.setdefault("entries", {})
    existing = entries.get(normalized, {})
    existing_aliases = existing.get("aliases", []) if isinstance(existing, dict) else []
    alias_values = [policy_topic, *(aliases or []), *(existing_aliases or [])]

    deduped_aliases = []
    seen = set()
    for alias in alias_values:
        if not isinstance(alias, str):
            continue
        key = _normalize_topic(alias)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_aliases.append(alias)

    entry = {
        "topic": policy_topic,
        "aliases": deduped_aliases,
        "updated_at": _utc_now_iso(),
        "mode": mode,
        "sentiments": sentiments,
    }
    if metadata:
        entry.update(metadata)

    entries[normalized] = entry
    _save_demo_cache(cache)


async def tinyfish_run(url: str, goal: str, browser_profile: str = "lite", timeout: float = 90.0) -> dict:
    """
    Execute a TinyFish synchronous run.
    Returns the run result or a fallback dict on error.
    """
    api_key = get_tinyfish_api_key()
    if not api_key:
        return {"error": "No TinyFish API key configured", "fallback": True}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_tinyfish_base_url()}/v1/automation/run",
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "goal": goal,
                    "browser_profile": browser_profile,
                },
                timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                # Check both infra-level and goal-level success
                if data.get("status") == "COMPLETED" and data.get("result"):
                    return data["result"]
                else:
                    return {"error": f"Run status: {data.get('status')}", "fallback": True}
            elif response.status_code == 429:
                return {"error": "TinyFish rate limit exceeded", "fallback": True}
            else:
                return {"error": f"TinyFish returned {response.status_code}", "fallback": True}
    except Exception as e:
        return {"error": str(e), "fallback": True}


async def fetch_sg_sentiment_live(policy_topic: str) -> list[dict]:
    """
    Use TinyFish to scrape real-time public sentiment about a policy topic
    from Singapore forums and social media.
    """
    reddit_goal = f"""Search for posts related to: {policy_topic}

Extract the top 10 most relevant posts. For each post return JSON:
{{
    "posts": [
        {{
            "title": "post title",
            "score": 42,
            "num_comments": 15,
            "sentiment": "positive" | "negative" | "neutral",
            "summary": "one sentence summary of the discussion",
            "url": "post url"
        }}
    ]
}}

If no relevant posts found, return {{"posts": [], "note": "No posts found for this topic"}}
Do not click any links. Only extract from the search results page."""
    hwz_goal = f"""Look for threads related to: {policy_topic}

Extract up to 10 relevant threads. Return JSON:
{{
    "threads": [
        {{
            "title": "thread title",
            "replies": 100,
            "views": 5000,
            "sentiment": "positive" | "negative" | "neutral",
            "summary": "one sentence summary"
        }}
    ]
}}

If no relevant threads found, return {{"threads": [], "note": "No threads found"}}
Do not click into any thread. Only extract from the forum listing."""

    reddit_result, hwz_result = await asyncio.gather(
        tinyfish_run(
            url="https://www.reddit.com/r/singapore/",
            goal=reddit_goal,
            browser_profile="stealth",
        ),
        tinyfish_run(
            url="https://forums.hardwarezone.com.sg/forums/eat-drink-man-woman.16/",
            goal=hwz_goal,
            browser_profile="stealth",
        ),
    )

    sentiments = []
    if not reddit_result.get("fallback"):
        for post in reddit_result.get("posts", []):
            sentiments.append({
                "source": "reddit",
                "text": post.get("title", ""),
                "sentiment": post.get("sentiment", "neutral"),
                "engagement": post.get("score", 0) + post.get("num_comments", 0),
            })

    if not hwz_result.get("fallback"):
        for thread in hwz_result.get("threads", []):
            sentiments.append({
                "source": "hwz",
                "text": thread.get("title", ""),
                "sentiment": thread.get("sentiment", "neutral"),
                "engagement": thread.get("replies", 0),
            })

    return sentiments


async def scrape_sg_sentiment(
    policy_topic: str,
    *,
    prefer_cache: bool = True,
    persist_cache: bool = True,
    aliases: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Cache-first TinyFish sentiment lookup for demo topics.
    Falls back to a live TinyFish fetch and persists successful results locally.
    """
    if prefer_cache:
        cached = get_cached_sg_sentiment(policy_topic)
        if cached is not None:
            return cached

    sentiments = await fetch_sg_sentiment_live(policy_topic)
    if sentiments and persist_cache:
        cache_sg_sentiment(policy_topic, sentiments, aliases=aliases, metadata=metadata, mode="live")
    return sentiments


async def scrape_policy_news(topic: str) -> list[dict]:
    """Scrape recent CNA news about a policy topic."""
    result = await tinyfish_run(
        url=f"https://www.channelnewsasia.com/search?q={topic.replace(' ', '+')}",
        goal=f"""Extract the top 5 news articles about: {topic}

Return JSON:
{{
    "articles": [
        {{
            "title": "article headline",
            "date": "publication date",
            "summary": "one sentence summary",
            "url": "article url"
        }}
    ]
}}

Only extract from the search results page. Do not click into articles.""",
        browser_profile="lite"
    )

    if result.get("fallback"):
        return []
    return result.get("articles", [])


async def scrape_demographics_live() -> dict:
    """
    Scrape SG demographic data live. Falls back to cached Census data.
    In practice, we already have Census CSVs so this is mainly for
    demonstrating TinyFish integration to judges.
    """
    result = await tinyfish_run(
        url="https://www.singstat.gov.sg/find-data/search-by-theme/population/population-and-population-structure/latest-data",
        goal="""Extract the key population statistics from this page.

Return JSON:
{
    "total_population": 5917000,
    "citizens": 3610000,
    "prs": 540000,
    "non_residents": 1770000,
    "median_age": 42.0,
    "source": "SingStat",
    "last_updated": "date shown on page"
}

Only extract numbers visible on the page. Do not navigate away.""",
        browser_profile="lite"
    )

    if result.get("fallback"):
        # Fall back to cached data
        path = os.path.join(os.path.dirname(__file__), "..", "data", "sg_demographics.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
    return result
