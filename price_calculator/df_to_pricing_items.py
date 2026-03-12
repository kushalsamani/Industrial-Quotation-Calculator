import pandas as pd
import re

from fittings_price_fetch import load_fittings_master


# =================================================
# Step 1: Load authoritative fitting vocabulary
# =================================================

def load_fitting_vocab() -> set[str]:
    """
    Returns the set of valid fitting_type values
    from fittings_master.csv
    """
    df = load_fittings_master()
    return set(df["fitting_type"].str.lower().unique())


# =================================================
# Step 2: Description → fitting_type normalization
# =================================================

# Ordered by priority (most specific first)
FITTING_SYNONYMS = [
    ("instrument tee", "instrument_tee"),
    ("reducing tee", "tee"),
    ("equal tee", "tee"),
    ("tee", "tee"),

    ("90 deg", "bend"),
    ("90°", "bend"),
    ("elbow", "bend"),
    ("90 elbow", "bend"),

    ("conc. reducer", "concentric_reducer"),
    ("conc reducer", "concentric_reducer"),
    ("concentric reducer", "concentric_reducer"),

    ("eccentric reducer", "eccentric_reducer"),
    ("ecc reducer", "eccentric_reducer"),

    ("blind flange", "blind"),
    ("flange blind", "blind"),

    ("cross", "cross"),
    ("spacer ring", "spacer"),
]


def normalize_fitting(description: str, fitting_vocab: set[str]) -> str:
    """
    Convert raw RFQ description into a DB-valid fitting_type.
    Fails loudly if mapping is not possible.
    """
    desc = description.lower()

    for key, value in FITTING_SYNONYMS:
        if key in desc:
            if value in fitting_vocab:
                return value
            raise ValueError(
                f"Mapped fitting '{value}' not found in fittings_master.csv"
            )

    raise ValueError(f"Unmapped fitting description: {description}")


# =================================================
# Step 3: Build size_us for fittings
# =================================================

def build_fitting_size_us(description: str) -> str:
    """
    Build size_us for fittings.
    - One size  → equal fitting (X x X)
    - Two sizes → reducing fitting (X x Y)
    """

    # Matches: 6", 1 1/2", 3 1/4"
    sizes = re.findall(
        r'\d+(?:\s*\d/\d+)?\s*"', 
        description
    )

    if not sizes:
        raise ValueError(f"No size found in description: {description}")

    sizes = [s.replace(" ", "") for s in sizes]

    # Equal fitting
    if len(sizes) == 1:
        return f'{sizes[0]} x {sizes[0]}'

    # Reducing fitting (ignore extras safely)
    return f'{sizes[0]} x {sizes[1]}'


# =================================================
# Step 4: Build size_us for spools (pipes)
# =================================================

def build_pipe_size_us(description: str, length: str) -> str:
    """
    Build size_us for spools: NB x length
    Example: 2" x 36"
    """

    # Extract NB like 1", 1 1/2", 2"
    nb_match = re.search(
        r'(\d+(?:\s*\d/\d+)?)\'\'', 
        description
    )

    if not nb_match:
        raise ValueError(f"Cannot extract pipe size from: {description}")

    nb = nb_match.group(1).replace(" ", "") + '"'
    length = length.replace("''", '"')

    return f'{nb} x {length}'


# =================================================
# Step 5: MAIN ADAPTER
# =================================================

def df_to_pricing_items(df: pd.DataFrame) -> list[dict]:
    """
    Converts LLM-generated RFQ DataFrame into
    input format for run_pricing_pipeline_us
    """

    fitting_vocab = load_fitting_vocab()
    items: list[dict] = []

    for _, row in df.iterrows():
        description = str(row["Description"])
        length = row.get("Length (inches)")

        # -------------------------
        # PIPE (SPOOL)
        # -------------------------
        if "spool" in description.lower():
            size = build_pipe_size_us(description, length)
            items.append({
                "desc": "spool",
                "size": size
            })
            continue

        # -------------------------
        # FITTING
        # -------------------------
        fitting_type = normalize_fitting(description, fitting_vocab)
        size = build_fitting_size_us(description)

        items.append({
            "desc": fitting_type,
            "size": size
        })

    return items


# =================================================
# Example usage
# =================================================
# items = df_to_pricing_items(rfq_df)
# priced_df = run_pricing_pipeline_us(items)
