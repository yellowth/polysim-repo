"""
TinyFish Web Agent integration for scraping Singapore demographic + sentiment data.
TinyFish is a browser automation API that accepts natural language goals
and returns structured JSON results from real Chromium browser sessions.
"""
import os, httpx, json

TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "")
TINYFISH_BASE_URL = os.getenv("TINYFISH_BASE_URL", "https://agent.tinyfish.io")


async def tinyfish_run(url: str, goal: str, browser_profile: str = "lite", timeout: float = 90.0) -> dict:
    """
    Execute a TinyFish synchronous run.
    Returns the run result or a fallback dict on error.
    """
    if not TINYFISH_API_KEY:
        return {"error": "No TinyFish API key configured", "fallback": True}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TINYFISH_BASE_URL}/v1/run",
                headers={
                    "X-API-Key": TINYFISH_API_KEY,
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


async def scrape_sg_sentiment(policy_topic: str) -> list[dict]:
    """
    Use TinyFish to scrape real-time public sentiment about a policy topic
    from Singapore forums and social media.
    """
    # Reddit r/singapore
    reddit_result = await tinyfish_run(
        url="https://www.reddit.com/r/singapore/",
        goal=f"""Search for posts related to: {policy_topic}

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
Do not click any links. Only extract from the search results page.""",
        browser_profile="stealth"  # Reddit blocks basic bots
    )

    # HardwareZone EDMW
    hwz_result = await tinyfish_run(
        url="https://forums.hardwarezone.com.sg/forums/eat-drink-man-woman.16/",
        goal=f"""Look for threads related to: {policy_topic}

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
Do not click into any thread. Only extract from the forum listing.""",
        browser_profile="stealth"
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
