# Releasing

No release has been published. The canonical repository is public and the
exact-head remote qualification is recorded in `SUPPORT.md`. The first release
remains blocked on an independently returned and verified maintainer receipt,
followed by explicit owner approval for the tag and publication actions.

## Candidate gate

1. Run `python3 scripts/qualify_release.py` on every locally available controller.
2. Run Ruff format/check and mypy.
3. Build sdist and wheel twice with the same `SOURCE_DATE_EPOCH`.
4. Normalize both sdists with `scripts/canonicalize_sdist.py`.
5. Require identical wheel SHA-256 values and identical normalized-sdist SHA-256 values.
6. Unpack the normalized sdist and rerun `scripts/qualify_release.py` from those bytes.
7. Install the wheel in an empty Python 3.10 environment and verify `ft-validate`, both
   bundled schemas, and the quick-start manifest.

Set `SOURCE_DATE_EPOCH` to the release commit timestamp. The standard setuptools sdist
builder currently leaves build-time metadata in the tar/gzip container; an unnormalized
sdist is therefore not the canonical release artifact even when its extracted files are
identical.

## Final release gate

- Worktree and index are clean.
- `v<version>` points exactly to `HEAD`.
- `CHANGELOG.md` has a dated version section.
- `SUPPORT.md` contains only measured platforms.
- Local candidate gate passes.
- Remote CI passes on the exact tag.
- Release archive manifest records artifact names, sizes, and SHA-256 values.
- Publishing the GitHub release or a package index upload requires explicit owner approval.
