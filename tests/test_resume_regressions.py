import builtins
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "run"))
import bt_bridge
import usb_launch


class ResumeRegressionTests(unittest.TestCase):
    def dry_run(self, args):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "not-created"
            output = io.StringIO()
            with (
                patch.object(usb_launch, "WORK", work),
                patch.object(usb_launch, "list_devices", return_value=[]),
                patch.object(
                    usb_launch,
                    "vm_alive",
                    side_effect=AssertionError("dry-run checked live VM"),
                ),
                patch.object(
                    usb_launch,
                    "default_setting",
                    side_effect=lambda key, fallback: fallback,
                ),
                patch.object(
                    usb_launch.subprocess,
                    "Popen",
                    side_effect=AssertionError("dry-run launched process"),
                ),
                patch.object(
                    sys,
                    "argv",
                    ["usb_launch.py", *args, "--display", "1920x1200", "--print"],
                ),
                contextlib.redirect_stdout(output),
            ):
                usb_launch.main()
            self.assertFalse(work.exists())
            return output.getvalue()

    def test_bluetooth_flag_forwarded(self):
        output = self.dry_run(["--bt", "0a12:0001"])
        self.assertIn("--bluetooth-device 0a12:0001", output)
        self.assertNotIn("--usb 0a12:0001", output)

    def test_bluetooth_and_separate_usb_forwarded(self):
        output = self.dry_run(["1234:5678", "--bt", "0a12:0001"])
        self.assertIn("--bluetooth-device 0a12:0001", output)
        self.assertIn("--usb 1234:5678", output)

    def test_reject_duplicate_controller(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as error,
        ):
            self.dry_run(["0A12:1", "--bt", "0a12:0001"])
        self.assertEqual(error.exception.code, 2)

    def test_venv_symlink_still_reexecutes(self):
        original_import = builtins.__import__

        def without_pyusb(name, *args, **kwargs):
            if name == "usb.core":
                raise ImportError("pyusb unavailable in base interpreter")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            interpreter = work / "bt-env/bin/python"
            interpreter.parent.mkdir(parents=True)
            interpreter.symlink_to(sys.executable)
            with (
                patch.object(bt_bridge, "WORK", work),
                patch.object(builtins, "__import__", side_effect=without_pyusb),
                patch.object(os, "execv", side_effect=SystemExit("reexec")) as execute,
            ):
                with self.assertRaises(SystemExit) as error:
                    bt_bridge.ensure_pyusb()
                self.assertEqual(str(error.exception), "reexec")
                self.assertEqual(execute.call_args.args[0], str(interpreter))

    def test_all_runner_scripts_parse(self):
        import ast

        for source in (ROOT / "run").glob("*.py"):
            with self.subTest(source=source.name):
                ast.parse(source.read_text())


if __name__ == "__main__":
    unittest.main()
