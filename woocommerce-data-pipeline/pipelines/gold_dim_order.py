# GOLD layer — builds the order dimension table (dim_order).

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import build_time_id_from_ts


def create_dim_order(orders_staff_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Build the dim_order dimension table from orders_with_staff_assignment_silver.

    One row per order, containing the order's own attributes (store, volume, value)
    plus a time_id foreign key that links to dim_time. Temporal breakdowns like
    year, month, weekday, etc. live in dim_time — not here.
    """
    df = orders_staff_silver.copy()

    # Safe casts for the key numeric fields
    df["order_id"]  = pd.to_numeric(df["order_id"],  errors="coerce").astype("Int64")
    df["num_items"] = pd.to_numeric(df["num_items"], errors="coerce").astype("Int64")

    # 'fecha' is the raw order date column from the source — rename it to something clearer
    df["order_timestamp"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["order_date"]      = df["order_timestamp"].dt.date

    # Build the FK that links this order to the right row in dim_time
    df["time_id"] = build_time_id_from_ts(df["order_timestamp"])

    # Keep only the columns that belong to the order itself
    dim_order = (
        df[[
            "order_id",
            "order_timestamp",
            "order_date",
            "time_id",
            "store_name",
            "num_items",
            "total_value",
        ]]
        .dropna(subset=["order_id"])       # can't have an order without an ID
        .drop_duplicates(subset=["order_id"])
        .sort_values("order_id")
        .reset_index(drop=True)
    )

    # Integrity checks before writing — better to fail loudly here than silently
    # produce bad joins downstream
    assert dim_order["order_id"].is_unique, "order_id is not unique in dim_order"

    if dim_order["time_id"].isna().any():
        raise ValueError("[VALIDATION] time_id cannot be null in dim_order")

    write_parquet(dim_order, f"{PATHS['gold']}/dim_order.parquet")
    return dim_order
