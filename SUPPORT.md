# Support matrix

## Controller runtime

The controller is standard-library-only Python and declares support for
CPython 3.10 through 3.14. A declared version is not a measured version: the
table below records only completed qualification runs.

| Controller | Host | Status |
|---|---|---|
| CPython 3.10.20 | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.11.13 | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.12.11 | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.13.5 | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.14.6 | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.13.5t | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.14.6t | macOS arm64 | `QUALIFIED` — 18/18 tests + example receipt verification |
| CPython 3.14 | Linux x86_64 | `UNMEASURED` |
| CPython 3.14 | Windows x86_64 | `UNMEASURED` |

The repository contains a 21-job standard/free-threaded GitHub Actions matrix for Linux, macOS,
and Windows. It is configuration only until the repository is pushed and the exact-head jobs run;
the table above does not promote configured jobs to measured support.

## Target runtime

The controller may launch any executable named in a trusted manifest. The
intended targets are CPython 3.13t and 3.14t, optionally paired with the same
binary under `PYTHON_GIL=1`. The controller does not infer that an executable
is free-threaded; the target command must print or otherwise establish that in
its own raw evidence.

On POSIX, negative subprocess return codes are classified as `CRASH`. Shell
wrappers that translate signals to positive codes such as 134 or 139 must list
those values in `crash_exit_codes`. Windows signal behavior is not inferred;
manifest authors must provide known crash exit codes and the support table
remains `UNMEASURED` until Windows qualification runs.
