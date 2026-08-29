__version__ = "0.1.0.dev0"

MANIFEST_SCHEMA_VERSION = "ft-safety-harness.manifest.v1"
RESULT_SCHEMA_VERSION = "ft-safety-harness.result.v1"

OUTCOMES = (
    "CLEAN",
    "CRASH",
    "TIMEOUT",
    "UNDERDETERMINED",
    "HARNESS_ERROR",
)

ROLES = ("base", "candidate", "control", "fixture")

EXPECTATIONS = (
    "all_clean",
    "at_least_one_crash",
    "all_timeout",
    "all_underdetermined",
    "all_harness_error",
    "none",
)
