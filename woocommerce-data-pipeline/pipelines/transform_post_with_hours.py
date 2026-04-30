# SILVER layer — filters and cleans the post_with_hours dataset.
# This table comes from WordPress's wp_posts table, so it contains all post
# types mixed together. We narrow it down to shop orders only.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import clean_text


def transform_post_with_hours(df: pd.DataFrame) -> pd.DataFrame:
    """
    Promote post_with_hours from Bronze to Silver:
    - Keep only rows where post_type is 'shop_order'
    - Rename WordPress columns (ID, post_date) to pipeline-standard names
    - Parse the order timestamp
    - Clean up text fields
    - Drop WordPress internals that aren't useful downstream
    - Write the result to Silver — this table feeds dim_time and fact_orders_time in Gold
    """
    df = df.copy()

    # This table contains all WordPress post types — we only want WooCommerce orders
    df = df[df["post_type"] == "shop_order"].copy()

    # Rename WordPress column conventions to our pipeline's standard naming
    df["order_id"]        = pd.to_numeric(df["ID"], errors="coerce").astype("Int64")
    df["order_timestamp"] = pd.to_datetime(df["post_date"], errors="coerce")

    # Light text cleanup on the columns we're keeping
    for col in ["post_title", "post_status"]:
        if col in df.columns:
            df[col] = clean_text(df[col])

    # Drop WordPress internals — none of these add value for time or order analysis
    cols_to_drop = [
        "ID", "post_modified", "post_content", "post_excerpt",
        "post_type", "post_parent", "guid", "to_ping", "pinged",
        "post_content_filtered", "post_mime_type",
        "comment_status", "ping_status",
    ]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    write_parquet(df, f"{PATHS['silver']}/post_with_hours_silver.parquet")
    return df
