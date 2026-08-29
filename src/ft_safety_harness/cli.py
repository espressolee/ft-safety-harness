"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from .constants import __version__
from .manifest import ManifestError, load_manifest
from .result import ResultError, verify_result
from .runner import run_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ft-validate")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="execute a trusted validation manifest")
    run.add_argument("manifest", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--artifacts-dir", type=Path)
    run.add_argument("--project-root", type=Path)

    check = subparsers.add_parser(
        "check-result", help="verify result and raw artifact bindings"
    )
    check.add_argument("result", type=Path)

    schema = subparsers.add_parser("schema", help="print a bundled JSON schema")
    schema.add_argument("kind", choices=("manifest", "result"))
    return parser


def _run(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    output = args.output.resolve()
    if output.exists():
        raise ManifestError(f"refusing to overwrite existing result: {output}")
    artifacts = (
        args.artifacts_dir.resolve()
        if args.artifacts_dir
        else output.with_name(output.stem + ".artifacts")
    )
    if artifacts.exists():
        raise ManifestError(f"refusing to overwrite existing artifacts: {artifacts}")
    try:
        artifacts.relative_to(output.parent)
    except ValueError as exc:
        raise ManifestError(
            "artifacts-dir must be inside the result directory"
        ) from exc
    if artifacts == output.parent:
        raise ManifestError("artifacts-dir must not be the result directory itself")
    project_root = (
        args.project_root.resolve()
        if args.project_root
        else manifest.path.parent.resolve()
    )
    result = run_manifest(
        manifest,
        output_path=output,
        artifact_root=artifacts,
        project_root=project_root,
    )
    print(
        json.dumps(
            {
                "result": str(output),
                "qualification_status": result["qualification_status"],
                "arms": [
                    {
                        "id": arm["id"],
                        "observed_status": arm["observed_status"],
                        "expectation_status": arm["expectation_status"],
                    }
                    for arm in result["arms"]
                ],
            },
            sort_keys=True,
        )
    )
    return {"PASS": 0, "FAIL": 1, "UNASSESSED": 3}[result["qualification_status"]]


def _check(args: argparse.Namespace) -> int:
    result = verify_result(args.result)
    print(
        json.dumps(
            {
                "result": str(args.result.resolve()),
                "verification": "PASS",
                "qualification_status": result["qualification_status"],
            },
            sort_keys=True,
        )
    )
    return 0


def _schema(args: argparse.Namespace) -> int:
    filename = f"{args.kind}-v1.schema.json"
    text = (
        resources.files("ft_safety_harness").joinpath("schemas", filename).read_text()
    )
    print(text, end="" if text.endswith("\n") else "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        if args.command == "check-result":
            return _check(args)
        if args.command == "schema":
            return _schema(args)
    except (ManifestError, ResultError) as exc:
        print(f"ft-validate: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")
