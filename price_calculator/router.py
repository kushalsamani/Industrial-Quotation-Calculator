"""
Pricing router module.

Routes structured, size-normalized inquiry items to the
appropriate pricing engine (pipe or fitting) and returns
a consolidated pricing DataFrame.
"""

import pandas as pd

from fittings_price_fetch import load_fittings_master, fetch_fitting_price
from pipe_price_calculation import pipe_pricing_mm  


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
        # PIPE ITEMS
        # -------------------------------------------------
        if item_type == "pipe":
            try:
                if not item.get("base_material") or not item.get("lining"):
                    raise ValueError(f"Missing base_material or lining for pipe at index {input_index}")

                df = pipe_pricing_mm(
                    item_type=item_type,
                    nb_list=[item["nb_1"]],
                    length_list=[item["length_mm"]],
                    base_material=item["base_material"],
                    lining=item["lining"],
                    condition=item["condition"]
                )

                row = df.iloc[0]

                results.append({
                    "input_index": input_index,
                    "base_material": item.get("base_material"),
                    "size_us": item.get("size_us", None),
                    "item_type": "pipe",
                    "fitting_type": None,
                    "condition": item["condition"],
                    "lining": item["lining"],                   
                    "nb_1": row["nb"],
                    "nb_2": None,
                    "length_mm": row["length_mm"],
                    "final_price": row["price_inr"],
                    "status": row["status"]
                })

            except Exception:
                results.append({
                    "input_index": input_index,
                    "size_us": item.get("size_us", None),
                    "base_material": item.get("base_material"),
                    "item_type": "pipe",
                    "fitting_type": None,
                    "condition": item["condition"],
                    "lining": None,
                    "nb_1": item.get("nb_1"),
                    "nb_2": None,
                    "length_mm": item.get("length_mm"),
                    "final_price": None,
                    "status": "error"
                })

        # -------------------------------------------------
        # Hose Pipe ITEMS
        # -------------------------------------------------

        elif item_type == "hose_pipe":
            try:
                if not item.get("base_material") or not item.get("lining"):
                    raise ValueError(f"Missing base_material or lining for pipe at index {input_index}")

                df = pipe_pricing_mm(
                    item_type=item_type,
                    nb_list=[item["nb_1"]],
                    length_list=[item["length_mm"]],
                    base_material=item["base_material"],
                    lining=item["lining"],
                    condition=item["condition"]
                )

                row = df.iloc[0]

                results.append({
                    "input_index": input_index,
                    "base_material": item.get("base_material"),
                    "size_us": item.get("size_us", None),
                    "item_type": "hose_pipe",
                    "fitting_type": None,
                    "condition": item["condition"],
                    "lining": item["lining"],                   
                    "nb_1": row["nb"],
                    "nb_2": None,
                    "length_mm": row["length_mm"],
                    "final_price": row["price_inr"],
                    "status": row["status"]
                })

            except Exception:
                results.append({
                    "input_index": input_index,
                    "size_us": item.get("size_us", None),
                    "base_material": item.get("base_material"),
                    "item_type": "hose_pipe",
                    "fitting_type": None,
                    "condition": item["condition"],
                    "lining": None,
                    "nb_1": item.get("nb_1"),
                    "nb_2": None,
                    "length_mm": item.get("length_mm"),
                    "final_price": None,
                    "status": "error"
                })


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
                    "lining": result["lining_quoted"],
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
                    "fitting_type": (f"{result['fitting_type']}_{item['angle']}" 
                                     if item.get("angle") is not None else result["fitting_type"]),
                    "condition": None,
                    "lining": None,
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


# if __name__ == "__main__":

#     structured_items = [
    # 0 - Pipe
#     {
#         "input_index": 0,
#         "size_us": "6\" × 1'-4" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 150,
#         "length_mm": 406.4
#     },

#     {
#         "input_index": 1,
#         "size_us": "4\" × 2'-2 1/8" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 100,
#         "length_mm": 663.575
#     },

#     {
#         "input_index": 2,
#         "size_us": "4\" × 2'-0" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 100,
#         "length_mm": 609.6
#     },
    
#     {
#         "input_index": 3,
#         "size_us": "4\" × 1'-11 3/4" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 100,
#         "length_mm": 603.25
#     },
#     {
#         "input_index": 4,
#         "size_us": "4\" × 1'-0 1/4" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 100,
#         "length_mm": 311.15
#     },
#     {
#         "input_index": 5,
#         "size_us": "4\" × 6 1/4\"" ,
#         "item_type": "pipe",
#         "base_material": "CS",
#         "lining": "PTFE",
#         "condition": "non_vacuum",
#         "nb_1": 100,
#         "length_mm": 158.75
#     }
# ]

# df = route_and_price_items(structured_items)
# df

