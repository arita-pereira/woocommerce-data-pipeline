from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Literal, Optional, Union

# Root directory for all pipeline data. Can be overridden via the BASE_DIR env variable,
# otherwise it defaults to the current working directory.
BASE_DIR = Path(os.getenv("BASE_DIR", "."))

# If a RUN_DATE is provided via environment variable, we use that date to run the pipeline
# historically (useful for backfills). Otherwise, we just use today's date.
_RUN_DATE_ENV = os.getenv("RUN_DATE")
if _RUN_DATE_ENV:
    try:
        RUN_DATE = datetime.strptime(_RUN_DATE_ENV, "%Y-%m-%d")
    except ValueError:
        raise ValueError("RUN_DATE must follow the format YYYY-MM-DD")
else:
    RUN_DATE = datetime.today()

# Handy string components of the run date, used to build partitioned folder paths.
YEAR = RUN_DATE.strftime("%Y")
MONTH = RUN_DATE.strftime("%m")
DAY = RUN_DATE.strftime("%d")


def build_paths(
    run_date: Optional[Union[str, datetime]] = None,
    base_dir: Union[str, Path] = BASE_DIR,
) -> Dict[str, Path]:
    """
    Build the folder paths for each layer of the medallion architecture
    (source → bronze → silver → gold), partitioned by date.

    Args:
        run_date: The date to build paths for. Accepts a 'YYYY-MM-DD' string,
                  a datetime object, or None (falls back to RUN_DATE).
        base_dir: Root directory under which all layer folders will be created.

    Returns:
        A dict mapping each layer name to its corresponding Path.
    """
    if run_date is None:
        dt = RUN_DATE
    elif isinstance(run_date, str):
        dt = datetime.strptime(run_date, "%Y-%m-%d")
    elif isinstance(run_date, datetime):
        dt = run_date
    else:
        raise TypeError("run_date must be None, a 'YYYY-MM-DD' string, or a datetime object")

    y, m, d = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    base = Path(base_dir)

    return {
        "source": base / "source" / y / m / d,
        "bronze": base / "bronze" / y / m / d,
        "silver": base / "silver" / y / m / d,
        "gold":   base / "gold"   / y / m / d,
    }


def ensure_dirs(paths: Dict[str, Path], exist_ok: bool = True) -> None:
    """
    Create all layer directories if they don't exist yet.
    Safe to call multiple times — it won't raise an error if they're already there.
    """
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=exist_ok)


def path_for(layer: Literal["source", "bronze", "silver", "gold"]) -> Path:
    """Quick helper to grab the path for a specific layer by name."""
    return PATHS_PATH[layer]


# Build and create all paths for today's run date on module load.
PATHS_PATH: Dict[str, Path] = build_paths()
ensure_dirs(PATHS_PATH)

# String version of the paths, handy when you need plain strings instead of Path objects
# (e.g. passing paths to external tools or config files).
PATHS: Dict[str, str] = {k: str(v) for k, v in PATHS_PATH.items()}
