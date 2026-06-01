"""YAML configuration loader for ubt_sim tasks.

Loads task YAML configs and resolves asset paths relative to the project root.
"""

import os
from pathlib import Path
from typing import Any

import yaml


def _find_project_root() -> Path:
    """Walk up from this file to find the ubt_sim project root (contains assets/ dir)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "assets").is_dir() and (parent / "source").is_dir():
            return parent
    raise FileNotFoundError("Could not find ubt_sim project root (directory with assets/ and source/)")


PROJECT_ROOT = _find_project_root()
ASSETS_DIR = PROJECT_ROOT / "assets"
CONFIG_DIR = PROJECT_ROOT / "config"


def resolve_asset_path(relative_path: str) -> str:
    """Resolve a relative asset path to an absolute path.

    If the path is already absolute, return as-is.
    Otherwise, resolve relative to the assets/ directory.
    """
    if os.path.isabs(relative_path):
        return relative_path
    return str(ASSETS_DIR / relative_path)


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load a YAML task configuration file.

    Resolves `root_path` (if present) relative to the config file's directory.
    Adds `project_root` and `assets_dir` to the returned config.
    """
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = CONFIG_DIR / config_path

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Resolve root_path relative to the config file's directory
    if "root_path" in cfg:
        cfg["root_path"] = os.path.abspath(
            os.path.join(config_path.parent, cfg["root_path"])
        )
    else:
        cfg["root_path"] = str(ASSETS_DIR)

    cfg["project_root"] = str(PROJECT_ROOT)
    cfg["assets_dir"] = str(ASSETS_DIR)

    return cfg


def get_scene_cfg(task_config: dict[str, Any]) -> dict[str, Any]:
    """Extract scene configuration from a task config, with resolved paths."""
    scene = task_config.get("scene", {})
    if "usd_path" in scene:
        scene["usd_path_resolved"] = resolve_asset_path(scene["usd_path"])
    return scene


def get_robot_cfg(task_config: dict[str, Any]) -> dict[str, Any]:
    """Extract robot configuration from a task config, with resolved paths."""
    robot = task_config.get("robot", {})
    if "usd_path" in robot:
        robot["usd_path_resolved"] = resolve_asset_path(robot["usd_path"])
    return robot
