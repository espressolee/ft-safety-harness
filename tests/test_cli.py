import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ft_safety_harness.cli import main

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_example_run_and_check(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                run_code = main(
                    [
                        "run",
                        str(REPOSITORY_ROOT / "examples" / "basic" / "manifest.json"),
                        "--output",
                        str(output),
                        "--project-root",
                        str(REPOSITORY_ROOT),
                    ]
                )
            summary = json.loads(stdout.getvalue())
            self.assertEqual(run_code, 0)
            self.assertEqual(summary["qualification_status"], "PASS")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                check_code = main(["check-result", str(output)])
            self.assertEqual(check_code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["verification"], "PASS")

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("{}", encoding="utf-8")
            code = main(
                [
                    "run",
                    str(REPOSITORY_ROOT / "examples" / "basic" / "manifest.json"),
                    "--output",
                    str(output),
                ]
            )
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
