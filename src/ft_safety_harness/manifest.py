"""Strict parsing for trusted execution manifests."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import EXPECTATIONS, MANIFEST_SCHEMA_VERSION, ROLES


class ManifestError(ValueError):
    """The manifest is incomplete, ambiguous, or outside the supported contract."""


@dataclass(frozen=True)
class Defaults:
    trials: int
    timeout_seconds: float


@dataclass(frozen=True)
class Arm:
    arm_id: str
    role: str
    command: tuple[str, ...]
    cwd: str
    environment: dict[str, str]
    trials: int
    timeout_seconds: float
    required_stdout_regex: str | None
    required_stderr_regex: str | None
    clean_exit_codes: tuple[int, ...]
    crash_exit_codes: tuple[int, ...]
    expectation: str


@dataclass(frozen=True)
class Manifest:
    path: Path
    name: str
    defaults: Defaults
    arms: tuple[Arm, ...]
    sha256: str


_TOP_LEVEL_KEYS = {"schema_version", "name", "defaults", "arms"}
_DEFAULT_KEYS = {"trials", "timeout_seconds"}
_ARM_KEYS = {
    "id",
    "role",
    "command",
    "cwd",
    "environment",
    "trials",
    "timeout_seconds",
    "required_stdout_regex",
    "required_stderr_regex",
    "clean_exit_codes",
    "crash_exit_codes",
    "expectation",
}
_ARM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be a JSON object")
    return value


def _strict_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ManifestError(f"{label} contains unknown keys: {', '.join(unknown)}")


def _positive_int(value: Any, label: str, *, maximum: int = 1000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"{label} must be an integer")
    if value < 1 or value > maximum:
        raise ManifestError(f"{label} must be between 1 and {maximum}")
    return value


def _positive_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestError(f"{label} must be a number")
    result = float(value)
    if not 0 < result <= 3600:
        raise ManifestError(f"{label} must be greater than 0 and at most 3600")
    return result


def _exit_codes(
    value: Any,
    label: str,
    default: tuple[int, ...],
    *,
    allow_empty: bool = False,
) -> tuple[int, ...]:
    if value is None:
        return default
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "an integer array" if allow_empty else "a non-empty integer array"
        raise ManifestError(f"{label} must be {qualifier}")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ManifestError(f"{label} must contain only integers")
        result.append(item)
    if len(set(result)) != len(result):
        raise ManifestError(f"{label} contains duplicate values")
    return tuple(result)


def _optional_regex(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{label} must be a non-empty string")
    try:
        re.compile(value)
    except re.error as exc:
        raise ManifestError(
            f"{label} is not a valid regular expression: {exc}"
        ) from exc
    return value


def _command(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{label} must be a non-empty string array")
    if not all(isinstance(item, str) and item for item in value):
        raise ManifestError(f"{label} must contain only non-empty strings")
    return tuple(value)


def _environment(value: Any, label: str) -> dict[str, str]:
    if value is None:
        return {}
    mapping = _object(value, label)
    result: dict[str, str] = {}
    for key, item in mapping.items():
        if not isinstance(key, str) or not key:
            raise ManifestError(f"{label} keys must be non-empty strings")
        if not isinstance(item, str):
            raise ManifestError(f"{label}.{key} must be a string")
        result[key] = item
    return result


def _safe_cwd(value: Any, label: str, manifest_dir: Path) -> str:
    if value is None:
        return "."
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute():
        raise ManifestError(f"{label} must be relative to the manifest")
    resolved = (manifest_dir / path).resolve()
    try:
        resolved.relative_to(manifest_dir.resolve())
    except ValueError as exc:
        raise ManifestError(f"{label} may not escape the manifest directory") from exc
    return value


def load_manifest(path: str | Path) -> Manifest:
    manifest_path = Path(path).resolve()
    try:
        raw_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise ManifestError(f"cannot read manifest: {exc}") from exc
    try:
        raw = json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest is not valid UTF-8 JSON: {exc}") from exc

    top = _object(raw, "manifest")
    _strict_keys(top, _TOP_LEVEL_KEYS, "manifest")
    if top.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            f"schema_version must be exactly {MANIFEST_SCHEMA_VERSION!r}"
        )
    name = top.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ManifestError("manifest.name must be a non-empty string")

    defaults_raw = _object(top.get("defaults", {}), "manifest.defaults")
    _strict_keys(defaults_raw, _DEFAULT_KEYS, "manifest.defaults")
    defaults = Defaults(
        trials=_positive_int(defaults_raw.get("trials", 1), "defaults.trials"),
        timeout_seconds=_positive_float(
            defaults_raw.get("timeout_seconds", 30.0), "defaults.timeout_seconds"
        ),
    )

    arms_raw = top.get("arms")
    if not isinstance(arms_raw, list) or not arms_raw:
        raise ManifestError("manifest.arms must be a non-empty array")

    seen_ids: set[str] = set()
    arms: list[Arm] = []
    for index, item in enumerate(arms_raw):
        label = f"manifest.arms[{index}]"
        arm_raw = _object(item, label)
        _strict_keys(arm_raw, _ARM_KEYS, label)
        arm_id = arm_raw.get("id")
        if not isinstance(arm_id, str) or not _ARM_ID_RE.fullmatch(arm_id):
            raise ManifestError(f"{label}.id is not a safe identifier")
        if arm_id in seen_ids:
            raise ManifestError(f"duplicate arm id: {arm_id}")
        seen_ids.add(arm_id)

        role = arm_raw.get("role")
        if role not in ROLES:
            raise ManifestError(f"{label}.role must be one of {', '.join(ROLES)}")
        expectation = arm_raw.get("expectation", "none")
        if expectation not in EXPECTATIONS:
            raise ManifestError(
                f"{label}.expectation must be one of {', '.join(EXPECTATIONS)}"
            )

        arms.append(
            Arm(
                arm_id=arm_id,
                role=role,
                command=_command(arm_raw.get("command"), f"{label}.command"),
                cwd=_safe_cwd(arm_raw.get("cwd"), f"{label}.cwd", manifest_path.parent),
                environment=_environment(
                    arm_raw.get("environment"), f"{label}.environment"
                ),
                trials=_positive_int(
                    arm_raw.get("trials", defaults.trials), f"{label}.trials"
                ),
                timeout_seconds=_positive_float(
                    arm_raw.get("timeout_seconds", defaults.timeout_seconds),
                    f"{label}.timeout_seconds",
                ),
                required_stdout_regex=_optional_regex(
                    arm_raw.get("required_stdout_regex"),
                    f"{label}.required_stdout_regex",
                ),
                required_stderr_regex=_optional_regex(
                    arm_raw.get("required_stderr_regex"),
                    f"{label}.required_stderr_regex",
                ),
                clean_exit_codes=_exit_codes(
                    arm_raw.get("clean_exit_codes"),
                    f"{label}.clean_exit_codes",
                    (0,),
                ),
                crash_exit_codes=_exit_codes(
                    arm_raw.get("crash_exit_codes"),
                    f"{label}.crash_exit_codes",
                    (),
                    allow_empty=True,
                ),
                expectation=expectation,
            )
        )

    return Manifest(
        path=manifest_path,
        name=name.strip(),
        defaults=defaults,
        arms=tuple(arms),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
