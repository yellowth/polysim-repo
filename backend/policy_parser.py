"""Extract structured policy provisions from PDFs and plaintext using GPT-4o."""
import asyncio
import io
import json
import pdfplumber
from openai import AsyncOpenAI

client = None

# Increased from 8000 to handle longer policy documents
MAX_TEXT_CHARS = 15000


def _get_client():
    global client
    if client is None:
        client = AsyncOpenAI()
    return client


EXTRACT_PROMPT = """Extract the key policy provisions from this document.
Return JSON: {"provisions": [{"id": 1, "title": "...", "summary": "...", "affected_groups": ["..."], "parameters": {"key": "value"}}]}
Focus on provisions that would affect residents differently based on income, age, race, housing type.
Extract 3-8 key provisions. Be specific about numbers, thresholds, amounts.
If fewer than 3 clear provisions exist, extract what you can."""


async def _call_with_retry(messages: list[dict], max_retries: int = 2) -> dict:
    """Call OpenAI with retry and exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            response = await _get_client().chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=messages,
                max_tokens=2000,
            )
            result = json.loads(response.choices[0].message.content)
            provisions = result.get("provisions", [])
            # Validate structure
            for i, p in enumerate(provisions):
                if "id" not in p:
                    p["id"] = i + 1
                if "title" not in p:
                    p["title"] = f"Provision {i + 1}"
                if "summary" not in p:
                    p["summary"] = ""
                if "affected_groups" not in p:
                    p["affected_groups"] = []
                if "parameters" not in p:
                    p["parameters"] = {}
            return provisions
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise e
    return []


async def parse_policy_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract text from PDF, then use OpenAI to structure into provisions."""
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    return await _call_with_retry([
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": text[:MAX_TEXT_CHARS]}
    ])


async def parse_policy_text(text: str) -> list[dict]:
    """Parse raw policy text (no PDF extraction needed)."""
    return await _call_with_retry([
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": text[:MAX_TEXT_CHARS]}
    ])
