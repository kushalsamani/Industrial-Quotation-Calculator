
from size_normalizer import parse_size
from router import route_and_price_items
import pandas as pd


def _detect_item_type(desc: str) -> str:
    """Infer item_type from description string. Returns 'hose_pipe', 'pipe', or 'fitting'."""
    d = desc.lower()
    if "hose_pipe" in d:
        return "hose_pipe"
    if "spool" in d or "pipe" in d:
        return "pipe"
    return "fitting"


def parse_items(items):
    """
    Parse US-format inquiry items by normalizing their size strings.

    Calls parse_size() on each item's 'size' field to extract nb_1, nb_2,
    and length_mm. Items that fail size parsing are included with an 'error'
    key so downstream steps can handle or report them.

    Parameters
    ----------
    items : list[dict]
        Raw items from parse_inquiry_text(), each with 'desc' and 'size' keys.

    Returns
    -------
    list[dict]
        Items with normalized size fields (nb_1, nb_2, length_mm, size_us)
        and a 'description' key. Failed items carry an 'error' string instead.
    """
    parsed_results = []

    for item in items:
        item_type = _detect_item_type(item["desc"])

        try:
            parsed = parse_size(
                size_us=item["size"],
                item_type=item_type
            )

            parsed_results.append({
                "description": item["desc"],
                "material": item.get("material"),
                "lining": item.get("lining") or "PTFE",
                **parsed
            })

        except Exception as e:
            parsed_results.append({
                "description": item["desc"],
                "material": item.get("material"),
                "lining": item.get("lining") or "PTFE",
                "size_us": item["size"],
                "error": str(e)
            })

    return parsed_results


def build_structured_items(parsed_results):
    """
    Convert parsed item dicts into a structured DataFrame ready for routing.

    Assigns item_type, resolves material defaults, and sets fitting_type
    (None for pipes/hose_pipes; the description string for fittings).
    This is the shared entry point for both US and non-US pipelines.

    Parameters
    ----------
    parsed_results : list[dict]
        For US: output of parse_items(). For non-US: output of
        parse_inquiry_text_non_us(), with nb_1/nb_2/length_mm already set.

    Returns
    -------
    pandas.DataFrame
        One row per item with columns: input_index, item_type, size_us,
        nb_1, nb_2, condition, length_mm, lining, base_material,
        fitting_type, error.
    """
    structured_items = []

    for idx, item in enumerate(parsed_results):

        item_type = _detect_item_type(item["description"])

        # material: use what LLM extracted; fall back to SS304 for hose_pipe, CS for everything else
        material = item.get("material")
        if not material:
            material = "SS304" if item_type == "hose_pipe" else "CS"

        base_entry = {
            "input_index": idx,
            "item_type": item_type,
            "size_us": item.get("size_us"),
            "nb_1": item.get("nb_1"),
            "nb_2": item.get("nb_2"),
            "condition": "non_vacuum",
            "length_mm": item.get("length_mm"),
            "lining": item.get("lining") or "PTFE",
            "base_material": material,
            "error": item.get("error")
        }

        if item_type in ("pipe", "hose_pipe"):
            base_entry["fitting_type"] = None
        else:
            base_entry["fitting_type"] = item["description"]

        structured_items.append(base_entry)

    return pd.DataFrame(structured_items)


def parse_fitting_type_and_angle(df):
    """
    Split bend_90 / bend_45 desc values into a base 'bend' fitting_type and a numeric angle column.

    The fittings master CSV stores all bends under fitting_type='bend' with
    a separate angle column. This step normalises the LLM output to match.

    Parameters
    ----------
    df : pandas.DataFrame
        Output of build_structured_items().

    Returns
    -------
    pandas.DataFrame
        Same DataFrame with an added 'angle' column (90, 45, or None)
        and bend rows updated to fitting_type='bend'.
    """
    df["angle"] = None

    mask_90 = df["fitting_type"] == "bend_90"
    mask_45 = df["fitting_type"] == "bend_45"
    df.loc[mask_90, "angle"] = 90
    df.loc[mask_45, "angle"] = 45
    df.loc[mask_90 | mask_45, "fitting_type"] = "bend"

    return df


def prepare_for_router(df):
    """
    Convert the structured DataFrame into a list of dicts for route_and_price_items().

    Drops the internal 'error' column, converts NaN to None, and casts
    nb_1/nb_2 to int so downstream lookups receive clean Python types.

    Parameters
    ----------
    df : pandas.DataFrame
        Output of parse_fitting_type_and_angle().

    Returns
    -------
    list[dict]
        One dict per item, safe to pass directly to route_and_price_items().
    """
    df = df.drop(columns=["error"])

    structured_items = df.to_dict(orient="records")

    structured_items = [
        {k: (None if pd.isna(v) else (int(v) if k in ("nb_1", "nb_2") else v)) for k, v in row.items()}
        for row in structured_items
    ]

    return structured_items


def run_pricing_pipeline_us(items):
    """
    Full pricing pipeline for US-format inquiries (inch/feet sizes).

    Parses size strings → builds structured DataFrame → extracts bend angles
    → routes to pricing engines.

    Parameters
    ----------
    items : list[dict]
        Output of parse_inquiry_text() or parse_inquiry_file().
        Each dict has 'desc', 'size', and optionally 'material' / 'lining'.

    Returns
    -------
    pandas.DataFrame
        Priced results from route_and_price_items().
    """
    parsed_results = parse_items(items)
    df = build_structured_items(parsed_results)
    df = parse_fitting_type_and_angle(df)
    structured_items = prepare_for_router(df)

    return route_and_price_items(structured_items)


def run_pricing_pipeline_non_us(items):
    """
    Full pricing pipeline for non-US inquiries (NB/DN integers, mm lengths).

    Skips size string parsing — nb_1, nb_2, and length_mm are already
    numeric in the input. Builds structured DataFrame → extracts bend angles
    → routes to pricing engines.

    Parameters
    ----------
    items : list[dict]
        Output of parse_inquiry_text_non_us(). Each dict has 'description',
        'nb_1', 'nb_2', 'length_mm', and optionally 'material' / 'lining'.

    Returns
    -------
    pandas.DataFrame
        Priced results from route_and_price_items().
    """
    df = build_structured_items(items)
    df = parse_fitting_type_and_angle(df)
    structured_items = prepare_for_router(df)

    return route_and_price_items(structured_items)
