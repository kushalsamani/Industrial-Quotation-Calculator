import os
import pandas as pd
import json
from google import genai
from fittings_price_fetch import load_fittings_master

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3-flash-preview"

SYSTEM_PROMPT = """
You convert arbitrary pasted text into a table.

Rules:
- Infer rows and columns if a table is implied.
- Preserve text exactly as provided.
- Do not clean, normalize, or modify values.
- If headers exist, use them.
- If headers do not exist, create reasonable column names.
- Return ONLY structured data.

Output format:
{
  "columns": [...],
  "rows": [
    [...],
    [...]
  ]
}
"""

def text_to_dataframe(raw_text: str) -> pd.DataFrame:

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            {"role": "system", "parts": [{"text": SYSTEM_PROMPT}]},
            {"role": "user", "parts": [{"text": raw_text}]},
        ],
    )

    # -----------------------------
    # SAFE response extraction
    # -----------------------------
    if not response.candidates:
        raise ValueError("No candidates returned by Gemini")

    candidate = response.candidates[0]

    if not candidate.content or not candidate.content.parts:
        raise ValueError(
            f"Gemini returned no content parts. Finish reason: {candidate.finish_reason}"
        )

    # Concatenate all text parts
    text = "".join(
        part.text for part in candidate.content.parts if hasattr(part, "text")
    ).strip()

    if not text:
        raise ValueError("Gemini returned empty text")

    # -----------------------------
    # JSON extraction
    # -----------------------------
    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in Gemini response")

    structured = json.loads(text[start:end])

    return pd.DataFrame(
        structured["rows"],
        columns=structured["columns"]
    )


