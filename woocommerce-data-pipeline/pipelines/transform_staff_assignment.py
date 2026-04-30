# SILVER layer — cleans and standardizes the orders_with_staff_assignment dataset.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import clean_text, clean_numeric_col


def transform_staff_assignment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Promote orders_with_staff_assignment from Bronze to Silver:
    - Reconcile the three order_id columns that come out of the source join
    - Cast IDs and numeric fields to safe types
    - Parse both the order date and the staff assignment timestamp
    - Clean up store and staff name text
    - Drop raw WordPress and join-artifact columns
    - Reorder columns with the most important ones first
    - Write the result to the Silver Parquet store
    """
    df = df.copy()

    # The source data contains order_id, order_id_x, and order_id_y as a result
    # of how the upstream join was done. We cast all three and warn if they diverge.
    for col in ["order_id_x", "order_id_y", "order_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if {"order_id_x", "order_id_y", "order_id"}.issubset(df.columns):
        if not df["order_id_x"].equals(df["order_id"]):
            print("[WARN] order_id_x doesn't match order_id in some rows — check the source join")
        if not df["order_id_y"].equals(df["order_id"]):
            print("[WARN] order_id_y doesn't match order_id in some rows — check the source join")

    df["order_id"] = df["order_id"].astype("Int64")

    # Safe numeric casts for the remaining key fields
    df["staff_id"]    = pd.to_numeric(df["staff_id"],  errors="coerce").astype("Int64")
    df["num_items"]   = pd.to_numeric(df["num_items"], errors="coerce").astype("Int64")
    df["total_value"] = clean_numeric_col(df["total_value"])  # handles Spanish decimal format

    # 'fecha' is the actual order date; 'post_date' is when the staff assignment was recorded
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    if "post_date" in df.columns:
        df["assignment_timestamp"] = pd.to_datetime(df["post_date"], errors="coerce")

    # Normalize free-text fields so casing and spacing are consistent
    for col in ["store_name", "staff_name"]:
        if col in df.columns:
            df[col] = clean_text(df[col])

    # Drop join artifacts and WordPress internals we no longer need
    cols_to_drop = [
        "order_id_x", "order_id_y", "ID",
        "post_content", "post_author", "post_status",
        "post_type", "is_virtual", "post_title",
    ]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # Surface the most meaningful columns first
    cols_first = [
        "order_id", "store_name", "staff_id", "staff_name",
        "num_items", "total_value", "fecha", "assignment_timestamp",
    ]
    other_cols = [c for c in df.columns if c not in cols_first]
    df = df[cols_first + other_cols]

    write_parquet(df, f"{PATHS['silver']}/orders_with_staff_assignment_silver.parquet")
    return df
