# GOLD layer — builds the staff dimension and staff-order fact table.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import clean_text, build_time_id_from_ts


def create_dim_staff(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the dim_staff dimension table from the Silver staff assignment data.

    One row per staff member, with their cleaned name, store, and the date
    range they've been active (first_seen / last_seen), derived from their
    assignment history.
    """
    dim = (
        df[["staff_id", "staff_name", "store_name", "assignment_timestamp"]]
        .dropna(subset=["staff_id"])
        .copy()
    )

    # Title-case the names so they're consistent regardless of how they came in
    dim["staff_name_clean"] = clean_text(dim["staff_name"]).str.title()

    # Summarize each staff member's activity window across all their assignments
    first_seen = dim.groupby("staff_id")["assignment_timestamp"].min().rename("first_seen_date")
    last_seen  = dim.groupby("staff_id")["assignment_timestamp"].max().rename("last_seen_date")

    dim = (
        dim.drop(columns=["assignment_timestamp"])
           .drop_duplicates(subset=["staff_id"])
           .merge(first_seen, on="staff_id", how="left")
           .merge(last_seen,  on="staff_id", how="left")
    )

    write_parquet(dim, f"{PATHS['gold']}/dim_staff.parquet")
    return dim


def create_fact_staff_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the fact_staff_orders fact table — one row per staff-order pair.

    Captures what each staff member handled (order volume and value) and
    includes an assignment_time_id FK so the assignment can be linked to
    dim_time for time-based analysis.
    """
    fact = df[[
        "order_id",
        "staff_id",
        "assignment_timestamp",
        "num_items",
        "total_value",
    ]].copy()

    # FK to dim_time, cast to Int64 to match the type used in that table
    fact["assignment_time_id"] = (
        build_time_id_from_ts(fact["assignment_timestamp"]).astype("Int64")
    )

    # Each row represents one order handled, so this metric is always 1 at
    # the grain of this table — useful for simple COUNT aggregations in BI tools
    fact["orders_handled"] = 1

    write_parquet(fact, f"{PATHS['gold']}/fact_staff_orders.parquet")
    return fact
