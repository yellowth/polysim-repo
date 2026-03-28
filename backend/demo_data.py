import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEMO_SAMPLES_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_policy_samples.json"


@lru_cache(maxsize=1)
def _load_demo_samples() -> list[dict[str, Any]]:
    with DEMO_SAMPLES_PATH.open() as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("demo_policy_samples.json must contain a list")
    return data


def list_demo_samples() -> list[dict[str, Any]]:
    samples = []
    for sample in _load_demo_samples():
        samples.append({
            "id": sample["id"],
            "title": sample["title"],
            "topic": sample["topic"],
            "snippet": sample["snippet"],
            "aliases": sample.get("aliases", []),
        })
    return samples


def get_demo_sample(sample_id: str) -> dict[str, Any] | None:
    for sample in _load_demo_samples():
        if sample.get("id") == sample_id:
            return sample
    return None
