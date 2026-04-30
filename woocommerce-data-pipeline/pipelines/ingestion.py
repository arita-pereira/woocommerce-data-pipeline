# BRONZE layer — reads CSVs from the source folder and saves them as Parquet
# with consistent, canonical names that the rest of the pipeline can rely on.

from pathlib import Path
from typing import Iterable, List, Optional
import re

from utils.io import read_csv, write_parquet, list_files
from config.paths import PATHS


def route_source_to_canonical(stem: str) -> Optional[str]:
    """
    Map a raw source filename (without extension) to a canonical dataset name.

    Source files often have timestamps or prefixes baked into their names
    (e.g. 'BRONZE_woocommerce_order_items_202503180953_20260303'), so we use
    keyword matching rather than exact names to stay flexible.

    Returns None if the filename doesn't match any known pattern — those files
    will be skipped during ingestion.
    """
    s = stem.lower()

    if "order_items" in s or "woocommerce_order_items" in s:
        return "order_items"

    if "order_itemmeta" in s or "woocommerce_order_itemmeta" in s:
        return "order_itemmeta"

    if "post_with_hours" in s or "posts_with_hours" in s:
        return "post_with_hours"

    if "orders_with_staff_assignment" in s or "order_with_staff_assignment" in s:
        return "orders_with_staff_assignment"

    return None


def ingest_file_from_source(src_path: Path, canonical_name: str, verbose: bool = True) -> Optional[str]:
    """
    Read a single CSV from the source folder and save it to Bronze as Parquet.
    The output filename is always the canonical name, regardless of what the
    source file was called.
    """
    dst = Path(PATHS["bronze"]) / f"{canonical_name}.parquet"

    if verbose:
        print(f"[BRONZE] Ingesting: {src_path.name} → {dst}")

    df = read_csv(src_path)
    write_parquet(df, dst)
    return canonical_name


def ingest_many(filenames: Iterable[str], verbose: bool = True) -> List[str]:
    """
    Ingest a specific list of files by name (without extension) from the
    active source folder. Useful when you want to re-run ingestion for just
    a subset of datasets rather than everything in the folder.
    """
    processed = []
    for name in filenames:
        src = Path(PATHS["source"]) / f"{name}.csv"
        if not src.exists():
            if verbose:
                print(f"[BRONZE] Source file not found, skipping: {src}")
            continue

        canonical = route_source_to_canonical(src.stem) or name  # fall back to the original name
        ok = ingest_file_from_source(src, canonical, verbose=verbose)
        if ok:
            processed.append(canonical)

    if verbose:
        print(f"[BRONZE] Done. Ingested: {processed}")
    return processed


def ingest_all_source_csv(verbose: bool = True) -> List[str]:
    """
    Scan the active source folder for all CSV files, identify each one by its
    canonical dataset name, and ingest them into Bronze as Parquet.

    Files that don't match any known pattern are skipped with a warning.
    Each dataset always lands with a fixed name (e.g. order_items.parquet),
    making downstream steps predictable regardless of the original filename.
    """
    src_dir = Path(PATHS["source"])
    files = [f for f in list_files(src_dir) if f.suffix.lower() == ".csv"]
    processed = []

    if verbose:
        print(f"[BRONZE] Source folder: {src_dir}")
        print(f"[BRONZE] Found {len(files)} CSV file(s)")

    for f in files:
        canonical = route_source_to_canonical(f.stem)
        if canonical is None:
            if verbose:
                print(f"[BRONZE][SKIP] Unrecognized file pattern, skipping: {f.name}")
            continue

        ok_name = ingest_file_from_source(f, canonical, verbose=verbose)
        if ok_name:
            processed.append(ok_name)

    if verbose:
        print(f"[BRONZE] Ingestion complete. {len(processed)} dataset(s) loaded → {processed}")

    return processed


if __name__ == "__main__":
    # Run this directly to ingest all files for today's date
    ingest_all_source_csv(verbose=True)
