import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local_launcher", ROOT / "local" / "launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LocalTests(unittest.TestCase):
    def test_setup_reuses_existing_model_and_finishes_without_app_server(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            (data / "setup-complete.json").write_text('{}')
            with patch.object(launcher, "DATA", data), patch.object(launcher, "PLATFORM", "windows-x64"), \
                 patch.object(launcher, "engine_path", return_value=data / "ollama.exe"), \
                 patch.object(launcher, "start_engine"), patch.object(launcher, "download") as download, \
                 patch.object(launcher, "pull_model") as pull, \
                 patch.object(launcher, "read_json", return_value={"models": [{"name": launcher.MODEL}]}):
                launcher.setup()
                self.assertEqual(launcher.STATE["status"], "ready")
                download.assert_not_called()
                pull.assert_not_called()
                self.assertFalse(hasattr(launcher, "start_app"))
                self.assertFalse(hasattr(launcher, "Handler"))

    def test_private_environment_does_not_inherit_cloud_credentials_or_proxies(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake", "OLLAMA_HOST": "remote", "HTTPS_PROXY": "remote", "DOCUMENT_REVIEW_HOSTED": "1"}):
            env = launcher.private_environment(Path("private-data"))
        self.assertNotIn("GEMINI_API_KEY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("DOCUMENT_REVIEW_HOSTED", env)
        self.assertEqual(env["OLLAMA_HOST"], "127.0.0.1:11435")
        self.assertEqual(env["OLLAMA_NO_CLOUD"], "1")
        self.assertEqual(env["DOCUMENT_REVIEW_LOCAL_ONLY"], "1")

    def test_checksum_failure_rejects_download(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "engine.zip"
            asset = {"browser_download_url": "https://example.invalid/engine", "digest": "sha256:wrong", "size": 3}
            with patch.object(launcher, "urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaisesRegex(ValueError, "integrity"):
                    launcher.download(asset, target)
            self.assertFalse(target.exists())

    def test_zip_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "engine.zip"
            with zipfile.ZipFile(archive, "w") as source:
                source.writestr("../escape.txt", "bad")
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                launcher.extract(archive, Path(folder) / "engine")
            self.assertFalse((Path(folder) / "escape.txt").exists())

    def test_download_manifest_is_pinned_to_official_sources(self):
        manifest = json.loads((ROOT / "local" / "downloads.json").read_text())
        self.assertEqual(set(manifest), {"windows-x64", "mac-arm64", "mac-x64", "linux-x64"})
        for platform in manifest.values():
            for source, repo in (("python", "astral-sh/python-build-standalone"), ("ollama", "ollama/ollama")):
                self.assertTrue(platform[source]["browser_download_url"].startswith(f"https://github.com/{repo}/releases/download/"))
                self.assertRegex(platform[source]["digest"], r"^sha256:[0-9a-f]{64}$")

    def test_local_only_app_has_no_cloud_selector_or_secret_access(self):
        from streamlit.testing.v1 import AppTest
        from demo import Walkthrough
        with patch.dict("os.environ", {"DOCUMENT_REVIEW_LOCAL_ONLY": "1"}), patch("providers.Gemini") as gemini, patch("providers.Ollama", return_value=Walkthrough()) as ollama:
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(app.selectbox)
            self.assertFalse(app.text_input)
            self.assertFalse(app.checkbox)
            app.radio(key="source_choice").set_value("Try the example reports").run()
            app.button(key="review_start").click().run(timeout=30)
            self.assertFalse(app.exception)
            ollama.assert_called_once_with("qwen2.5:7b", port=11435)
            gemini.assert_not_called()
            self.assertEqual(app.session_state["review_result"]["stop_reason"], "finished")
