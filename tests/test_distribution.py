import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "distribution_setup", ROOT / "distribution/setup.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
package_spec = importlib.util.spec_from_file_location(
    "distribution_package", ROOT / "distribution/package.py"
)
package = importlib.util.module_from_spec(package_spec)
package_spec.loader.exec_module(package)


class DistributionTests(unittest.TestCase):
    def archive(self, omitted=None):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w") as archive:
            for name in package.REQUIRED - set(omitted or []):
                content = b"0.1.0-alpha.1\n" if name == "VERSION" else b"test source"
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        return output.getvalue()

    def test_archive_requires_setup_dependency(self):
        with self.assertRaisesRegex(SystemExit, "distribution/setup.py"):
            package.archived_version(self.archive(["distribution/setup.py"]))

    def test_archive_requires_bundled_bridge_dependency(self):
        with self.assertRaisesRegex(SystemExit, "run/bt_bridge.py"):
            package.archived_version(self.archive(["run/bt_bridge.py"]))

    def test_unrelated_untracked_pruner_not_required(self):
        self.assertNotIn("run/prune.py", package.REQUIRED)
        self.assertEqual(package.archived_version(self.archive()), "0.1.0-alpha.1")

    def test_existing_disk_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "work"
            disk = work / "image/googlebook.raw"
            disk.parent.mkdir(parents=True)
            disk.write_bytes(b"existing-data")
            with patch.object(setup.subprocess, "run") as execute:
                with self.assertRaisesRegex(SystemExit, "Existing VM preserved"):
                    setup.setup(ROOT, work)
                execute.assert_not_called()
            self.assertEqual(disk.read_bytes(), b"existing-data")

    def test_setup_never_runs_as_root(self):
        with patch.object(os, "geteuid", return_value=0):
            with self.assertRaisesRegex(SystemExit, "not with sudo"):
                setup.setup(ROOT, "/not-created")

    def test_setup_invokes_bundled_source_with_separate_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "work"
            with patch.object(setup.subprocess, "run") as execute:
                setup.setup(ROOT, work)
            call = execute.call_args_list[0]
            self.assertEqual(call.args[0][-1], str(ROOT / "install.sh"))
            self.assertEqual(call.kwargs["env"]["GOOGLEBOOK_WORK"], str(work.resolve()))
            self.assertEqual(execute.call_args_list[1].args[0][0], "/usr/bin/open")

    def test_setup_and_launch_preserve_selected_work_despite_terminal_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "selected work"
            with patch.dict(os.environ, {"GOOGLEBOOK_WORK": "/wrong-terminal-vm"}):
                with patch.object(setup.subprocess, "run") as execute:
                    setup.setup(ROOT, work)
            self.assertEqual(len(execute.call_args_list), 2)
            for call in execute.call_args_list:
                self.assertEqual(
                    call.kwargs["env"]["GOOGLEBOOK_WORK"], str(work.resolve())
                )

    def test_physical_capture_disabled_without_side_effects(self):
        for args in (
            ["run/run_vm.py", "/missing", "test", "--usb", "1234:5678"],
            ["run/usb_launch.py", "--bt", "0a12:0001"],
        ):
            result = subprocess.run(
                [sys.executable, *args], cwd=ROOT, capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("alpha", result.stderr)


if __name__ == "__main__":
    unittest.main()
