"""
inquiry_parser.py

Converts raw RFQ text (email paste, extracted PDF/Excel/image text)
directly into pricing pipeline input format via a single LLM call.

Single responsibility:  raw text / file  →  [{"desc": ..., "size": ...}]

Usage
-----
    from inquiry_parser import parse_inquiry_text, parse_inquiry_file

    # From pasted text
    items = parse_inquiry_text(raw_text)
    df = run_pricing_pipeline_us(items)

    # From a file (PDF / Excel / CSV / image)
    items = parse_inquiry_file("inquiry.pdf")
    df = run_pricing_pipeline_us(items)

    # Keep qty as a field instead of expanding
    items = parse_inquiry_text(raw_text, expand_qty=False)
    # → [{"desc": ..., "size": ..., "qty": N}, ...]
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
if not _API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

_client = genai.Client(api_key=_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


# -----------------------------------------------------------------------
# SYSTEM PROMPT
# -----------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are a piping materials expert. Convert raw RFQ (Request for Quotation)
text into a structured JSON array for a pricing system.

## Output format
Return ONLY a valid JSON array — no markdown fences, no explanation:
[
  {"desc": "<item_type>", "size": "<size_string>"},
  ...
]

One dict per line item. Ignore quantity entirely.

## desc mapping rules
Map every description to exactly one of these strings:

| desc value            | Recognise these (and similar)                             |
|-----------------------|-----------------------------------------------------------|
| "spool"               | pipe spool, spool, pipe cut to length, CS pipe, SS pipe   |
| "90 elbow"            | 90 ELL, ELL 90, 90 DEG elbow, 90° elbow, 90 ELBOW        |
| "45 elbow"            | 45 ELL, ELL 45, 45 DEG elbow, 45° elbow, 45 ELBOW        |
| "blind flange"        | blind flange, BLD FLG, FLG BLD, FLANGE BLD, BLD. FLG     |
| "reducing flange"     | reducing flange, RED. FLG, FLG RED., RED FLG              |
| "instrument tee"      | instrument tee, INSTR. TEE, INSTR TEE                     |
| "reducing tee"        | reducing tee, TEE RED, RED TEE  (two different NBs)       |
| "equal tee"           | equal tee, TEE  (same NB on all ends)                     |
| "concentric reducer"  | concentric reducer, CONC. RED, CONC RED                   |
| "eccentric reducer"   | eccentric reducer, ECC. RED, ECC RED                      |
| "hose_pipe"           | hose pipe, flexible hose, rubber hose                     |
| "spacer"              | spacer, solid spacer, ring spacer, spacer ring            |
| "plug valve"          | plug valve                                                |
| "ball valve"          | ball valve                                                |
| "check valve"         | check valve, NRV, non-return valve                        |
| "butterfly valve"     | butterfly valve, BFV                                      |
| "wye strainer"        | wye strainer, Y strainer, WY strainer                     |
| "unknown"             | anything you cannot confidently classify                  |

## size string rules

Fittings — single NB (e.g. a 6" elbow):
  → `6" x 6"`   (repeat the NB on both sides)

Fittings — two NBs (e.g. a reducer):
  → `8" x 6"`   (larger NB first)

Spools / pipe (NB × length):
  → `3" x 12'-7"`  (NB x ft-in length)
  → `3" x 8 1/8"`  (NB x pure-inch length, when length < 1 foot)
  - Strip trailing L / LG / LG. from the size field  ("12'-7"LG" → "12'-7"")
  - Preserve fractions exactly as written (3/4, 1/8, 15/16, etc.)
  - Use ft-in format when length ≥ 1 foot, inch-only when < 1 foot

Fractional NB like "1 1/2"" is valid — write it as `1 1/2" x ...`

## Special handling

DITTO: same item type as the previous non-DITTO line item.
  Use the NB / size from the DITTO line itself.
  Example:
    9 – 1" PLUG VALVE, TEFLON LINED
    2 – 2" DITTO
    4 – 3" DITTO
  → three separate dicts, all plug valve, with their respective sizes.

Ignore: quantity numbers, "N ea", "N nos", "N pcs", "N –", header rows,
  column labels (ITEM, QTY, UOM, DESCRIPTION, SIZE), page numbers,
  job titles, general notes, totals.

## Examples

Input:
  9 – 1" PLUG VALVE, 150LB, TEFLON LINED
  2 – 2" DITTO
  1 – 4" TEFLON LINED WYE STRAINER, 150LB RF

Output:
  [
    {"desc": "plug valve",   "size": "1\" x 1\""},
    {"desc": "plug valve",   "size": "2\" x 2\""},
    {"desc": "wye strainer", "size": "4\" x 4\""}
  ]

Input (table copied from email, columns separated by newlines):
  ITEM  QTY  UOM  DESCRIPTION                                     SIZE
  1     7    ea   8", 90 ELL S/40s 150# RF, 316SS+PTFE            8"
  2     2    ea   8"x6", CONC RED S/40s 150#RF, 316SS+PTFE        8"x6"
  3     1    ea   3"x12'-7"LG, MK-AP1431 S/40s 150#RF, 316SS+PTFE  3"x12'-7"LG
  4     3    ea   2"x1", RED. FLG 150# RF, 316SS+PTFE             2"x1"

Output:
  [
    {"desc": "90 elbow",           "size": "8\" x 8\""},
    {"desc": "concentric reducer", "size": "8\" x 6\""},
    {"desc": "spool",              "size": "3\" x 12'-7\""},
    {"desc": "reducing flange",    "size": "2\" x 1\""}
  ]
"""


# -----------------------------------------------------------------------
# TEXT → ITEMS  (core function)
# -----------------------------------------------------------------------

def parse_inquiry_text(raw_text: str) -> list[dict]:
    """
    Convert raw RFQ text into pricing pipeline items.

    Parameters
    ----------
    raw_text : str
        Raw inquiry text from any source (email paste, OCR output, etc.)

    Returns
    -------
    list[dict]
        [{"desc": "90 elbow", "size": '8" x 8"'}, ...]
        Items with qty > 1 are repeated accordingly.
    """
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=raw_text,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()

    start = text.find("[")
    end = text.rfind("]") + 1

    if start == -1 or end == 0:
        raise ValueError(f"LLM returned no JSON array.\nResponse was:\n{text}")

    raw_items = json.loads(text[start:end])

    return [{"desc": item["desc"], "size": item["size"]} for item in raw_items]


# -----------------------------------------------------------------------
# FILE → ITEMS  (file-based entry point)
# -----------------------------------------------------------------------

def parse_inquiry_file(file_path: str) -> list[dict]:
    """
    Extract text from a file and parse it as an RFQ inquiry.

    Supported formats: .txt, .pdf, .xlsx, .xls, .csv, .png, .jpg, .jpeg

    Parameters
    ----------
    file_path : str
        Path to the inquiry file.
    expand_qty : bool
        Passed through to parse_inquiry_text.

    Returns
    -------
    list[dict]
        Same format as parse_inquiry_text.
    """
    raw_text = _extract_text(file_path)
    return parse_inquiry_text(raw_text)


def _extract_text(file_path: str) -> str:
    """
    Extract all meaningful text from a file into a single string.
    This raw text is then handed to the LLM for semantic parsing.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if ext == ".pdf":
        import pdfplumber
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)

    if ext in {".xlsx", ".xls"}:
        import pandas as pd
        xls = pd.ExcelFile(path)
        parts = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet).dropna(how="all")
            if not df.empty:
                parts.append(df.to_string(index=False))
        return "\n\n".join(parts)

    if ext == ".csv":
        import pandas as pd
        df = pd.read_csv(path).dropna(how="all")
        return df.to_string(index=False)

    if ext in {".png", ".jpg", ".jpeg"}:
        from PIL import Image
        import pytesseract
        return pytesseract.image_to_string(Image.open(path))

    raise ValueError(f"Unsupported file type: {ext}")
