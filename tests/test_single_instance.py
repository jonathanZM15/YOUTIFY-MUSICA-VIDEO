"""Exercise actual Windows kernel objects and competing processes, without Tk."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.single_instance import SingleInstance

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(sys.platform == "win32", "Windows single-instance integration")
class TestSingleInstance(unittest.TestCase):
    def name(self):
        return "Local\\Youtify.Test." + uuid4().hex

    def test_only_first_owner_can_start(self):
        name = self.name()
        with SingleInstance(name) as first, SingleInstance(name) as second:
            self.assertTrue(first.is_primary)
            self.assertFalse(second.is_primary)

    def test_duplicate_notifies_even_before_window_is_created(self):
        name = self.name()
        with SingleInstance(name) as first:
            self.assertFalse(first.activation_requested())
            with SingleInstance(name) as second:
                self.assertFalse(second.is_primary)
            self.assertTrue(first.activation_requested())
            self.assertFalse(first.activation_requested())

    def test_can_reopen_after_normal_close(self):
        name = self.name()
        with SingleInstance(name):
            pass
        with SingleInstance(name) as reopened:
            self.assertTrue(reopened.is_primary)

    def test_data_directory_does_not_change_application_identity(self):
        with patch.dict(os.environ, {"YOUTIFY_DATA_DIR": "C:/first"}):
            first = SingleInstance()
        with patch.dict(os.environ, {"YOUTIFY_DATA_DIR": "C:/second"}):
            second = SingleInstance()
        self.assertEqual(first.name, second.name)
        self.assertEqual(first.window_property, second.window_property)

    def test_lock_failure_does_not_allow_a_window_to_start(self):
        guard = SingleInstance(self.name())
        with patch.object(guard.kernel, "CreateMutexW", return_value=None):
            with self.assertRaises(OSError):
                guard.acquire()
        self.assertIsNone(guard._event)
        self.assertFalse(guard.is_primary)

    def test_guard_import_does_not_load_gui_or_download_engine(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "import core.single_instance,sys; assert 'tkinter' not in sys.modules; assert 'yt_dlp' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_six_simultaneous_starts_have_exactly_one_owner(self):
        code = """
import json,sys
sys.path.insert(0,sys.argv[1])
from core.single_instance import SingleInstance
with SingleInstance(sys.argv[2]) as guard:
    print(json.dumps({'primary':guard.is_primary}),flush=True)
    if guard.is_primary: sys.stdin.readline()
"""
        processes = []
        with tempfile.TemporaryDirectory() as temporary:
            name = self.name()
            try:
                for i in range(6):
                    env = dict(os.environ, YOUTIFY_DATA_DIR=str(Path(temporary)/str(i)))
                    processes.append(subprocess.Popen([sys.executable, "-B", "-c", code, str(ROOT), name],
                        cwd=temporary, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
                results = [json.loads(p.stdout.readline()) for p in processes]
                self.assertEqual(sum(row["primary"] for row in results), 1)
                for p, result in zip(processes, results):
                    if result["primary"]:
                        p.stdin.write("close\n")
                        p.stdin.flush()
                    self.assertEqual(p.wait(10), 0)
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                    p.communicate(timeout=5)

    def test_process_crash_does_not_leave_a_stale_lock(self):
        name = self.name()
        code = "from core.single_instance import SingleInstance; import sys,time; g=SingleInstance(sys.argv[1]); print(g.acquire(),flush=True); time.sleep(30)"
        p = subprocess.Popen([sys.executable, "-B", "-c", code, name], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            self.assertEqual(p.stdout.readline().strip(), "True")
            p.kill()
            p.communicate(timeout=5)
            with SingleInstance(name) as reopened:
                self.assertTrue(reopened.is_primary)
        finally:
            if p.poll() is None:
                p.kill()
            p.communicate(timeout=5)
