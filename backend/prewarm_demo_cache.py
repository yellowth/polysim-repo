import asyncio
from pprint import pprint

from dotenv import load_dotenv

load_dotenv(".env")

from demo_data import list_demo_samples
from scraper import scrape_sg_sentiment


async def main() -> None:
    samples = list_demo_samples()
    summary = []

    for sample in samples:
        sentiments = await scrape_sg_sentiment(
            sample["topic"],
            prefer_cache=False,
            persist_cache=True,
            aliases=sample.get("aliases", []),
            metadata={"sample_id": sample["id"]},
        )
        summary.append({
            "id": sample["id"],
            "topic": sample["topic"],
            "sentiments_cached": len(sentiments),
        })

    pprint(summary)


if __name__ == "__main__":
    asyncio.run(main())
