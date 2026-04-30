import os
from pathlib import Path
import pandas as pd


def _log(msg: str):
    """Simple prefixed logger to keep IO-related messages easy to spot in the console."""
    print(f"[IO] {msg}")


def ensure_parent_dir(path):
    """
    Make sure the parent directory of a given path exists before writing to it.
    Creates any missing folders along the way, so you don't have to do it manually.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_csv(path, sep=",", encoding=None, parse_dates=None):
    """
    Read a CSV file into a DataFrame with some sensible defaults.
    Handles common null representations ('null', 'NULL', 'Null') automatically.
    """
    return pd.read_csv(
        path,
        sep=sep,
        encoding=encoding or "utf-8",
        parse_dates=parse_dates,
        na_values=["null", "NULL", "Null"],
        keep_default_na=True,
    )


def write_parquet(df, path, index=False):
    """
    Save a DataFrame as a Parquet file. Creates the destination folder if needed.
    The index is excluded by default since it's rarely meaningful to keep it.
    """
    p = ensure_parent_dir(path)
    df.to_parquet(p, index=index)


def read_parquet(path, columns=None):
    """
    Read a Parquet file into a DataFrame. Pass a list of column names to load
    only what you need — great for keeping memory usage low on large files.
    """
    return pd.read_parquet(path, columns=columns)


def list_files(path, pattern="*.csv"):
    """
    Return a sorted list of files in a directory matching the given pattern.
    Defaults to CSV files, but you can pass any glob pattern (e.g. '*.parquet').
    """
    return sorted(Path(path).glob(pattern))
