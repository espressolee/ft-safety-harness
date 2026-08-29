"""Result derivation and fail-closed artifact verification."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .constants import OUTCOMES, RESULT_SCHEMA_VERSION


class ResultError(ValueError):
    """A result or one of its bound artifacts is incomplete or inconsistent."""


def count_outcomes(trials: Iterable[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(trial.get("outcome") for trial in trials)
    return {outcome: int(counter.get(outcome, 0)) for outcome in OUTCOMES}


def observed_status(counts: dict[str, int]) -> str:
    present = [outcome for outcome, count in counts.items() if count]
    if len(present) != 1:
        return "MIXED"
    return {
        "CLEAN": "ALL_CLEAN",
        "CRASH": "CRASH_OBSERVED",
        "TIMEOUT": "TIMEOUT_OBSERVED",
        "UNDERDETERMINED": "UNDERDETERMINED",
        "HARNESS_ERROR": "HARNESS_ERROR",
    }[present[0]]


def expectation_status(expectation: str, counts: dict[str, int], total: int) -> str:
    if expectation == "none":
        return "NOT_DECLARED"
    if expectation == "all_clean":
        satisfied = counts["CLEAN"] == total
    elif expectation == "at_least_one_crash":
        satisfied = (
            counts["CRASH"] >= 1
            and counts["TIMEOUT"] == 0
            and counts["HARNESS_ERROR"] == 0
            and counts["UNDERDETERMINED"] == 0
        )
    elif expectation == "all_timeout":
        satisfied = counts["TIMEOUT"] == total
    elif expectation == "all_underdetermined":
        satisfied = counts["UNDERDETERMINED"] == total
    elif expectation == "all_harness_error":
        satisfied = counts["HARNESS_ERROR"] == total
    else:
        raise ResultError(f"unknown expectation: {expectation}")
    return "SATISFIED" if satisfied else "VIOLATED"


def qualification_status(arms: Iterable[dict[str, Any]]) -> str:
    statuses = [arm["expectation_status"] for arm in arms]
    if any(status == "VIOLATED" for status in statuses):
        return "FAIL"
    if any(status == "NOT_DECLARED" for status in statuses):
        return "UNASSESSED"
    return "PASS"


def _bound_artifact(base: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ResultError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute():
        raise ResultError(f"{label} must be relative")
    resolved = (base / path).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ResultError(f"{label} escapes the result directory") from exc
    return resolved


def _verify_artifact(
    path: Path, expected_size: Any, expected_sha: Any, label: str
) -> None:
    if not path.is_file():
        raise ResultError(f"{label} is missing: {path}")
    data = path.read_bytes()
    if expected_size != len(data):
        raise ResultError(
            f"{label} size drift: expected {expected_size}, got {len(data)}"
        )
    actual_sha = hashlib.sha256(data).hexdigest()
    if expected_sha != actual_sha:
        raise ResultError(f"{label} SHA-256 drift")


def verify_result(path: str | Path) -> dict[str, Any]:
    result_path = Path(path).resolve()
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResultError(f"cannot read result JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ResultError("result must be a JSON object")
    if data.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise ResultError(f"unsupported schema_version: {data.get('schema_version')!r}")
    arms = data.get("arms")
    if not isinstance(arms, list) or not arms:
        raise ResultError("result.arms must be a non-empty array")

    for arm_index, arm in enumerate(arms):
        if not isinstance(arm, dict):
            raise ResultError(f"arms[{arm_index}] must be an object")
        trials = arm.get("trials")
        if not isinstance(trials, list) or not trials:
            raise ResultError(f"arms[{arm_index}].trials must be non-empty")
        for trial_index, trial in enumerate(trials):
            label = f"arms[{arm_index}].trials[{trial_index}]"
            if not isinstance(trial, dict):
                raise ResultError(f"{label} must be an object")
            if trial.get("outcome") not in OUTCOMES:
                raise ResultError(f"{label}.outcome is invalid")
            for stream in ("stdout", "stderr"):
                record = trial.get(stream)
                if not isinstance(record, dict):
                    raise ResultError(f"{label}.{stream} must be an object")
                artifact = _bound_artifact(
                    result_path.parent, record.get("path"), f"{label}.{stream}.path"
                )
                _verify_artifact(
                    artifact,
                    record.get("size_bytes"),
                    record.get("sha256"),
                    f"{label}.{stream}",
                )

        recomputed_counts = count_outcomes(trials)
        if arm.get("outcome_counts") != recomputed_counts:
            raise ResultError(f"arms[{arm_index}].outcome_counts drift")
        if arm.get("observed_status") != observed_status(recomputed_counts):
            raise ResultError(f"arms[{arm_index}].observed_status drift")
        expectation = arm.get("expectation")
        if not isinstance(expectation, str):
            raise ResultError(f"arms[{arm_index}].expectation must be a string")
        recomputed_expectation = expectation_status(
            expectation, recomputed_counts, len(trials)
        )
        if arm.get("expectation_status") != recomputed_expectation:
            raise ResultError(f"arms[{arm_index}].expectation_status drift")

    if data.get("qualification_status") != qualification_status(arms):
        raise ResultError("qualification_status drift")
    return data
