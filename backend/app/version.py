"""The app's version and the git commit the server is running.

The version number comes from backend/pyproject.toml. The commit is read from the
repo when the server starts; where there is no git checkout (e.g. a Docker image
or AWS), set APP_COMMIT instead.
"""

import os
import subprocess
import tomllib
from functools import lru_cache
from pathlib import Path

from app.config import REPO_ROOT

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


@lru_cache
def app_version() -> str:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


@lru_cache
def app_commit() -> str | None:
    if commit := os.environ.get("APP_COMMIT"):
        return commit[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
