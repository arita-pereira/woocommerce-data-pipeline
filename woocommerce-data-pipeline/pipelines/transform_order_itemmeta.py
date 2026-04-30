# SILVER layer — cleans and pivots the order_itemmeta dataset.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import clean_text, clean_numeric_col


def transform_order_itemmeta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Promote order_itemmeta from Bronze to Silver:
    - Cast IDs to nullable integers
    - Keep only the meta keys we actually care about for analysis
    - Pivot from long format (key/value rows) to wide format (one column per key)
    - Rename pivoted columns to clean, readable names
    - Cast monetary and quantity fields to the right numeric types
    - Write the result to the Silver Parquet store
    """
    df = df.copy()

    # Safe nullable integer casts
    df["meta_id"]       = pd.to_numeric(df["meta_id"],       errors="coerce").astype("Int64")
    df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce").astype("Int64")

    # Clean up whitespace in both key and value columns before filtering
    df["meta_key"]   = clean_text(df["meta_key"].astype("string"))
    df["meta_value"] = clean_text(df["meta_value"].astype("string"))

    # WooCommerce stores a lot of internal meta we don't need — keep only these
    meta_keys = [
        "_product_id", "_variation_id", "_qty",
        "_line_total", "_line_tax", "_line_subtotal", "_line_subtotal_tax",
    ]
    df = df[df["meta_key"].isin(meta_keys)].copy()

    # Pivot from long format to wide: one row per order_item_id, one column per meta key
    df_pivot = (
        df.pivot_table(
            index="order_item_id",
            columns="meta_key",
            values="meta_value",
            aggfunc="last",  # take the latest value if there are duplicates
        )
        .reset_index()
    )

    # Strip the leading underscore from WooCommerce's internal key names
    rename_map = {
        "_product_id":       "product_id",
        "_variation_id":     "variation_id",
        "_qty":              "quantity",
        "_line_total":       "line_total",
        "_line_tax":         "line_tax",
        "_line_subtotal":    "line_subtotal",
        "_line_subtotal_tax":"line_subtotal_tax",
    }
    df_pivot = df_pivot.rename(columns=rename_map)

    # Integer fields
    for c in ["product_id", "variation_id", "quantity"]:
        if c in df_pivot.columns:
            df_pivot[c] = pd.to_numeric(df_pivot[c], errors="coerce").astype("Int64")

    # Monetary fields — use clean_numeric_col to handle Spanish decimal formatting
    for c in ["line_total", "line_tax", "line_subtotal", "line_subtotal_tax"]:
        if c in df_pivot.columns:
            df_pivot[c] = clean_numeric_col(df_pivot[c])

    write_parquet(df_pivot, f"{PATHS['silver']}/order_itemmeta_silver.parquet")
    return df_pivot
