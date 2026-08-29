import json
import tempfile
import unittest
from pathlib import Path

from ft_safety_harness.manifest import ManifestError, load_manifest


class ManifestTests(unittest.TestCase):
    def write(self, root: Path, data: dict) -> Path:
        path = root / "manifest.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def minimal(self) -> dict:
        return {
            "schema_version": "ft-safety-harness.manifest.v1",
            "name": "test",
            "arms": [
                {
                    "id": "candidate",
                    "role": "candidate",
                    "command": ["{python}", "probe.py"],
                }
            ],
        }

    def test_loads_strict_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = load_manifest(self.write(Path(directory), self.minimal()))
        self.assertEqual(manifest.name, "test")
        self.assertEqual(manifest.arms[0].trials, 1)
        self.assertEqual(manifest.arms[0].timeout_seconds, 30.0)
        self.assertEqual(len(manifest.sha256), 64)

    def test_rejects_unknown_key(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.minimal()
            data["typo"] = True
            with self.assertRaisesRegex(ManifestError, "unknown keys"):
                load_manifest(self.write(Path(directory), data))

    def test_rejects_duplicate_arm_id(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.minimal()
            data["arms"].append(dict(data["arms"][0]))
            with self.assertRaisesRegex(ManifestError, "duplicate arm id"):
                load_manifest(self.write(Path(directory), data))

    def test_rejects_cwd_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.minimal()
            data["arms"][0]["cwd"] = "../outside"
            with self.assertRaisesRegex(ManifestError, "may not escape"):
                load_manifest(self.write(Path(directory), data))

    def test_rejects_invalid_regex(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.minimal()
            data["arms"][0]["required_stdout_regex"] = "["
            with self.assertRaisesRegex(ManifestError, "valid regular expression"):
                load_manifest(self.write(Path(directory), data))


if __name__ == "__main__":
    unittest.main()
