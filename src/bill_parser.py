"""
Extracts structured line-item data from a hospital bill using Claude.

Unlike the AWS-cloud version, this calls the Anthropic API directly rather
than Bedrock -- Bedrock's model-invocation emulation is only available in
LocalStack's paid Pro tier, not the free/open-source version. This module
needs only ANTHROPIC_API_KEY, no AWS account of any kind.
"""
import base64
import json

import anthropic

from src.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = """You are reading a hospital bill (photo or scanned PDF page) from India.
Extract every line item you can find. Return ONLY valid JSON, no markdown fences, no commentary.

Schema:
{
  "hospital_name": string or null,
  "bill_date": string or null,
  "patient_name": string or null,
  "line_items": [
    {
      "description": string,
      "category": one of ["room_rent", "consultation", "diagnostics", "procedures", "medicines", "consumables", "other"],
      "quantity": number or null,
      "unit_price": number or null,
      "amount": number,
      "date": string or null
    }
  ],
  "subtotal": number or null,
  "discount": number or null,
  "tax": number or null,
  "total_amount": number or null,
  "extraction_confidence": one of ["high", "medium", "low"],
  "notes": string or null
}

Rules:
- If a value isn't present or illegible, use null rather than guessing.
- Categorize each item using your best judgement of standard Indian hospital billing categories.
- Include all pages' items in one line_items array.
- Set extraction_confidence to "low" if handwriting/poor scan made extraction unreliable.
"""


def _media_type_for(file_bytes: bytes) -> str:
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/jpeg"


def extract_bill(file_bytes: bytes, content_type: str | None = None) -> dict:
    media_type = content_type or _media_type_for(file_bytes)
    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")
    doc_block_type = "document" if media_type == "application/pdf" else "image"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {"type": doc_block_type, "source": {"type": "base64", "media_type": media_type, "data": encoded}},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    )

    raw_text = "".join(block.text for block in message.content if block.type == "text")
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output: {raw_text[:500]}")