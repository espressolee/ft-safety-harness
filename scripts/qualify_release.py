#!/usr/bin/env python3
"""Run the offline, clean-worktree release qualification in a temporary root."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"


def run(command: list[str], *, env: dict[str, str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE)
    with tempfile.TemporaryDirectory(prefix="ft-safety-harness-qualify-") as directory:
        root = Path(directory)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        compile_env = env.copy()
        compile_env["PYTHONPYCACHEPREFIX"] = str(root / "pycache")
        run(
            [sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"],
            env=compile_env,
        )
        run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            env=env,
        )
        result = root / "result.json"
        run(
            [
                sys.executable,
                "-m",
                "ft_safety_harness",
                "run",
                "examples/basic/manifest.json",
                "--output",
                str(result),
                "--project-root",
                str(ROOT),
            ],
            env=env,
        )
        run(
            [
                sys.executable,
                "-m",
                "ft_safety_harness",
                "check-result",
                str(result),
            ],
            env=env,
        )
        for kind in ("manifest", "result"):
            completed = subprocess.run(
                [sys.executable, "-m", "ft_safety_harness", "schema", kind],
                cwd=ROOT,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            json.loads(completed.stdout)

    print(
        json.dumps(
            {
                "qualification": "PASS",
                "controller_python": sys.version.split()[0],
                "platform": sys.platform,
                "network_used": False,
                "working_tree_output": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
