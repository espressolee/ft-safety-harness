import gzip
import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canonicalize_sdist", ROOT / "scripts" / "canonicalize_sdist.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_source(path: Path, *, timestamp: int) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(
            filename="different-name", fileobj=raw, mode="wb", mtime=timestamp
        ) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        directory = tarfile.TarInfo("package/")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        directory.mtime = timestamp
        archive.addfile(directory)
        payload = b"same bytes\n"
        member = tarfile.TarInfo("package/data.txt")
        member.size = len(payload)
        member.mode = 0o644
        member.mtime = timestamp
        archive.addfile(member, io.BytesIO(payload))


def write_unsafe_source(path: Path) -> None:
    with tarfile.open(path, mode="w:gz") as archive:
        payload = b"escape\n"
        member = tarfile.TarInfo("../escape.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))


class ReleaseArtifactTests(unittest.TestCase):
    def test_canonicalization_removes_timestamp_and_owner_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_a = root / "a.tar.gz"
            source_b = root / "b.tar.gz"
            output_a = root / "canonical-a.tar.gz"
            output_b = root / "canonical-b.tar.gz"
            write_source(source_a, timestamp=1_700_000_001)
            write_source(source_b, timestamp=1_800_000_001)
            MODULE.canonicalize_sdist(source_a, output_a, 1_700_000_000)
            MODULE.canonicalize_sdist(source_b, output_b, 1_700_000_000)
            self.assertEqual(digest(output_a), digest(output_b))

            with tarfile.open(output_a, mode="r:gz") as archive:
                members = archive.getmembers()
                self.assertTrue(
                    all(member.mtime == 1_700_000_000 for member in members)
                )
                self.assertTrue(
                    all(member.uid == 0 and member.gid == 0 for member in members)
                )

    def test_canonicalization_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "unsafe.tar.gz"
            output = root / "canonical.tar.gz"
            write_unsafe_source(source)
            with self.assertRaisesRegex(ValueError, "unsafe archive member path"):
                MODULE.canonicalize_sdist(source, output, 1_700_000_000)


if __name__ == "__main__":
    unittest.main()
