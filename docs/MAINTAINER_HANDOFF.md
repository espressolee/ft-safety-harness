# Maintainer handoff

The goal of a handoff is independent execution, not a screenshot of the reporter's run.

## Reporter prepares

- a manifest containing exact base, candidate, and control commands;
- package or repository revisions outside command arguments when they are sensitive;
- the smallest reproducer the disclosure policy permits;
- explicit trial counts, timeouts, required markers, and expectations;
- a statement of platforms and interpreter builds not measured.

Do not place credentials, embargoed source, or private paths in a public manifest. Environment
values are omitted from the result, but command arguments are recorded.

## Maintainer runs

```bash
ft-validate run manifest.json --output result.json --project-root /path/to/checkout
ft-validate check-result result.json
```

The maintainer should return `result.json` and its sibling artifact directory together. Either one
without the other is incomplete evidence. The reporter verifies the receipt before interpreting it.

## Interpretation checklist

- Does `provenance.git.head` match the requested source revision?
- Is `status_state` known, and does its limited `status_scope` suffice for the claim?
- Did every arm run the requested number of trials?
- Are GIL/free-threaded facts printed by the target itself in raw evidence?
- Did controls distinguish target mutation from decoy mutation and no mutation?
- Are crashes, timeouts, malformed success, and harness errors reported separately?
- Does the candidate close the measured failure without upgrading the claim to race freedom?

An independently verified receipt establishes an external reproduction of the manifest's process
outcomes. It does not transfer maintainer authority, validate a security severity, or prove that
unmeasured platforms are safe.
