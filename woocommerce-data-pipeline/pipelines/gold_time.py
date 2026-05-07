# GOLD layer — builds the time dimension and order-time fact table.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import hour_bucket, build_time_id_from_ts


def create_dim_time(
    df_post_silver: pd.DataFrame,
    df_staff_silver: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Build the dim_time dimension table from post_with_hours_silver.

    One row per unique hour-level timestamp (time_id = YYYYMMDDHH), with all
    the temporal attributes a BI tool might want to slice by: date, year, month,
    weekday, hour bucket, weekend flag, etc.

    Args:
        df_post_silver:  post_with_hours_silver, which provides order timestamps.
        df_staff_silver: orders_with_staff_assignment_silver, which provides staff
                         assignment timestamps. Pass this to ensure every
                         assignment_time_id in fact_staff_orders has a matching
                         row in dim_time (eliminates orphan rows).
    """
    # Start with order timestamps from post_with_hours
    order_ts = (
        df_post_silver
        .rename(columns={"order_timestamp": "ts"})[["ts"]]
    )

    # If staff assignment timestamps are provided, include them too.
    # Without this, assignment_time_ids that don't coincide with an order
    # timestamp would be orphans in fact_staff_orders → dim_time.
    if df_staff_silver is not None:
        assign_ts = (
            df_staff_silver[["assignment_timestamp"]]
            .rename(columns={"assignment_timestamp": "ts"})
        )
        dim = pd.concat([order_ts, assign_ts], ignore_index=True).drop_duplicates()
    else:
        dim = order_ts.drop_duplicates()

    dim["ts"] = pd.to_datetime(dim["ts"], errors="coerce")
    dim = dim.dropna(subset=["ts"])

    # Derive all the time attributes from the parsed timestamp
    dim["order_date"]         = dim["ts"].dt.date
    dim["order_year"]         = dim["ts"].dt.year
    dim["order_month"]        = dim["ts"].dt.month
    dim["order_month_name"]   = dim["ts"].dt.strftime("%B")
    dim["order_day"]          = dim["ts"].dt.day
    dim["order_hour"]         = dim["ts"].dt.hour
    dim["order_weekday"]      = dim["ts"].dt.weekday        # 0 = Monday, 6 = Sunday
    dim["order_weekday_name"] = dim["ts"].dt.strftime("%A")
    dim["order_hour_bucket"]  = dim["order_hour"].apply(hour_bucket)
    dim["is_weekend"]         = dim["order_weekday"].apply(lambda x: x >= 5)

    # Primary key: compact integer of the form YYYYMMDDHH
    dim["time_id"] = build_time_id_from_ts(dim["ts"]).astype("Int64")

    dim = dim[[
        "time_id", "ts",
        "order_date", "order_year", "order_month", "order_month_name",
        "order_day", "order_hour", "order_hour_bucket",
        "order_weekday", "order_weekday_name", "is_weekend",
    ]].drop_duplicates(subset=["time_id"])

    write_parquet(dim, f"{PATHS['gold']}/dim_time.parquet")
    return dim


def create_fact_orders_time(df_post_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Build the fact_orders_time bridge table — one row per order with its
    timestamp and the corresponding time_id FK for joining to dim_time.
    """
    fact = df_post_silver[["order_id", "order_timestamp"]].drop_duplicates().copy()

    fact["order_timestamp"] = pd.to_datetime(fact["order_timestamp"], errors="coerce")
    fact["time_id"]         = build_time_id_from_ts(fact["order_timestamp"])

    write_parquet(fact, f"{PATHS['gold']}/fact_orders_time.parquet")
    return fact
