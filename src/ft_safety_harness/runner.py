"""Subprocess execution with raw evidence preservation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import RESULT_SCHEMA_VERSION, __version__
from .manifest import Arm, Manifest, ManifestError
from .provenance import collect_provenance, environment_digest
from .result import (
    count_outcomes,
    expectation_status,
    observed_status,
    qualification_status,
)

_SCAN_LIMIT = 8 * 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _expand_command(command: tuple[str, ...], manifest_dir: Path) -> list[str]:
    replacements = {
        "{python}": sys.executable,
        "{manifest_dir}": str(manifest_dir),
    }
    return [
        item.replace("{python}", replacements["{python}"]).replace(
            "{manifest_dir}", replacements["{manifest_dir}"]
        )
        for item in command
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_record(path: Path, output_parent: Path) -> dict[str, Any]:
    return {
        "path": os.path.relpath(path, output_parent),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _decode_for_marker_scan(data: bytes) -> str:
    return (
        data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    )


def _scan_text(path: Path) -> tuple[str, bool]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size <= _SCAN_LIMIT:
            data = handle.read()
            return _decode_for_marker_scan(data), False
        half = _SCAN_LIMIT // 2
        beginning = handle.read(half)
        handle.seek(max(0, size - half))
        ending = handle.read(half)
    text = _decode_for_marker_scan(beginning)
    text += "\n<FT_SAFETY_HARNESS_OUTPUT_TRUNCATED_FOR_MARKER_SCAN>\n"
    text += _decode_for_marker_scan(ending)
    return text, True


def _terminate_process(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    else:
        proc.terminate()
    try:
        proc.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    else:
        proc.kill()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _classify(
    arm: Arm,
    *,
    return_code: int | None,
    timed_out: bool,
    launch_error: str | None,
    stdout_text: str,
    stderr_text: str,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if launch_error is not None:
        return "HARNESS_ERROR", [launch_error]
    if timed_out:
        return "TIMEOUT", [f"deadline exceeded: {arm.timeout_seconds}s"]
    if return_code is None:
        return "HARNESS_ERROR", ["subprocess produced no return code"]
    if return_code < 0 or return_code in arm.crash_exit_codes:
        return "CRASH", [f"crash return code: {return_code}"]
    if return_code not in arm.clean_exit_codes:
        return "HARNESS_ERROR", [f"undeclared nonzero return code: {return_code}"]

    if arm.required_stdout_regex and not re.search(
        arm.required_stdout_regex, stdout_text, re.MULTILINE
    ):
        reasons.append("required stdout evidence absent")
    if arm.required_stderr_regex and not re.search(
        arm.required_stderr_regex, stderr_text, re.MULTILINE
    ):
        reasons.append("required stderr evidence absent")
    if reasons:
        return "UNDERDETERMINED", reasons
    return "CLEAN", ["allowed exit code and required evidence present"]


def _run_trial(
    arm: Arm,
    trial_index: int,
    manifest: Manifest,
    artifact_root: Path,
    output_parent: Path,
) -> dict[str, Any]:
    arm_dir = artifact_root / arm.arm_id
    arm_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = arm_dir / f"{trial_index:04d}.stdout"
    stderr_path = arm_dir / f"{trial_index:04d}.stderr"
    command = _expand_command(arm.command, manifest.path.parent)
    command_digest = hashlib.sha256(
        json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    cwd = (manifest.path.parent / arm.cwd).resolve()
    environment = os.environ.copy()
    environment.update(arm.environment)

    started_at = _utc_now()
    started = time.monotonic()
    timed_out = False
    launch_error: str | None = None
    return_code: int | None = None

    with (
        stdout_path.open("wb") as stdout_handle,
        stderr_path.open("wb") as stderr_handle,
    ):
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                start_new_session=(os.name == "posix"),
            )
        except (OSError, ValueError) as exc:
            launch_error = f"launch failed: {type(exc).__name__}: {exc}"
            stderr_handle.write((launch_error + "\n").encode())
        else:
            try:
                return_code = proc.wait(timeout=arm.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_process(proc)
                return_code = proc.returncode

    duration_seconds = time.monotonic() - started
    stdout_text, stdout_scan_truncated = _scan_text(stdout_path)
    stderr_text, stderr_scan_truncated = _scan_text(stderr_path)
    outcome, reasons = _classify(
        arm,
        return_code=return_code,
        timed_out=timed_out,
        launch_error=launch_error,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
    )
    return {
        "trial": trial_index,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "duration_seconds": round(duration_seconds, 9),
        "return_code": return_code,
        "timed_out": timed_out,
        "outcome": outcome,
        "reasons": reasons,
        "command_sha256": command_digest,
        "stdout_scan_truncated": stdout_scan_truncated,
        "stderr_scan_truncated": stderr_scan_truncated,
        "stdout": _artifact_record(stdout_path, output_parent),
        "stderr": _artifact_record(stderr_path, output_parent),
    }


def run_manifest(
    manifest: Manifest,
    *,
    output_path: Path,
    artifact_root: Path,
    project_root: Path,
) -> dict[str, Any]:
    output_path = output_path.resolve()
    artifact_root = artifact_root.resolve()
    if output_path.exists():
        raise ManifestError(f"refusing to overwrite existing result: {output_path}")
    try:
        artifact_root.relative_to(output_path.parent)
    except ValueError as exc:
        raise ManifestError(
            "artifact root must be inside the result directory"
        ) from exc
    if artifact_root == output_path.parent:
        raise ManifestError("artifact root must not be the result directory itself")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=False)

    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": {"name": "ft-safety-harness", "version": __version__},
        "run_id": str(uuid.uuid4()),
        "name": manifest.name,
        "started_at": _utc_now(),
        "finished_at": None,
        "manifest": {
            "schema_version": "ft-safety-harness.manifest.v1",
            "sha256": manifest.sha256,
            "filename": manifest.path.name,
        },
        "provenance": collect_provenance(project_root.resolve()),
        "qualification_status": None,
        "arms": [],
    }

    for arm in manifest.arms:
        trials = [
            _run_trial(
                arm,
                index,
                manifest,
                artifact_root,
                output_path.parent,
            )
            for index in range(1, arm.trials + 1)
        ]
        counts = count_outcomes(trials)
        result["arms"].append(
            {
                "id": arm.arm_id,
                "role": arm.role,
                "command_template": list(arm.command),
                "cwd": arm.cwd,
                "environment_keys": sorted(arm.environment),
                "environment_sha256": environment_digest(arm.environment),
                "trials_requested": arm.trials,
                "timeout_seconds": arm.timeout_seconds,
                "clean_exit_codes": list(arm.clean_exit_codes),
                "crash_exit_codes": list(arm.crash_exit_codes),
                "required_stdout_regex": arm.required_stdout_regex,
                "required_stderr_regex": arm.required_stderr_regex,
                "expectation": arm.expectation,
                "outcome_counts": counts,
                "observed_status": observed_status(counts),
                "expectation_status": expectation_status(
                    arm.expectation, counts, len(trials)
                ),
                "trials": trials,
            }
        )

    result["qualification_status"] = qualification_status(result["arms"])
    result["finished_at"] = _utc_now()
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, output_path)
    return result
