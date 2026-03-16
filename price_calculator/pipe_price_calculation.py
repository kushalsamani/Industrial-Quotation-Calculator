"""
Purpose
-------
Runtime-safe pipe pricing module.

This module:
- Loads pretrained pipe pricing models (.joblib)
- Performs price prediction only
- Has ZERO training logic
- Has ZERO CSV access
- Has ZERO training logs

Models must be trained beforehand using pipe_model_trainer.py
"""

from pathlib import Path
import joblib
import pandas as pd
import numpy as np

# ======================================================
# CONFIG
# ======================================================

BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"

# Cache for loaded models
_MODEL_CACHE = {}


# ======================================================
# INTERNAL UTILITIES
# ======================================================

def _model_filename(
    item_type: str,
    base_material: str,
    lining: str,
    condition: str,
    nb: int
) -> str:
    """
    Generate model filename based on model identity.
    """
    return f"{item_type}_{base_material}_{lining}_{condition}_NB{nb}.joblib"


def _load_model(
    item_type: str,
    base_material: str,
    lining: str,
    condition: str,
    nb: int
):
    """
    Load a trained model from disk (cached).
    """
    key = (item_type, base_material, lining, condition, nb)

    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    model_file = MODEL_DIR / _model_filename(
        item_type, base_material, lining, condition, nb
    )

    if not model_file.exists():
        raise FileNotFoundError(f"No trained model found for "
        f"{item_type=}, {base_material=}, {lining=}, {condition=}, {nb=}"
        )

    model = joblib.load(model_file)
    _MODEL_CACHE[key] = model
    return model


# ======================================================
# CORE PREDICTION LOGIC
# ======================================================

def predict_price_mm(
    item_type: str,
    base_material: str,
    lining: str,
    nb: int,
    length_mm: float,
    condition: str 
) -> float:
    """
    Predict pipe price using pretrained model.

    Parameters
    ----------
    item_type: str
    base_material : str
    lining : str
    nb : int
    length_mm : float
    condition : str

    Returns
    -------
    float
        Predicted price in USD
    """
    model = _load_model(
        item_type, base_material, lining, condition, nb
    )

    X = np.array([[length_mm]])
    return float(model.predict(X)[0])


# ======================================================
# PUBLIC API (ROUTER-FRIENDLY)
# ======================================================

def pipe_pricing_mm(
    item_type,
    nb_list,
    length_list,
    base_material,
    lining,
    condition
):
    """
    Price pipes using pretrained ML models.

    Returns
    -------
    pd.DataFrame
        Schema compatible with router.py
    """
    if len(nb_list) != len(length_list):
        raise ValueError("NB list and length list must be same length")

    rows = []

    for nb, mm in zip(nb_list, length_list):
        try:
            price = predict_price_mm(
                item_type=item_type,
                base_material=base_material,
                lining=lining,
                nb=nb,
                length_mm=mm,
                condition=condition
            )

            rows.append({
                "nb": nb,
                "length_mm": mm,
                "condition_quoted": condition,
                "price_usd": round(price, 2),
                "status": "ok"
            })

        except Exception:
            rows.append({
                "nb": nb,
                "length_mm": mm,
                "condition_quoted": condition,
                "price_usd": np.nan,
                "status": "not_available",
            })

    return pd.DataFrame(rows)
