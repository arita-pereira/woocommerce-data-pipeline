import pandas as pd
import numpy as np
import re


def clean_text(s: pd.Series) -> pd.Series:
    """
    Tidy up a string column: strips leading/trailing whitespace and collapses
    any runs of internal spaces into a single space.
    """
    s = s.astype("string")
    s = s.str.strip()
    s = s.str.replace(r"\s+", " ", regex=True)
    return s


def normalize_string_scalar(x):
    """
    Same cleanup as clean_text, but for a single value instead of a whole column.
    Leaves NaN values untouched.
    """
    if pd.isna(x):
        return x
    x = str(x).strip()
    x = re.sub(r"\s+", " ", x)
    return x


def clean_numeric_scalar(x):
    """
    Parse a single value into a float, handling the Spanish number format
    where dots are thousand separators and commas are decimal separators
    (e.g. '1.234,56' → 1234.56). Returns NaN if the value can't be parsed.
    """
    if pd.isna(x):
        return np.nan
    x = str(x).strip()
    x = x.replace(".", "").replace(",", ".")
    try:
        return float(x)
    except Exception:
        return np.nan


def clean_numeric_col(s: pd.Series) -> pd.Series:
    """Apply clean_numeric_scalar across an entire column."""
    return s.apply(clean_numeric_scalar)


def hour_bucket(h: int) -> str:
    """
    Group an hour (0–23) into a named time-of-day bucket:
    morning (6–12), afternoon (13–19), or night (everything else).
    """
    if 6 <= h < 13:
        return "morning"
    if 13 <= h < 20:
        return "afternoon"
    return "night"


def build_time_id_from_ts(ts: pd.Series) -> pd.Series:
    """
    Build a compact integer time key from a timestamp column, formatted as YYYYMMDDhh.
    Useful for joining against a time dimension table in a data warehouse.
    """
    dt = pd.to_datetime(ts, errors="coerce")
    return (
        dt.dt.year  * 1_000_000 +
        dt.dt.month *    10_000 +
        dt.dt.day   *       100 +
        dt.dt.hour
    )


def assert_unique(df, cols, tabla=""):
    """
    Raise an error if there are duplicate rows for the given key columns.
    Good to call after joins or aggregations to catch unexpected duplicates early.
    """
    if df.duplicated(subset=cols).any():
        raise ValueError(f"[VALIDATION] {tabla}: duplicate keys found in columns {cols}")


def assert_in_range(s, low, high, label):
    """
    Raise an error if any non-null values in the series fall outside [low, high].
    Handy for sanity-checking things like percentages, ratings, or age fields.
    """
    if not s.dropna().between(low, high).all():
        raise ValueError(f"[VALIDATION] {label}: values out of expected range {low}–{high}")
