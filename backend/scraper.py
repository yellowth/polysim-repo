"""TinyFish integration for scraping Singapore demographic + sentiment data."""
import os, httpx, json

TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "")
TINYFISH_BASE_URL = os.getenv("TINYFISH_BASE_URL", "https://api.tinyfish.io")  # adjust to actual endpoint

async def tinyfish_scrape(target: str, query: str = "") -> dict:
    """
    Use TinyFish API to scrape web content.
    Adjust URL/params based on actual TinyFish API docs from the hackathon workshop.

    Targets:
    - "census": Singapore population statistics
    - "sentiment": Public sentiment from forums/social media
    - "news": Recent policy-related news
    """
    # TODO: Replace with actual TinyFish API calls after workshop
    # This is a placeholder structure — update endpoints after the 10:30 AM workshop

    targets = {
        "census": {
            "url": "https://www.singstat.gov.sg/find-data/search-by-theme/population",
            "instruction": "Extract population breakdown by age, race, housing type for Singapore"
        },
        "sentiment": {
            "urls": [
                "https://www.reddit.com/r/singapore/",
                "https://forums.hardwarezone.com.sg/forums/eat-drink-man-woman.16/"
            ],
            "instruction": f"Find public opinions and sentiment about: {query}"
        },
        "news": {
            "url": "https://www.channelnewsasia.com/singapore",
            "instruction": f"Find recent news articles about: {query}"
        }
    }

    target_config = targets.get(target, targets["news"])

    try:
        async with httpx.AsyncClient() as client:
            # Placeholder TinyFish API call structure
            response = await client.post(
                f"{TINYFISH_BASE_URL}/scrape",
                headers={"Authorization": f"Bearer {TINYFISH_API_KEY}"},
                json={
                    "url": target_config.get("url", target_config.get("urls", [""])[0]),
                    "instruction": target_config.get("instruction", ""),
                },
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"TinyFish returned {response.status_code}", "fallback": True}
    except Exception as e:
        return {"error": str(e), "fallback": True}


async def scrape_demographics() -> dict:
    """Scrape and structure SG demographic data. Falls back to cached data."""
    result = await tinyfish_scrape("census")
    if result.get("fallback"):
        # Load pre-cached demographic data
        path = os.path.join(os.path.dirname(__file__), "..", "data", "sg_demographics.json")
        with open(path) as f:
            return json.load(f)
    return result

async def scrape_sentiment(policy_keywords: list[str]) -> list[dict]:
    """Scrape public sentiment about policy topics."""
    query = " ".join(policy_keywords[:5])
    result = await tinyfish_scrape("sentiment", query)
    if result.get("fallback"):
        return []  # No cached sentiment — agents run without ground-truth seeding
    return result.get("sentiments", [])
