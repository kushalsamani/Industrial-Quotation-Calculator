"""
pipe_model_trainer.py

Purpose
-------
This module owns the complete lifecycle of pipe pricing ML models.

It is the ONLY place in the system where:
- Pipe models are trained or retrained
- Model files are created or overwritten
- Data fingerprints are computed and stored
- Training logs are written

This file must NEVER be imported by runtime pricing logic.
Training must be triggered explicitly.

Core Principle
--------------
Each model represents one pricing surface defined by:
(item_type, base_material, lining, condition, nb)

Length is NOT part of the model identity.
Length is the independent variable used inside the model.

If any data point for a model group changes, the model is retrained
using ALL available data for that group.
"""

import os
import json
import hashlib
import logging
from typing import Dict, Tuple

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import joblib

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
LOG_DIR = os.path.join(BASE_DIR, "logs")

PIPES_MASTER_CSV = os.path.join(DATA_DIR, "pipes_master.csv")
FINGERPRINT_FILE = os.path.join(METADATA_DIR, "model_fingerprints.json")
TRAINING_LOG_FILE = os.path.join(LOG_DIR, "pipe_model_training.log")

# Ensure required directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------

logging.basicConfig(
    filename=TRAINING_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------

def _model_key(row: pd.Series) -> Tuple[str, str, str, str, int]:
    """
    Generate the unique model key for a pipe pricing model.

    Parameters
    ----------
    row : pd.Series
        A row from pipes_master.csv

    Returns
    -------
    tuple
        (base_material, lining, condition, nb)
    """
    return (
        row["item_type"],
        row["base_material"],
        row["lining"],
        row["condition"],
        int(row["nb"]),
    )


def _model_filename(model_key: Tuple[str, str, str, str, int]) -> str:
    """
    Generate a deterministic filename for a model.

    Example:
    pipe_CS_PTFE_non_vacuum_NB25.joblib
    hose_pipe_SS304_non_vacuum_NB25.joblib
    """
    item_type, material, lining, condition, nb = model_key
    return f"{item_type}_{material}_{lining}_{condition}_NB{nb}.joblib"


def _compute_fingerprint(df: pd.DataFrame) -> str:
    """
    Compute a deterministic fingerprint for a model's training data.

    The fingerprint is based on ALL (length_mm, price_usd) pairs.
    Order does not matter.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing length_mm and price_usd

    Returns
    -------
    str
        SHA256 fingerprint
    """
    df_sorted = df[["length_mm", "price_usd"]].sort_values(
        by=["length_mm", "price_usd"]
    ).reset_index(drop=True)

    raw_bytes = df_sorted.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def _load_existing_fingerprints() -> Dict[str, str]:
    """
    Load stored model fingerprints from disk.

    Returns
    -------
    dict
        {model_filename: fingerprint}
    """
    if not os.path.exists(FINGERPRINT_FILE):
        return {}

    with open(FINGERPRINT_FILE, "r") as f:
        return json.load(f)


def _save_fingerprints(fingerprints: Dict[str, str]) -> None:
    """
    Persist model fingerprints to disk.
    """
    with open(FINGERPRINT_FILE, "w") as f:
        json.dump(fingerprints, f, indent=2)


# ------------------------------------------------------------------
# Core Training Logic
# ------------------------------------------------------------------

def sync_pipe_models() -> None:
    """
    Synchronize pipe pricing models with pipes_master.csv.

    For each unique (item_type, base_material, lining, condition, nb):
    - Compute data fingerprint
    - If model does not exist -> train
    - If model exists and fingerprint unchanged -> skip
    - If model exists and fingerprint changed -> retrain

    Training always uses ALL available data for the model group.
    """
    if not os.path.exists(PIPES_MASTER_CSV):
        raise FileNotFoundError("pipes_master.csv not found")

    df = pd.read_csv(PIPES_MASTER_CSV)

    required_cols = {
        "item_type",
        "base_material",
        "lining",
        "condition",
        "nb",
        "length_mm",
        "price_usd",
    }
    if not required_cols.issubset(df.columns):
        raise ValueError("pipes_master.csv schema is invalid")

    existing_fingerprints = _load_existing_fingerprints()
    updated_fingerprints = dict(existing_fingerprints)

    grouped = df.groupby(
        ["item_type", "base_material", "lining", "condition", "nb"],
        dropna=False
    )

    for model_key, group_df in grouped:
        item_type, material, lining, condition, nb = model_key
        model_file = _model_filename(model_key)
        model_path = os.path.join(MODEL_DIR, model_file)

        fingerprint = _compute_fingerprint(group_df)
        previous_fingerprint = existing_fingerprints.get(model_file)

        # Decide action
        if os.path.exists(model_path) and fingerprint == previous_fingerprint:
            # Model is up-to-date
            continue

        # Train or retrain
        X = group_df[["length_mm"]].values
        y = group_df["price_usd"].values

        if len(group_df) < 2:
            logging.warning(
                f"Skipping training for {model_file} due to insufficient data"
            )
            continue

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.35, random_state=42
        )

        model = LinearRegression()
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)

        joblib.dump(model, model_path)
        updated_fingerprints[model_file] = fingerprint

        logging.info(
            f"Trained model={model_file} | "
            f"item_type={item_type}, material={material}, "
            f"material={material}, lining={lining}, "
            f"condition={condition}, nb={nb} | "
            f"rows={len(group_df)} | r2={round(r2, 4)}"
        )

    _save_fingerprints(updated_fingerprints)


# ------------------------------------------------------------------
# Script Entry Point
# ------------------------------------------------------------------

if __name__ == "__main__":
    sync_pipe_models()
