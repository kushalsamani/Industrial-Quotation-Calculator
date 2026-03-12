from pathlib import Path
from typing import List, Union

import pandas as pd
import pdfplumber
from PIL import Image
import pytesseract


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
}


def ingest_inquiry(file_path: str) -> Union[pd.DataFrame, List[str]]:
    """
    Ingest an inquiry file.

    Returns
    -------
    - TXT files  -> List[str] (raw text lines)   [UNCHANGED]
    - All others -> pd.DataFrame (extracted tables)

    Notes
    -----
    - No semantic understanding
    - No size parsing
    - No pricing logic
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".txt":
        return _ingest_text(path)

    if ext == ".pdf":
        return _ingest_pdf_tables(path)

    if ext in {".xlsx", ".xls"}:
        return _ingest_excel_tables(path)

    if ext == ".csv":
        return _ingest_csv_tables(path)

    if ext in {".png", ".jpg", ".jpeg"}:
        return _ingest_image_tables(path)

    raise RuntimeError("Unhandled file type")


# -------------------------------------------------
# TXT INGESTION (UNCHANGED)
# -------------------------------------------------

def _ingest_text(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    return lines


# -------------------------------------------------
# PDF TABLE INGESTION
# -------------------------------------------------

def _ingest_pdf_tables(path: Path) -> pd.DataFrame:
    tables = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted_tables = page.extract_tables()
            
            for table in extracted_tables:
                if not table or len(table) < 2:
                    continue
                
                df = pd.DataFrame(table[1:])
                df = df.dropna(how="all".reset_index(drop=True))
                
                if not df.empty:
                    tables.append(df)

    return tables


# -------------------------------------------------
# EXCEL TABLE INGESTION
# -------------------------------------------------

def _ingest_excel_tables(path: Path) -> pd.DataFrame:
    tables = []

    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df = df.dropna(how="all")
        if not df.empty:
            tables.append(df)

    if not tables:
        return pd.DataFrame()

    return pd.concat(tables, ignore_index=True)


# -------------------------------------------------
# CSV TABLE INGESTION
# -------------------------------------------------

def _ingest_csv_tables(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.dropna(how="all")
    return df


# -------------------------------------------------
# IMAGE TABLE INGESTION (OCR)
# -------------------------------------------------

def _ingest_image_tables(path: Path) -> pd.DataFrame:
    image = Image.open(path)
    text = pytesseract.image_to_string(image)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    rows = [line.split() for line in lines if len(line.split()) > 1]

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.dropna(how="all")
    return df
