# Result contract

## Evidence layers

The runner reports process observations. Consumers must keep these layers
separate:

```text
trial outcome
→ arm observation
→ manifest expectation
→ engineering interpretation
→ upstream or security decision
```

Only the first three are produced by this tool.

## Run status

| Status | Contract |
|---|---|
| `PASS` | Every arm declared an expectation and every expectation matched. |
| `FAIL` | At least one declared expectation was violated. |
| `UNASSESSED` | No expectation failed, but at least one arm declared `none`. |

An expected crash fixture can therefore contribute to a qualification
`PASS`; the pass means the classifier observed the expected crash, not that the
target is safe.

## Artifact binding

Each trial binds stdout and stderr by relative path, byte count, and SHA-256.
`check-result` rejects missing files, paths escaping the result directory,
size drift, hash drift, unknown schema versions, and incomplete trial records.

The result intentionally omits environment values. It records their key names
and a digest of the key/value mapping. This preserves change detection without
copying secrets into the report. Manifest authors remain responsible for not
placing secrets in command arguments, which are recorded for reproducibility.

## Non-implications

`CLEAN` means one subprocess completed according to the manifest. It does not
mean race-free. `CRASH` means a signal or declared crash exit code was
observed. It does not identify a root cause. `TIMEOUT` does not distinguish a
deadlock from slow execution. `UNDERDETERMINED` is not a clean result.
