# SILVER layer — cleans and structures the order_items dataset.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import clean_text


def transform_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """
    Promote order_items from Bronze to Silver:
    - Cast IDs to nullable integers
    - Split the combined 'Name - Color - Size' field into separate columns
    - Clean up whitespace in all text fields
    - Drop columns that aren't useful for analysis
    - Write the result to the Silver Parquet store
    """
    df = df.copy()

    # Cast IDs to nullable Int64 so we can handle missing values cleanly
    df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce").astype("Int64")
    df["order_id"]      = pd.to_numeric(df["order_id"], errors="coerce").astype("Int64")

    # The item name field encodes name, color, and size in a single string
    # separated by ' - ' (e.g. "Classic Tee - Red - M"). We split from the
    # right so that product names containing ' - ' don't get broken up.
    name_series = df["order_item_name"].astype("string")
    split_cols = name_series.str.rsplit(" - ", n=2, expand=True)

    # Pad to 3 columns in case some items are missing color and/or size
    if split_cols.shape[1] == 1:
        split_cols = pd.concat([
            split_cols,
            pd.Series(pd.NA, index=split_cols.index),
            pd.Series(pd.NA, index=split_cols.index),
        ], axis=1)
    elif split_cols.shape[1] == 2:
        split_cols = pd.concat([
            split_cols,
            pd.Series(pd.NA, index=split_cols.index),
        ], axis=1)

    split_cols.columns = ["_name", "_color", "_size"]

    df["order_item_name"]  = split_cols["_name"]
    df["order_item_color"] = split_cols["_color"]
    df["order_item_size"]  = split_cols["_size"]

    # Strip extra whitespace from all three new text columns
    for col in ["order_item_name", "order_item_color", "order_item_size"]:
        df[col] = clean_text(df[col])

    # Drop the item type column if present — it doesn't add analytical value
    if "order_item_type" in df.columns:
        df = df.drop(columns=["order_item_type"])

    # Bring the most important columns to the front for readability
    cols_first = [
        "order_item_id", "order_id",
        "order_item_name", "order_item_color", "order_item_size",
    ]
    other_cols = [c for c in df.columns if c not in cols_first]
    df = df[cols_first + other_cols]

    write_parquet(df, f"{PATHS['silver']}/order_items_silver.parquet")
    return df
