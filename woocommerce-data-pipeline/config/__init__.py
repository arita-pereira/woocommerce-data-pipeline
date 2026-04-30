# Makes 'config' a Python package and exposes the most commonly used
# path objects so other modules can import them directly from 'config'
# instead of having to reach into the submodule.
#
# Usage:
#   from config import PATHS, build_paths

from .paths import PATHS, PATHS_PATH, build_paths, ensure_dirs, path_for
