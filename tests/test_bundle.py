import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bundle_data


class BundleSafetyTests(unittest.TestCase):
    def archive(self, root, name, payload=b"{}", symlink=False):
        archive = root / "bundle.tar.gz"
        with tarfile.open(archive, "w:gz") as out:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            if symlink:
                member.type = tarfile.SYMTYPE
                member.linkname = "/tmp/untrusted"
                member.size = 0
            out.addfile(member, None if symlink else io.BytesIO(payload))
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "files": 1,
                    "uncompressed_bytes": 0 if symlink else len(payload),
                }
            )
        )
        return patch.multiple(
            bundle_data, BUNDLE=archive, MANIFEST=manifest, WORKBENCH=root / "expanded"
        )

    def test_rejects_traversal_and_symlinks(self):
        for name, link in [("../escape.json", False), ("/escape.json", False), ("link.json", True)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                with self.archive(Path(tmp), name, symlink=link):
                    with self.assertRaisesRegex(ValueError, "Unsafe"):
                        bundle_data.ensure()

    def test_rejects_modified_bundle_and_unapproved_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.archive(Path(tmp), "events_manifest.json"):
                with self.assertRaises(ValueError):
                    bundle_data.ensure()
                with bundle_data.BUNDLE.open("ab") as out:
                    out.write(b"changed")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    bundle_data.ensure()

    def test_does_not_overwrite_newer_forecast_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.archive(Path(tmp), "forecast_log_PL.json"):
                target = bundle_data.WORKBENCH / "forecast_log_PL.json"
                target.parent.mkdir()
                target.write_text('{"newer": true}')
                with patch.object(bundle_data, "validate_public") as validate:
                    bundle_data.ensure()
                    validate.assert_called_once_with({})
                self.assertEqual(json.loads(target.read_text()), {"newer": True})
