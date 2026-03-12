"""
Pricing router module.

Routes structured, size-normalized inquiry items to the
appropriate pricing engine (pipe or fitting) and returns
a consolidated pricing DataFrame.
"""

import pandas as pd

from fittings_price_fetch import load_fittings_master, fetch_fitting_price
from pipe_price_calculation import pipe_pricing_mm  


def _price_pipe_item(item: dict, item_type: str) -> dict:  # type: ignore[type-arg]
    """
    Price a single pipe or hose_pipe item. Returns one result dict.
    item_type must be 'pipe' or 'hose_pipe'.
    """
    input_index = item["input_index"]
    try:
        if not item.get("base_material") or not item.get("lining"):
            raise ValueError(f"Missing base_material or lining for {item_type} at index {input_index}")

        df = pipe_pricing_mm(
            item_type=item_type,
            nb_list=[item["nb_1"]],
            length_list=[item["length_mm"]],
            base_material=item["base_material"],
            lining=item["lining"],
            condition=item["condition"]
        )
        row = df.iloc[0]
        return {
            "input_index": input_index,
            "base_material": item.get("base_material"),
            "size_us": item.get("size_us"),
            "item_type": item_type,
            "fitting_type": None,
            "condition": item["condition"],
            "lining": item["lining"],
            "nb_1": row["nb"],
            "nb_2": None,
            "length_mm": row["length_mm"],
            "final_price": row["price_inr"],
            "status": row["status"]
        }
    except Exception:
        return {
            "input_index": input_index,
            "size_us": item.get("size_us"),
            "base_material": item.get("base_material"),
            "item_type": item_type,
            "fitting_type": None,
            "condition": item["condition"],
            "lining": item.get("lining"),
            "nb_1": item.get("nb_1"),
            "nb_2": None,
            "length_mm": item.get("length_mm"),
            "final_price": None,
            "status": "error"
        }


def route_and_price_items(structured_items: list[dict]) -> pd.DataFrame:
    """
    Route structured inquiry items to pricing engines.

    Parameters
    ----------
    structured_items : list[dict]
        Canonical inquiry items with numeric sizes already normalized.

    Returns
    -------
    pandas.DataFrame
        Consolidated pricing results preserving input order.
    """

    fittings_df = load_fittings_master()
    results = []

    for item in structured_items:
        input_index = item["input_index"]
        item_type = item["item_type"]

        # -------------------------------------------------
        # PIPE / HOSE PIPE ITEMS
        # -------------------------------------------------
        if item_type in ("pipe", "hose_pipe"):
            results.append(_price_pipe_item(item, item_type))


        # -------------------------------------------------
        # FITTING ITEMS
        # -------------------------------------------------
        elif item_type == "fitting":
            try:
                result = fetch_fitting_price(
                    fittings_df=fittings_df,
                    base_material=item["base_material"],
                    lining=item["lining"],
                    fitting_type=item["fitting_type"],
                    nb_1=item["nb_1"],
                    nb_2=item["nb_2"],
                    angle=item.get("angle")
                )

                results.append({
                    "input_index": input_index,
                    "size_us": item.get("size_us", None),
                    "base_material": item.get("base_material"),
                    "item_type": "fitting",
                    "fitting_type": (f"{result['fitting_type']}_{item['angle']}" 
                                     if item.get("angle") is not None else result["fitting_type"]),
                    "condition": None,
                    "lining": result["lining_quoted"] or result["lining_requested"],
                    "nb_1": result["nb_1"],
                    "nb_2": result["nb_2"],
                    "length_mm": None,                                                           
                    "final_price": result["final_price"],
                    "status": result["status"]
                })

            except Exception:
                results.append({
                    "input_index": input_index,
                    "size_us": item.get("size_us", None),
                    "base_material": item.get("base_material"),
                    "item_type": "fitting",
                    "fitting_type": item.get("fitting_type"),
                    "condition": None,
                    "lining": item.get("lining"),
                    "nb_1": item.get("nb_1"),
                    "nb_2": item.get("nb_2"),
                    "length_mm": None,
                    "final_price": None,
                    "status": "error"
                })

        # -------------------------------------------------
        # INVALID ITEM TYPE
        # -------------------------------------------------
        else:
            results.append({
                "input_index": input_index,
                "size_us": item.get("size_us", None),
                "base_material": item.get("base_material"),
                "item_type": item_type,
                "fitting_type": None,
                "condition": None,
                "lining": None,
                "nb_1": None,
                "nb_2": None,
                "length_mm": None,
                "final_price": None,
                "status": "invalid_item_type"
            })

    df_final = pd.DataFrame(results)
    df_final = df_final.sort_values("input_index").reset_index(drop=True)
    df_final = df_final.where(pd.notnull(df_final), "")

    return df_final



