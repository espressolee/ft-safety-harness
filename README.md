# ft-safety-harness

`ft-safety-harness` repeatedly runs trusted base, candidate, and control
commands in subprocesses and preserves enough evidence to distinguish a clean
exit from a crash, timeout, malformed success, or harness failure.

It is designed for free-threaded Python extension work, where a useful report
usually needs more than “the patch passed once”:

```text
exact base + exact candidate + GIL/control arms
→ repeated subprocess trials
→ raw outputs and digests
→ explicit outcome counts
→ declared expectation check
```

This repository is the canonical source for the generic dynamic validation
runner. It deliberately does not contain private advisories, package-specific
reproducers, or research manuscripts.

## Five-minute start

The repository has no runtime dependencies. From a clean clone:

```bash
python3 scripts/qualify_release.py
```

To run the included synthetic example without installing the package:

```bash
PYTHONPATH=src python3 -m ft_safety_harness run \
  examples/basic/manifest.json \
  --output /tmp/ft-safety-result.json

PYTHONPATH=src python3 -m ft_safety_harness check-result \
  /tmp/ft-safety-result.json
```

Installed use:

```bash
python3 -m pip install .
ft-validate run manifest.json --output result.json
ft-validate check-result result.json
```

## Manifest

Commands are argument arrays and run with `shell=False`. Manifests are code
execution authority: run only manifests you trust.

```json
{
  "schema_version": "ft-safety-harness.manifest.v1",
  "name": "candidate-smoke",
  "defaults": {"trials": 3, "timeout_seconds": 5.0},
  "arms": [
    {
      "id": "candidate",
      "role": "candidate",
      "command": ["{python}", "candidate_repro.py"],
      "environment": {"PYTHON_GIL": "0"},
      "required_stdout_regex": "SURVIVED",
      "expectation": "all_clean"
    }
  ]
}
```

Supported placeholders are `{python}` and `{manifest_dir}`. Working
directories must be relative to the manifest and may not escape it.
Environment values are used for execution but omitted from the result; only
the sorted key names and an environment digest are recorded.

## Trial outcomes

| Outcome | Meaning |
|---|---|
| `CLEAN` | Exit code is allowed and required output markers matched. |
| `CRASH` | Process ended by signal or a declared crash exit code. |
| `TIMEOUT` | Deadline expired and the process group was terminated. |
| `UNDERDETERMINED` | Exit was otherwise clean but required evidence was absent. |
| `HARNESS_ERROR` | Launch failed or an undeclared nonzero exit occurred. |

A generic exit code 1 or 2 is not silently promoted to `CRASH`. An exit 0
without the required marker is not silently promoted to `CLEAN`.
Marker matching uses universal-newline normalization (`CRLF` and lone `CR` to
`LF`); the bound raw stdout/stderr artifacts are never rewritten.

## Expectations

An arm may declare one of:

- `all_clean`
- `at_least_one_crash`
- `all_timeout`
- `all_underdetermined`
- `all_harness_error`
- `none`

The run-level status is `PASS` only when every declared expectation is
satisfied. Undeclared expectations produce `UNASSESSED`, not a nominal pass.

## Evidence and provenance

Every result includes:

- tool and schema versions;
- manifest SHA-256;
- host and controller Python facts;
- `Py_GIL_DISABLED` and current GIL state when available;
- Git HEAD and top-level dirty state for `--project-root`, when available;
- exact command templates, trial timestamps, return codes, and durations;
- raw stdout/stderr paths, byte counts, and SHA-256 values;
- per-arm outcome counts and expectation status.

`check-result` recomputes artifact sizes and digests. Missing or changed raw
evidence fails verification.

Git dirty-state provenance deliberately excludes ignored files and submodule
worktrees and says so in `status_scope`; either stronger cleanliness claim
requires a separate repository-specific check.

## Relationship to static scanners

Static tools such as `ft-review-toolkit` and FT-BRL find candidate unsafe
patterns. This tool answers a narrower dynamic question: what happened when an
exact command was executed repeatedly under declared controls? Static
detection, dynamic reproduction, root-cause analysis, and security severity
remain separate evidence families.

## Claim ceiling

A `PASS` establishes only that the manifest's explicit process-outcome
expectations were met and its recorded artifacts verify. It does not establish:

- root cause;
- absence of races;
- snapshot semantics;
- exploitability or severity;
- cross-platform safety;
- an upstream maintainer's acceptance;
- a release or publication.

See [docs/RESULT_CONTRACT.md](docs/RESULT_CONTRACT.md) for the complete result
contract, [SUPPORT.md](SUPPORT.md) for measured platform support, and
[RELEASING.md](RELEASING.md) for deterministic release gates. The independent
execution workflow is in
[docs/MAINTAINER_HANDOFF.md](docs/MAINTAINER_HANDOFF.md).
