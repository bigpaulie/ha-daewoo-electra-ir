"""Publication guards must catch invalid metadata and common leaks without echoing them."""

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication", ROOT / "tools/check_publication.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class PublicationTests(unittest.TestCase):
    def test_source_is_sanitized(self):
        self.assertEqual(publication.check_source(), [])

    def test_leak_patterns_and_safe_protocol_bytes(self):
        # Construct synthetic samples rather than retaining real addresses/paths.
        samples = [
            "/" + "Users" + "/test-person/project/source.py",
            "https://" + "chatgpt.com" + "/share/synthetic-reference",
            ".".join(["192", "168", "25", "25"]),
            ":".join(["ab", "cd", "ef", "12", "34", "56"]),
            "test-person" + "@" + "example.org",
            "ghp_" + "x" * 25,
        ]
        for sample in samples:
            with self.subTest(kind=sample.split(":", 1)[0][:8]):
                errors = publication.inspect_text("synthetic", sample)
                self.assertTrue(errors)
                self.assertNotIn(sample, " ".join(errors))
        self.assertFalse(
            publication.inspect_text("protocol", "C3 87 12 79 60 00 88 66 00 20 00 1E 61")
        )

    def test_unassigned_release_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            integration = root / "custom_components/daewoo_electra_ir"
            integration.mkdir(parents=True)
            (integration / "manifest.json").write_text(json.dumps({"codeowners": []}))
            self.assertGreaterEqual(len(publication.check_release(root)), 2)

    def test_archive_rejects_cache_and_private_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("__pycache__/example.pyc", b"cache")
                archive.writestr("notes.txt", "test-person" + "@" + "example.org")
            self.assertEqual(len(publication.check_archive(path)), 2)
