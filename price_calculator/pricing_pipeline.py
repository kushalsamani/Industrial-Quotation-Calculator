
from size_normalizer import parse_size
from router import route_and_price_items
import pandas as pd



def parse_items(items):
    parsed_results = []

    for item in items:
        
        desc_lower = item["desc"].lower()

        if "hose_pipe" in desc_lower:
            item_type = "hose_pipe"
        elif "spool" in desc_lower or "pipe" in desc_lower:
            item_type = "pipe"
        else:
            item_type = "fitting"

        try:
            parsed = parse_size(
                size_us=item["size"],
                item_type=item_type
            )

            parsed_results.append({
                "description": item["desc"],
                **parsed
            })

        except Exception as e:
            parsed_results.append({
                "description": item["desc"],
                "size_us": item["size"],
                "error": str(e)
            })

    return parsed_results



def build_structured_items(parsed_results):
    structured_items = []

    for idx, item in enumerate(parsed_results):

        desc_lower = item["description"].lower()

        if "hose_pipe" in desc_lower:
            item_type = "hose_pipe"
        elif "spool" in desc_lower or "pipe" in desc_lower:
            item_type = "pipe"
        else:
            item_type = "fitting"

        base_entry = {
            "input_index": idx,
            "item_type": item_type,
            "size_us": item.get("size_us"),
            "nb_1": item.get("nb_1"),
            "nb_2": item.get("nb_2"),
            "condition": "non_vacuum",
            "length_mm": item.get("length_mm"),
            "lining": "PTFE",
            "error": item.get("error")
        }

        if item_type == "hose_pipe":
            base_entry["base_material"] = "SS304"
        else:
            base_entry["base_material"] = "CS"



        if item_type in ("pipe", "hose_pipe"):
            base_entry["fitting_type"] = None
        else:
            base_entry["fitting_type"] = item["description"]

        structured_items.append(base_entry)

    return pd.DataFrame(structured_items)


def apply_elbow_angles(df):
    df["angle"] = None

    mask_90 = df["fitting_type"].str.contains(
        "90 elbow", case=False, na=False
    )
    df.loc[mask_90, "angle"] = 90

    mask_45 = df["fitting_type"].str.contains(
        "45 elbow", case=False, na=False
    )
    df.loc[mask_45, "angle"] = 45

    return df


def normalize_fitting_types(df):
    df["fitting_type"] = df["fitting_type"].replace(
        to_replace=r"(?i)^(90|45)\s*elbow$",
        value="bend",
        regex=True
    )

    fitting_type_map = {
        "blind flange": "blind",
        "conc. reducer": "concentric_reducer",
        "conc reducer": "concentric_reducer",
        "concentric reducer": "concentric_reducer",
        "instrument tee": "instrument_tee",
        "eccentric reducer": "eccentric_reducer",
        "reducing tee": "tee",
        "spool": "pipe",
        "pipe": "pipe",
        "equal tee": "tee",
        "hose_pipe": "hose_pipe",
        "Hose": "hose_pipe",
    }

    df["fitting_type"] = (
        df["fitting_type"]
        .str.lower()
        .replace(fitting_type_map)
    )

    pipe_mask = df["fitting_type"] == "pipe" 
    df.loc[pipe_mask, "item_type"] = "pipe"
    df.loc[pipe_mask, "fitting_type"] = None

    return df


def prepare_for_router(df):
    df = df.drop(columns=["error"])

    structured_items = df.to_dict(orient="records")

    structured_items = [
        {k: (None if pd.isna(v) else (int(v) if k in ("nb_1", "nb_2") else v)) for k, v in row.items()}
        for row in structured_items
    ]

    return structured_items


def run_pricing_pipeline_us(items):
    parsed_results = parse_items(items)
    df = build_structured_items(parsed_results)
    df = apply_elbow_angles(df)
    df = normalize_fitting_types(df)
    structured_items = prepare_for_router(df)

    return route_and_price_items(structured_items)

def run_pricing_pipeline_non_us(items):
    df = build_structured_items(items)
    df = apply_elbow_angles(df)
    df = normalize_fitting_types(df)
    structured_items = prepare_for_router(df)

    return route_and_price_items(structured_items)




