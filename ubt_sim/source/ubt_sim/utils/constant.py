import os
from pathlib import Path


def _detect_project_root() -> Path:
    """Locate project root by searching for a directory containing assets/."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "assets").is_dir() and (parent / "source").is_dir():
            return parent
    # Fallback: assume source/ubt_sim/utils -> project root is 3 levels up
    return Path(__file__).resolve().parents[3]


def _resolve_assets_root() -> str:
    """Return env override if provided, otherwise default assets directory."""
    env_root = os.environ.get("UBT_SIM_ASSETS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve().as_posix()

    return (_detect_project_root() / "assets").resolve().as_posix()


ASSETS_ROOT = _resolve_assets_root()
