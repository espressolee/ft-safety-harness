#!/usr/bin/env python3
"""Normalize an sdist tar.gz so identical trees produce identical bytes."""

from __future__ import annotations

import argparse
import gzip
import tarfile
from pathlib import Path, PurePosixPath


def canonicalize_sdist(source: Path, destination: Path, epoch: int) -> None:
    if epoch < 0:
        raise ValueError("epoch must be non-negative")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(source, mode="r:gz") as archive:
        members = sorted(archive.getmembers(), key=lambda member: member.name)
        seen_names: set[str] = set()
        for member in members:
            archive_path = PurePosixPath(member.name)
            if archive_path.is_absolute() or ".." in archive_path.parts:
                raise ValueError(f"unsafe archive member path: {member.name}")
            if member.name in seen_names:
                raise ValueError(f"duplicate archive member: {member.name}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"unsupported archive member type: {member.name}")
            seen_names.add(member.name)
        with (
            destination.open("xb") as raw_output,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_output, mtime=epoch
            ) as gzip_output,
            tarfile.open(
                fileobj=gzip_output, mode="w", format=tarfile.USTAR_FORMAT
            ) as output,
        ):
            for member in members:
                normalized = tarfile.TarInfo(member.name)
                normalized.size = member.size
                normalized.mode = member.mode
                normalized.type = member.type
                normalized.linkname = member.linkname
                normalized.mtime = epoch
                normalized.uid = 0
                normalized.gid = 0
                normalized.uname = ""
                normalized.gname = ""
                normalized.devmajor = 0
                normalized.devminor = 0
                file_object = archive.extractfile(member) if member.isfile() else None
                output.addfile(normalized, file_object)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--epoch", type=int, required=True)
    args = parser.parse_args()
    canonicalize_sdist(args.source, args.destination, args.epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
