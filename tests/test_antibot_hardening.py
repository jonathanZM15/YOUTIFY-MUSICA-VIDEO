"""Runtime and updater regressions: no network or environment mutations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.runtime import javascript_options
from core.updater import Updater
from core.storage import JsonStore


class TestRuntimeAndUpdates(unittest.TestCase):
    def test_node_is_configured_with_explicit_path(self):
        with patch("core.runtime.shutil.which", side_effect=lambda name: "C:/node.exe" if name == "node" else None):
            self.assertIn("node", javascript_options()["js_runtimes"])

    def test_no_runtime_does_not_enable_remote_code_downloads(self):
        with tempfile.TemporaryDirectory() as tmp, patch("core.runtime.BASE_DIR", Path(tmp)), patch("core.runtime.shutil.which", return_value=None):
            self.assertEqual(javascript_options(), {"js_runtimes": {}})

    def test_bundled_node_takes_precedence(self):
        with tempfile.TemporaryDirectory() as tmp, patch("core.runtime.BASE_DIR", Path(tmp)):
            runtime = Path(tmp) / "runtime"
            runtime.mkdir()
            (runtime / "node.exe").touch()
            with patch("core.runtime.shutil.which", return_value="other/node.exe"):
                self.assertEqual(javascript_options()["js_runtimes"]["node"]["path"], str(runtime / "node.exe"))

    def test_semantic_version_prerelease_is_older(self):
        self.assertFalse(Updater.is_newer_version("v1.2.0rc1", "1.2.0"))
        self.assertTrue(Updater.is_newer_version("v1.2.1", "1.2.0"))

    def test_invalid_version_is_ignored(self):
        self.assertFalse(Updater.is_newer_version("surprise", "1.2.0"))

    def test_update_urls_must_belong_to_this_repository(self):
        self.assertTrue(Updater._valid_release_url("https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/tag/v1.2.0"))
        for url in ["https://evil.example/setup.exe", "https://github.com.evil.example/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases", "file:///setup.exe"]:
            self.assertFalse(Updater._valid_release_url(url))

    def test_json_store_preserves_previous_data_if_replace_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(Path(tmp) / "state.json")
            store.write({"old": True})
            with patch("core.storage.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError): store.write({"new": True})
            self.assertEqual(store.read(), {"old": True})
            self.assertFalse(list(Path(tmp).glob("*.tmp")))
