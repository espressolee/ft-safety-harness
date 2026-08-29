# Contributing

Changes should preserve the distinction between process observation and bug
validation. A subprocess signal is evidence that a process ended by signal;
it is not by itself proof of a root cause, exploitability, or a security
severity.

Before submitting a change, run:

```bash
python3 scripts/qualify_release.py
```

Tests use `unittest` and must include a negative fixture for any new outcome or
verdict path. Do not add package-specific or embargoed reproducers to this
repository. Use synthetic fixtures or a separate private manifest.
