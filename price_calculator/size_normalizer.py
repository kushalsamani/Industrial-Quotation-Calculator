"""
Size normalization module.

Responsible for converting raw inquiry size strings (size in us standards)
(inches, ft-inch formats) into canonical numeric values
used by pricing engines.

This module performs NO pricing.
"""

from fractions import Fraction

# -----------------------------------------------------
# NB MAPPING (AUTHORITATIVE)
# -----------------------------------------------------

INCH_TO_NB = { # type: ignore
    1: 25,
    1.5: 40,
    2: 50,
    3: 80,
    4: 100,
    6: 150,
    8: 200,
    10: 250,
    12: 300,
}


# -----------------------------------------------------
# FT-INCH TO MM (REUSED FROM PIPE MODULE)
# -----------------------------------------------------



def ft_in_to_mm(text: str) -> float:
    """
    Convert e.g. "2'-3 1/8\"" to mm.
    Handles: 2'-3 1/8", 2'-3", 2'-0", 10'-0"
    """
    # Normalize quotes (curly/smart quotes → straight)
    text = (
        text.strip()
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'")
            .replace('\u2013', '-').replace('\u2014', '-')
            .replace('"', '')
    )

    # Split on apostrophe to get feet and inch parts
    if "'" in text:
        ft_part, in_part = text.split("'")
        feet = int(ft_part.strip())
    else:
        feet = 0
        in_part = text

    in_part = in_part.strip().replace('-', '').strip()  # remove leading dash if any

    # Parse inches: could be "3 1/8", "3", "1/8", or "0"
    total_inches = Fraction(0)
    for token in in_part.split():
        total_inches += Fraction(token)  # Fraction handles "3", "1/8", "0" all correctly

    total_inches += feet * 12

    return round(float(total_inches) * 25.4, 2)


# -----------------------------------------------------
# INCH STRING TO NB
# -----------------------------------------------------

def inch_text_to_nb(text: str) -> int:
    """
    Convert an inch size string like '6"', '1.5"', or '1 1/2"' to NB.
    Handles both decimal and fractional formats.
    """
    clean = text.replace('"', '').strip()

    try:
        inch_value = float(sum(Fraction(t) for t in clean.split()))
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"Invalid inch size: {text}")

    if inch_value not in INCH_TO_NB:
        raise ValueError(f"No NB mapping found for {inch_value}\"")

    return INCH_TO_NB[inch_value]


# -----------------------------------------------------
# SIZE PARSER (CORE FUNCTION)
# -----------------------------------------------------

def parse_size(
    size_us: str,
    item_type: str
) -> dict:
    """
    Parse size in us standards into canonical values.

    Parameters
    ----------
        size_us : str
        Original size string from inquiry.
        Example: '6" x 3\'-4 1/8"' or '6" x 6"'

    item_type : str
        Either 'pipe' or 'fitting'

    Returns
    -------
    dict
        {
            size_us,
            nb_1,
            nb_2,
            length_mm
        }
    """

    if not size_us or "x" not in size_us.lower():
        raise ValueError(f"Invalid size format: {size_us}")

    # Preserve original text for output
    normalized = size_us.lower()

    left, right = [s.strip() for s in normalized.split("x", 1)]

    # Left side is always NB for both, pipes and fittings.
    nb_1 = inch_text_to_nb(left)

    # -------------------------------------------------
    # PIPE LOGIC
    # -------------------------------------------------
    if item_type == "pipe" or item_type == "hose_pipe":
        length_mm = ft_in_to_mm(right)

        return {
            "size_us": size_us,
            "nb_1": nb_1,
            "nb_2": None,
            "length_mm": length_mm
        } # type: ignore

    # -------------------------------------------------
    # FITTING LOGIC
    # -------------------------------------------------
    elif item_type == "fitting":
        nb_2 = inch_text_to_nb(right)

        return {
            "size_us": size_us,
            "nb_1": nb_1,
            "nb_2": nb_2,
            "length_mm": None
        } # type: ignore

    else:
        raise ValueError(f"Unsupported item_type: {item_type}")
