import hashlib
import io
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "VERSION",
    "LICENSE",
    "distribution/launcher.m",
    "distribution/Setup.command",
    "distribution/setup.py",
    "assets/AppIcon.icns",
    "install.sh",
    "prereqs.sh",
    "lib.sh",
    "fetch.sh",
    "build-host.sh",
    "build-guest.sh",
    "build-image.sh",
    "host/viewer.m",
    "host/build_viewer.py",
    "run/run_vm.py",
    "run/vm_control.py",
    "run/bt_bridge.py",
    "tools/unpack_cuttlefish.py",
    "guest/input/vm/Input.java",
}


def archived_version(archive):
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        missing = REQUIRED - {
            member.name for member in source.getmembers() if member.isfile()
        }
        if missing:
            raise SystemExit(
                "Committed source archive is incomplete: " + ", ".join(sorted(missing))
            )
        version = source.extractfile("VERSION").read().decode().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?", version):
        raise SystemExit("Invalid committed VERSION")
    return version


def package():
    subprocess.run(
        ["git", "diff", "--exit-code", "HEAD"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", revision], cwd=ROOT
    )
    version = archived_version(archive)
    output = ROOT / "dist" / version
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="googlebook-package-", dir=output
    ) as temporary:
        stage = Path(temporary)
        app = stage / "Try Googlebook OS.app"
        contents = app / "Contents"
        resources = contents / "Resources"
        binary = contents / "MacOS/TryGooglebookOS"
        binary.parent.mkdir(parents=True)
        resources.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(resources / "source", filter="data")
        committed = resources / "source"
        shutil.copyfile(committed / "assets/AppIcon.icns", resources / "AppIcon.icns")
        shutil.copyfile(
            committed / "distribution/Setup.command", resources / "Setup.command"
        )
        (resources / "Setup.command").chmod(0o755)
        (contents / "Info.plist").write_bytes(
            plistlib.dumps(
                {
                    "CFBundleIdentifier": "in.dagar.try-googlebook-os",
                    "CFBundleName": "Try Googlebook OS",
                    "CFBundleExecutable": "TryGooglebookOS",
                    "CFBundlePackageType": "APPL",
                    "CFBundleShortVersionString": "0.1.0",
                    "CFBundleVersion": "1",
                    "CFBundleIconFile": "AppIcon",
                    "LSMinimumSystemVersion": "26.0",
                    "NSHighResolutionCapable": True,
                    "TryGooglebookVersion": version,
                    "TryGooglebookRevision": revision,
                }
            )
        )
        subprocess.run(
            [
                "clang",
                "-fobjc-arc",
                "-fblocks",
                "-O2",
                "-arch",
                "arm64",
                "-mmacosx-version-min=26.0",
                str(committed / "distribution/launcher.m"),
                "-framework",
                "AppKit",
                "-o",
                str(binary),
            ],
            check=True,
        )
        subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
        subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(app)], check=True
        )
        (stage / "Applications").symlink_to("/Applications")
        (stage / "READ ME.txt").write_text(
            f"Try Googlebook OS {version}\n\n"
            "Drag the app into Applications, then open it. First launch prepares the VM locally.\n"
            "About 9 GB of downloads and 60 GB free disk are needed for setup.\n"
            "This is an ad-hoc signed experimental launcher, not a notarized release.\n"
            "macOS may require explicit approval in System Settings > Privacy & Security.\n"
            "No Google recovery image, user data or UTM binaries are included.\n"
            "USB, real Bluetooth and camera support are not enabled in this alpha.\n"
            "https://github.com/4nkitd/try-googlebook-os\n"
        )
        dmg = output / f"TryGooglebookOS-{version}-arm64.dmg"
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-ov",
                "-format",
                "UDZO",
                "-fs",
                "HFS+",
                "-volname",
                "Try Googlebook OS",
                "-srcfolder",
                str(stage),
                str(dmg),
            ],
            check=True,
        )
    source_archive = output / f"try-googlebook-os-{version}-source.tar.gz"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            f"--prefix=try-googlebook-os-{version}/",
            "-o",
            str(source_archive),
            revision,
        ],
        cwd=ROOT,
        check=True,
    )
    checksums = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in (dmg, source_archive)
    )
    (output / "SHA256SUMS").write_text(checksums)
    print(checksums)


if __name__ == "__main__":
    package()
