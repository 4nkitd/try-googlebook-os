#!/usr/bin/env python3
"""Start or stop the Googlebook VM, optionally with USB devices passed through.

  usb_launch.py                 list the USB devices macOS can see
  usb_launch.py VVVV:PPPP ...   start the VM as the administrator with those devices attached,
                                then open the viewer window on it
  usb_launch.py --stop          ask the newest VM to shut down
  usb_launch.py --status        show whether a VM is running
  usb_launch.py --print ...     print the commands instead of running them

The VM runs with administrator rights because macOS only lets a process take a device its
drivers have claimed (webcams, drives, audio gear) when that process is root or carries a
restricted Apple entitlement this project does not have. Devices macOS has not claimed work
without it, but those are rare. While a device is attached the Mac cannot use it, and hubs
cannot be passed. Unmount a drive on the Mac first.

Quitting the viewer does not stop a VM started this way; use --stop.
"""

import argparse, json, os, shlex, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = ROOT / "work"
sys.path.insert(0, str(HERE))
import vm_control  # noqa: E402

VIEWER = WORK / "host/Googlebook VM.app/Contents/MacOS/GooglebookViewer"
RUNNER = HERE / "run_vm.py"


def list_devices():
    out = subprocess.run(
        ["/usr/sbin/system_profiler", "SPUSBDataType", "-json"],
        capture_output=True,
        text=True,
    ).stdout
    found = []

    def walk(items):
        for it in items or []:
            vid, pid = it.get("vendor_id"), it.get("product_id")
            if vid and pid:
                vid = vid.split()[0].replace("0x", "")
                pid = pid.split()[0].replace("0x", "")
                found.append((it.get("_name", "USB device"), vid, pid))
            walk(it.get("_items"))

    try:
        walk(json.loads(out).get("SPUSBDataType"))
    except ValueError:
        pass
    return found


def newest_run_dir():
    logs = WORK / "logs"
    dirs = (
        [d for d in logs.glob("*") if (d / "serial.sock").exists()]
        if logs.exists()
        else []
    )
    return max(dirs, key=lambda d: d.stat().st_mtime) if dirs else None


def vm_alive():
    return (
        subprocess.run(["pgrep", "-f", "qemu-interop"], capture_output=True).returncode
        == 0
    )


def default_setting(key, fallback):
    r = subprocess.run(
        ["/usr/bin/defaults", "read", "local.googlebook.viewer", key],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else fallback


def native_display():
    try:
        raw = subprocess.run(
            ["/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True,
            text=True,
        ).stdout
        for d in json.loads(raw).get("SPDisplaysDataType", []):
            if str(d.get("spdisplays_main", "")).endswith("yes"):
                w, h = [int(x) for x in d["_spdisplays_pixels"].split(" x ")]
                return f"{w}x{min(h, round(w / 1.6))}"
    except Exception:
        pass
    return "3024x1890"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("devices", nargs="*", metavar="VVVV:PPPP")
    ap.add_argument(
        "--display",
        help="guest resolution (defaults to the viewer setting, then this display)",
    )
    ap.add_argument("--memory", type=int, help="guest memory in MiB")
    ap.add_argument("--cpus", type=int, help="guest processor cores")
    ap.add_argument(
        "--print",
        dest="dry_run",
        action="store_true",
        help="print the commands instead of running them",
    )
    ap.add_argument("--stop", action="store_true", help="power off the newest VM")
    ap.add_argument(
        "--status", action="store_true", help="show whether a VM is running"
    )
    args = ap.parse_args()

    if args.status:
        d = newest_run_dir()
        print("vm running:", "yes" if vm_alive() else "no")
        print("newest run folder:", d if d else "none")
        return

    if args.stop:
        d = newest_run_dir()
        if not vm_alive() or not d:
            print("no VM to stop")
            return
        vm_control.send(d, "VM_POWEROFF")
        print("asked Android to power off, waiting for the VM to exit")
        for _ in range(40):
            if not vm_alive():
                print("VM stopped")
                return
            time.sleep(1)
        print(
            "the VM did not stop; quit it from the viewer window if that instance owns it, or check the run log"
        )
        return

    found = list_devices()
    if not args.devices:
        if not found:
            print("no USB devices attached")
        for label, vid, pid in found:
            print(f"{vid}:{pid}  {label}")
        print(
            "\nusage: usb_launch.py VVVV:PPPP [more ...]   (no 0x prefix, repeat for several devices)"
        )
        return

    for spec in args.devices:
        parts = spec.split(":")
        if len(parts) != 2 or not all(
            p and all(c in "0123456789abcdefABCDEF" for c in p) for p in parts
        ):
            sys.exit(
                f"bad device spec {spec!r}; expected hex VENDOR:PRODUCT like 05ac:8514 "
                "(run without arguments to list)"
            )

    display = args.display or default_setting("Resolution", "native")
    if "x" not in display:
        display = native_display()
    memory = args.memory or int(default_setting("MemoryMiB", "4096"))
    cpus = args.cpus or int(default_setting("CPUs", "6"))
    name = time.strftime("usb-%Y%m%d-%H%M%S")
    logs = WORK / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / f"{name}.launch.log"
    script = logs / f"{name}.launch.sh"
    usb_args = " ".join(f"--usb {shlex.quote(d)}" for d in args.devices)
    script_text = (
        "#!/bin/sh\n"
        f"cd {shlex.quote(str(ROOT))} && umask 0 && "
        f"nohup /usr/bin/python3 {shlex.quote(str(RUNNER))} "
        f"{shlex.quote(str(WORK))} {shlex.quote(name)} "
        f"--display {shlex.quote(display)} --memory {memory} --cpus {cpus} "
        f"{usb_args} >> {shlex.quote(str(log))} 2>&1 &\n"
    )
    inner = f"/bin/sh {shlex.quote(str(script))}"
    applescript = (
        'do shell script "'
        + inner.replace("\\", "\\\\").replace('"', '\\"')
        + '" with administrator privileges'
    )
    if args.dry_run:
        print(script_text)
        print(["osascript", "-e", applescript])
        return

    if vm_alive():
        sys.exit("a VM is already running; stop it first with: usb_launch.py --stop")

    script.write_text(script_text)
    script.chmod(0o755)
    if subprocess.run(["osascript", "-e", applescript]).returncode != 0:
        sys.exit("administrator approval was declined; nothing was started")

    print("VM starting with administrator rights, waiting for the display")
    sock = logs / name / "spice.sock"
    for _ in range(150):
        if sock.exists():
            break
        time.sleep(1)
    else:
        sys.exit(f"the display never came up; see {log}")

    token = ""
    token_file = logs / name / "token"
    for _ in range(30):
        try:
            token = token_file.read_text().strip()
        except OSError:
            token = ""
        if token:
            break
        time.sleep(1)
    if not token:
        sys.exit(f"could not read the control token; see {log}")

    env = dict(os.environ, VM_INPUT_TOKEN=token)
    subprocess.Popen([str(VIEWER), str(sock)], env=env)
    print(f"viewer opened for {name}")
    print(f"stop it later with: {Path(__file__).name} --stop")


if __name__ == "__main__":
    main()
