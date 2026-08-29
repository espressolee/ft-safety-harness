import json
import os
import tempfile
import unittest
from pathlib import Path

from ft_safety_harness.manifest import load_manifest
from ft_safety_harness.result import ResultError, verify_result
from ft_safety_harness.runner import run_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPOSITORY_ROOT / "examples" / "basic" / "probe.py"


class RunnerTests(unittest.TestCase):
    def write_manifest(self, root: Path, arms: list[dict]) -> Path:
        path = root / "manifest.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "ft-safety-harness.manifest.v1",
                    "name": "runner-test",
                    "defaults": {"trials": 1, "timeout_seconds": 5.0},
                    "arms": arms,
                }
            ),
            encoding="utf-8",
        )
        return path

    def arm(self, arm_id: str, mode: str, expectation: str, **extra):
        result = {
            "id": arm_id,
            "role": "fixture",
            "command": ["{python}", str(PROBE), mode],
            "expectation": expectation,
        }
        result.update(extra)
        return result

    def execute(self, root: Path, arms: list[dict]):
        manifest = load_manifest(self.write_manifest(root, arms))
        output = root / "result.json"
        result = run_manifest(
            manifest,
            output_path=output,
            artifact_root=root / "artifacts",
            project_root=REPOSITORY_ROOT,
        )
        return output, result

    def test_all_outcome_classes_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, result = self.execute(
                root,
                [
                    self.arm(
                        "clean",
                        "clean",
                        "all_clean",
                        required_stdout_regex="^SURVIVED$",
                    ),
                    self.arm(
                        "crash",
                        "declared-crash",
                        "at_least_one_crash",
                        crash_exit_codes=[99],
                    ),
                    self.arm(
                        "timeout",
                        "timeout",
                        "all_timeout",
                        timeout_seconds=0.1,
                    ),
                    self.arm(
                        "underdetermined",
                        "malformed",
                        "all_underdetermined",
                        required_stdout_regex="^SURVIVED$",
                    ),
                    self.arm("error", "error", "all_harness_error"),
                ],
            )
            verified = verify_result(output)
        self.assertEqual(result["qualification_status"], "PASS", msg=result["arms"])
        self.assertEqual(verified["qualification_status"], "PASS")
        self.assertEqual(
            [arm["observed_status"] for arm in result["arms"]],
            [
                "ALL_CLEAN",
                "CRASH_OBSERVED",
                "TIMEOUT_OBSERVED",
                "UNDERDETERMINED",
                "HARNESS_ERROR",
            ],
        )

    def test_missing_marker_is_not_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            _, result = self.execute(
                Path(directory),
                [
                    self.arm(
                        "candidate",
                        "malformed",
                        "all_clean",
                        required_stdout_regex="^SURVIVED$",
                    )
                ],
            )
        self.assertEqual(result["qualification_status"], "FAIL")
        self.assertEqual(result["arms"][0]["observed_status"], "UNDERDETERMINED")

    def test_generic_exit_two_is_harness_error_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            _, result = self.execute(
                Path(directory), [self.arm("candidate", "error", "none")]
            )
        self.assertEqual(result["arms"][0]["outcome_counts"]["HARNESS_ERROR"], 1)
        self.assertEqual(result["arms"][0]["outcome_counts"]["CRASH"], 0)

    @unittest.skipUnless(os.name == "posix", "negative signal return codes are POSIX")
    def test_negative_signal_return_code_is_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            _, result = self.execute(
                Path(directory),
                [self.arm("signal", "signal-crash", "at_least_one_crash")],
            )
        self.assertEqual(result["qualification_status"], "PASS")
        self.assertEqual(result["arms"][0]["outcome_counts"]["CRASH"], 1)

    def test_tampered_artifact_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, result = self.execute(
                root,
                [
                    self.arm(
                        "candidate",
                        "clean",
                        "all_clean",
                        required_stdout_regex="SURVIVED",
                    )
                ],
            )
            stdout_rel = result["arms"][0]["trials"][0]["stdout"]["path"]
            (output.parent / stdout_rel).write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ResultError, "drift"):
                verify_result(output)


if __name__ == "__main__":
    unittest.main()
