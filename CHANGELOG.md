# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic
Versioning once the first release is published.

## [Unreleased]

### Added

- Manifest-driven base, candidate, and control execution.
- Explicit `CLEAN`, `CRASH`, `TIMEOUT`, `UNDERDETERMINED`, and
  `HARNESS_ERROR` trial outcomes.
- Raw stdout/stderr artifacts with size and SHA-256 receipts.
- Host, Python, manifest, tool, and Git provenance.
- Fail-closed result verification.
- Positive and negative classifier fixtures.
- Deterministic sdist canonicalization and release-gate documentation.
