import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local"))
import updates
import launcher
from corpus import Corpus
from evidence_search import VERSION


class UpdateTests(unittest.TestCase):
    def package(self, root, tag="local-preview-v0.3.5", platform="windows-x64"):
        root.mkdir(parents=True, exist_ok=True)
        (root / "version.txt").write_text(tag)
        (root / "platform.txt").write_text(platform)
        (root / "launcher.py").write_text("# fixture, never executed")
        binary = updates.executable(root, platform)
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_bytes(b"fixture")

    def release(self, tag="local-preview-v0.3.5"):
        name = "Document-Review-windows-x64.zip"
        return {"tag_name": tag, "draft": False, "assets": [
            {"name": n, "size": 500, "browser_download_url": updates.BASE + tag + "/" + n}
            for n in (name, name + ".sha256")]}

    def test_manual_check_filters_versions_and_incomplete_platforms(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.package(root, "local-preview-v0.3.4")
            incomplete = self.release("local-preview-v0.3.9")
            incomplete["assets"] = []
            with patch.object(updates, "fetch", return_value=json.dumps([
                    incomplete, self.release("local-preview-v0.3.3"), self.release()]).encode()) as fetch:
                self.assertEqual(updates.check(root, "windows-x64")["version"], "local-preview-v0.3.5")
                fetch.assert_called_once_with(updates.API, 2 * 1024**2)
            with patch.object(updates, "fetch", return_value=b"[]"):
                self.assertIsNone(updates.check(root, "windows-x64"))
            with patch.object(updates, "fetch", side_effect=OSError()):
                with self.assertRaisesRegex(updates.UpdateError, "when online"):
                    updates.check(root, "windows-x64")

    def test_external_asset_url_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.package(root, "local-preview-v0.3.4")
            release = self.release()
            release["assets"][0]["browser_download_url"] = "https://example.invalid/payload.zip"
            with patch.object(updates, "fetch", return_value=json.dumps([release]).encode()):
                with self.assertRaisesRegex(updates.UpdateError, "source"):
                    updates.check(root, "windows-x64")

    def test_verified_package_install_preserves_model_and_activates_shortcut_pointer(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            old = data / "app" / "v0.3.4"
            self.package(old, "local-preview-v0.3.4")
            model = data / "models" / "keep.bin"
            model.parent.mkdir()
            model.write_bytes(b"existing model")
            fixture = io.BytesIO()
            with zipfile.ZipFile(fixture, "w") as archive:
                for name, value in {"version.txt": "local-preview-v0.3.5", "platform.txt": "windows-x64",
                                    "launcher.py": "# fixture", "python/pythonw.exe": "fixture"}.items():
                    archive.writestr("Document Review Local/" + name, value)
            content = fixture.getvalue()
            name = "Document-Review-windows-x64.zip"
            info = {"version": "local-preview-v0.3.5", "name": name, "size": len(content),
                    "url": updates.BASE + "local-preview-v0.3.5/" + name}
            info["checksum_url"] = info["url"] + ".sha256"
            checksum = hashlib.sha256(content).hexdigest() + "  " + name
            with patch.object(updates, "fetch", return_value=checksum.encode()), \
                 patch.object(updates, "urlopen", return_value=io.BytesIO(content)):
                destination = updates.prepare(info, data, "windows-x64", launcher.extract, lambda text: None, threading.Event())
            self.assertEqual(model.read_bytes(), b"existing model")
            self.assertTrue(old.is_dir())
            self.assertFalse((data / "active-version.json").exists())
            with patch.object(updates, "launch") as launch:
                updates.activate(data, old, destination, "windows-x64")
                launch.assert_called_once_with(destination, "windows-x64")
            self.assertEqual(updates.active_root(data, old, "windows-x64"), destination)
            self.assertIsNone(updates.active_root(data, destination, "windows-x64"))
            # A failed restart restores the previous selection.
            pointer = data / "active-version.json"
            pointer.unlink()
            with patch.object(updates, "launch", side_effect=OSError()):
                with self.assertRaises(updates.UpdateError):
                    updates.activate(data, old, destination, "windows-x64")
            self.assertFalse(pointer.exists())
            self.assertEqual(model.read_bytes(), b"existing model")
            # A checksum failure never creates an active installation.
            bad = dict(info, version="local-preview-v0.3.6")
            bad["url"] = updates.BASE + bad["version"] + "/" + name
            bad["checksum_url"] = bad["url"] + ".sha256"
            with patch.object(updates, "fetch", return_value=("0" * 64 + "  " + name).encode()), \
                 patch.object(updates, "urlopen", return_value=io.BytesIO(content)):
                with self.assertRaisesRegex(updates.UpdateError, "verification"):
                    updates.prepare(bad, data, "windows-x64", launcher.extract, lambda text: None, threading.Event())
            self.assertFalse(updates.target(data, bad["version"]).exists())

    def test_local_can_index_over_20mb_and_over_300_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "large.pdf"
            with path.open("wb") as output:
                output.truncate(21 * 1024**2)
            with self.assertRaisesRegex(ValueError, "20 MB"):
                Corpus.from_paths([path])
            fake = {"schema_version": VERSION, "source_name": "large.pdf", "source_sha256": "a" * 64, "page_count": 301,
                    "passages": [{"id": "p0001-c001", "pdf_page": 1, "page_label": "1", "text": "test"}]}
            with patch("corpus.index_pdf", return_value=fake):
                with self.assertRaisesRegex(ValueError, "300 pages"):
                    Corpus.from_paths([path], max_file_bytes=None)
                corpus = Corpus.from_paths([path], max_file_bytes=None, max_pages=None, max_passages=None)
            self.assertEqual(corpus.manifest()[0]["pages"], 301)


if __name__ == "__main__":
    unittest.main()
