"""Host, controller, manifest, and source provenance."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any


def environment_digest(environment: dict[str, str]) -> str:
    payload = json.dumps(environment, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _git(project_root: Path) -> dict[str, Any]:
    def run(*args: str) -> tuple[str | None, str | None]:
        try:
            result = subprocess.run(
                ["git", "-C", str(project_root), *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
        except FileNotFoundError:
            return None, "GIT_NOT_FOUND"
        except subprocess.TimeoutExpired:
            return None, "TIMEOUT"
        except subprocess.CalledProcessError as exc:
            return None, f"NONZERO_EXIT_{exc.returncode}"
        return result.stdout.strip(), None

    head, head_error = run("rev-parse", "HEAD")
    if head is None:
        return {
            "available": False,
            "head": None,
            "head_error": head_error,
            "dirty": None,
            "status_state": "UNAVAILABLE",
            "status_error": "HEAD_UNAVAILABLE",
            "status_scope": "tracked_and_untracked_excluding_ignored_and_submodules",
        }
    status, status_error = run(
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
        "--ignore-submodules=all",
    )
    return {
        "available": True,
        "head": head,
        "head_error": None,
        "dirty": None if status is None else bool(status),
        "status_state": (
            "UNAVAILABLE" if status is None else "DIRTY" if status else "CLEAN"
        ),
        "status_error": status_error,
        "status_scope": "tracked_and_untracked_excluding_ignored_and_submodules",
    }


def collect_provenance(project_root: Path) -> dict[str, Any]:
    gil_probe = getattr(sys, "_is_gil_enabled", None)
    gil_enabled = gil_probe() if callable(gil_probe) else None
    return {
        "path_policy": "absolute_paths_omitted",
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "controller_python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "abiflags": getattr(sys, "abiflags", ""),
            "py_gil_disabled": sysconfig.get_config_var("Py_GIL_DISABLED"),
            "gil_enabled": gil_enabled,
        },
        "git": _git(project_root),
    }
