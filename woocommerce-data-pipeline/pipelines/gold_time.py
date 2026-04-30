# GOLD layer — builds the time dimension and order-time fact table.

import pandas as pd
from utils.io import write_parquet
from config.paths import PATHS
from utils.preprocessing import hour_bucket, build_time_id_from_ts


def create_dim_time(df_post_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Build the dim_time dimension table from post_with_hours_silver.

    One row per unique hour-level timestamp (time_id = YYYYMMDDHH), with all
    the temporal attributes a BI tool might want to slice by: date, year, month,
    weekday, hour bucket, weekend flag, etc.
    """
    # Deduplicate on the raw timestamp — one row per distinct hour we've seen
    dim = df_post_silver.rename(columns={"order_timestamp": "ts"})[["ts"]].drop_duplicates()
    dim["ts"] = pd.to_datetime(dim["ts"], errors="coerce")

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
    ]]

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
