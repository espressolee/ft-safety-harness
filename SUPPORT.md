# Support matrix

## Controller runtime

The controller is standard-library-only Python and declares support for
CPython 3.10 through 3.14. A declared version is not a measured version. The
tables below record only completed qualification runs.

### Exact-head remote qualification

GitHub Actions run
[`33244249316`](https://github.com/espressolee/ft-safety-harness/actions/runs/33244249316)
completed successfully against exact head
`3ae7d02fabcf975626967840b070c890d3dc4641` on 2026-08-29.

| Controller | GitHub-hosted runners | Status |
|---|---|---|
| CPython 3.10, 3.11, 3.12, 3.13, and 3.14 | `ubuntu-latest`, `macos-latest`, and `windows-latest` | `QUALIFIED` — 15/15 jobs |
| Free-threaded CPython 3.13t and 3.14t | `ubuntu-latest`, `macos-latest`, and `windows-latest` | `QUALIFIED` — 6/6 jobs |

Each of the 21 successful jobs ran `python scripts/qualify_release.py`, which
compiled the Python sources, ran all 20 unit tests, generated and verified an
example receipt, and parsed both bundled schemas. The runner labels are moving
GitHub environments, so this evidence is scoped to the linked run and commit;
it is not a claim about every OS image or Python patch release those labels may
select in the future.

### Local qualification

| Controller | Host | Status |
|---|---|---|
| CPython 3.10.20 | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.11.13 | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.12.11 | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.13.5 | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.14.6 | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.13.5t | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |
| CPython 3.14.6t | macOS arm64 | `QUALIFIED` — 20/20 tests + example receipt verification |

## Target runtime

The controller may launch any executable named in a trusted manifest. The
intended targets are CPython 3.13t and 3.14t, optionally paired with the same
binary under `PYTHON_GIL=1`. The controller does not infer that an executable
is free-threaded; the target command must print or otherwise establish that in
its own raw evidence.

On POSIX, negative subprocess return codes are classified as `CRASH`. Shell
wrappers that translate signals to positive codes such as 134 or 139 must list
those values in `crash_exit_codes`. The remote matrix exercises a negative
signal fixture on POSIX and explicitly declared positive crash exit codes on
all three runner families. Windows signal and exception-code meanings are not
inferred; manifest authors must still provide crash exit codes established for
their target process.
