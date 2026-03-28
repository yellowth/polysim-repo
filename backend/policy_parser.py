import pdfplumber
import io, json
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def parse_policy_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract text from PDF, then use OpenAI to structure into provisions."""
    # Extract raw text
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    # Use OpenAI to extract structured provisions
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """Extract the key policy provisions from this document.
Return JSON: {"provisions": [{"id": 1, "title": "...", "summary": "...", "affected_groups": ["..."], "parameters": {"key": "value"}}]}
Focus on provisions that would affect Singapore residents differently based on income, age, race, housing type.
Extract 3-8 key provisions. Be specific about numbers, thresholds, amounts."""},
            {"role": "user", "content": text[:8000]}  # token limit guard
        ],
        max_tokens=2000
    )
    result = json.loads(response.choices[0].message.content)
    return result.get("provisions", [])
