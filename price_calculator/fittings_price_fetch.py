"""
This module is responsible for fetching prices of Pipe Fittings.

"""
from pathlib import Path
import pandas as pd


# ---------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------

# Path to the master fittings price list CSV
BASE_DIR = Path(__file__).parent
FITTINGS_MASTER_CSV = BASE_DIR / "data" / "fittings_master.csv"


# ---------------------------------------------------------------------
# Data loading utilities
# ---------------------------------------------------------------------

# Module-level cache: holds the DataFrame and the file's last-modified
# timestamp at the time it was loaded. Reloads automatically if the
# CSV file is saved/updated between calls.
_fittings_df: pd.DataFrame | None = None
_fittings_mtime: float | None = None


def load_fittings_master() -> pd.DataFrame:
    """
    Load the master fittings price list from CSV into a pandas DataFrame.

    Caches the result in memory. On every call, checks the file's
    last-modified timestamp — reloads only if the file has changed
    since the last load. Safe for long-running processes (notebooks,
    API servers) where the CSV may be updated mid-session.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing all fittings base prices with columns:
        item_type, base_material, lining, fitting_type, nb_1, nb_2,
        angle, price_inr.

    Raises
    ------
    FileNotFoundError
        If fittings_master.csv is not found.
    ValueError
        If the CSV file is empty.
    """
    global _fittings_df, _fittings_mtime

    if not FITTINGS_MASTER_CSV.exists():
        raise FileNotFoundError(
            f"Fittings master file not found at: {FITTINGS_MASTER_CSV}"
        )

    current_mtime = FITTINGS_MASTER_CSV.stat().st_mtime

    if _fittings_df is None or current_mtime != _fittings_mtime:
        df = pd.read_csv(FITTINGS_MASTER_CSV)
        if df.empty:
            raise ValueError("Fittings master CSV is empty.")
        _fittings_df = df
        _fittings_mtime = current_mtime

    return _fittings_df


def fetch_fitting_price( # type: ignore
    fittings_df: pd.DataFrame,
    base_material: str,
    lining: str,
    fitting_type: str,
    nb_1: int,
    nb_2: int,
    angle: int | None = None,
) -> dict: # type: ignore
    """
    Fetch the final price for a single fitting using an exact-match lookup.

    This function performs a deterministic lookup against the master fittings
    price table and returns the final quoted price if an exact match is found.

    At this stage:
    - No fallback logic is applied (e.g. PTFE → PFA).
    - No discount logic is applied.
    - The returned price is exactly the price stored in the master CSV.

    Parameters
    ----------
    fittings_df : pandas.DataFrame
        The master fittings price DataFrame loaded using load_fittings_master().

    base_material : str
        Base material of the fitting.
        Example: "CS"

    lining : str
        Requested lining material.
        Example: "PTFE" or "PFA"

    fitting_type : str
        Type of fitting.
        Example values:
        - "bend"
        - "tee"
        - "concentric_reducer"
        - "ball_valve"
        - "hp_bellow"

    nb_1 : int
        First nominal bore value.

    nb_2 : int
        Second nominal bore value.
        For single-size fittings, nb_1 == nb_2.

    angle : int or None, optional
        Bend angle in degrees.
        Applicable only for fitting_type = "bend".
        Expected values: 45 or 90.
        For all other fittings, this must be None.

    Returns
    -------
    dict
        A dictionary containing the pricing result.
        Keys:
        - base_material
        - fitting_type
        - lining_requested
        - lining_quoted
        - nb_1
        - nb_2
        - angle
        - final_price
        - status
    """

    # -------------------------------------------------------------
    # Step 1: Normalize inputs
    # -------------------------------------------------------------
    base_material = base_material.strip().upper()
    lining = lining.strip().upper()
    fitting_type = fitting_type.strip().lower()

    # -------------------------------------------------------------
    # Step 2: Exact-match filtering
    # -------------------------------------------------------------
    df = fittings_df[
        (fittings_df["base_material"] == base_material) &
        (fittings_df["lining"] == lining) &
        (fittings_df["fitting_type"] == fitting_type) &
        (fittings_df["nb_1"] == nb_1) &
        (fittings_df["nb_2"] == nb_2)
    ]

    # Angle handling
    if fitting_type == "bend":
        df = df[df["angle"] == angle]
    else:
        df = df[df["angle"].isna()]

        # -------------------------------------------------------------
    # Step 3: Exact match handling
    # -------------------------------------------------------------
    if not df.empty:
        row = df.iloc[0]
        return {
            "base_material": base_material,
            "fitting_type": fitting_type,
            "lining_requested": lining,
            "lining_quoted": lining,
            "nb_1": nb_1,
            "nb_2": nb_2,
            "angle": angle,
            "final_price": int(row["price_inr"]),
            "status": "exact_match"
        } # type: ignore

    # -------------------------------------------------------------
    # Step 4: PTFE → PFA fallback (CS material only)
    # -------------------------------------------------------------
    if base_material == "CS" and lining == "PTFE":

        fallback_df = fittings_df[
            (fittings_df["base_material"] == base_material) &
            (fittings_df["lining"] == "PFA") &
            (fittings_df["fitting_type"] == fitting_type) &
            (fittings_df["nb_1"] == nb_1) &
            (fittings_df["nb_2"] == nb_2)
        ]

        if fitting_type == "bend":
            fallback_df = fallback_df[fallback_df["angle"] == angle]
        else:
            fallback_df = fallback_df[fallback_df["angle"].isna()]

        if not fallback_df.empty:
            row = fallback_df.iloc[0]
            return {
                "base_material": base_material,
                "fitting_type": fitting_type,
                "lining_requested": lining,
                "lining_quoted": "PFA",
                "nb_1": nb_1,
                "nb_2": nb_2,
                "angle": angle,
                "final_price": int(row["price_inr"]),
                "status": "fallback_applied"                
           } # type: ignore

    # -------------------------------------------------------------
    # Step 5: Not found
    # -------------------------------------------------------------
    return {
        "base_material": base_material,
        "fitting_type": fitting_type,
        "lining_requested": lining,
        "lining_quoted": None,
        "nb_1": nb_1,
        "nb_2": nb_2,
        "angle": angle,
        "final_price": None,
        "status": "not_found",
    }
# ---------------------------------------------------------------------
# End of module