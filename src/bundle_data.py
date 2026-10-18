"""Compact reproducible data bundle; never execute or blindly extract archive paths."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from open_policy import OPEN, WORKBENCH, validate_public

BUNDLE = OPEN / "workbench.tar.gz"
MANIFEST = OPEN / "bundle_manifest.json"


def pack():
    files = sorted(WORKBENCH.rglob("*.json"))
    with tarfile.open(BUNDLE, "w:gz", compresslevel=9) as archive:
        for path in files:
            if path.name != "catalogue.json":
                validate_public(json.loads(path.read_text()))
            archive.add(path, arcname=path.relative_to(WORKBENCH).as_posix(), recursive=False)
    MANIFEST.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "sha256": hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
                "files": len(files),
                "uncompressed_bytes": sum(p.stat().st_size for p in files),
                "note": "Derived from approved sources. Per-file provenance and source fingerprints are inside the bundle. Reproduce with open_events.py and forecast_lab.py; then bundle_data.py pack.",
            },
            indent=2,
        )
        + "\n"
    )
    (WORKBENCH / ".bundle-sha256").write_text(json.loads(MANIFEST.read_text())["sha256"])
    print(f"Bundled {len(files)} JSON files in {BUNDLE.stat().st_size/1e6:.1f} MB")


def ensure():
    expected = json.loads(MANIFEST.read_text())
    digest = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    if digest != expected["sha256"]:
        raise ValueError("Public data bundle checksum mismatch")
    stamp = WORKBENCH / ".bundle-sha256"
    if (
        stamp.exists()
        and stamp.read_text() == digest
        and (WORKBENCH / "events_manifest.json").exists()
    ):
        return
    WORKBENCH.mkdir(parents=True, exist_ok=True)
    with tarfile.open(BUNDLE, "r:gz") as archive:
        members = archive.getmembers()
        size = sum(m.size for m in members)
        if (
            len(members) != expected["files"]
            or size != expected["uncompressed_bytes"]
            or size > 256 * 1024 * 1024
        ):
            raise ValueError("Unexpected bundle dimensions")
        for member in members:
            relative = PurePosixPath(member.name)
            if (
                not member.isfile()
                or relative.is_absolute()
                or ".." in relative.parts
                or len(relative.parts) > 2
                or relative.suffix != ".json"
            ):
                raise ValueError("Unsafe data bundle member")
            body = archive.extractfile(member).read()
            payload = json.loads(body)
            if relative.name != "catalogue.json":
                validate_public(payload)
            target = WORKBENCH / relative
            # CI may already have a newer result-derived forecast or immutable log.
            if target.exists() and relative.name.startswith(("forecast_", "backtest_")):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    stamp.write_text(digest)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=["pack", "unpack"])
    {"pack": pack, "unpack": ensure}[p.parse_args().operation]()
