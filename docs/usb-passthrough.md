# USB passthrough (and camera notes)

**Public alpha:** physical capture and root QEMU execution are blocked. List/status/stop
and `--print` remain available for diagnosis, but start commands exit before any admin
prompt or hardware capture. The text below describes research code, not supported features.

Experimental implementation, not verified with physical devices. CLI parsing, Bluetooth
framing, device-list startup and the normal VM stop path have been tested. USB capture,
Bluetooth pairing, webcam access and audio have not. Do not treat this as release-ready.

## Use

    cd try-googlebook-os
    uv run run/usb_launch.py                 # list devices (vvvv:pppp)
    uv run run/usb_launch.py 05ac:8514       # start the VM as admin with this device attached
    uv run run/usb_launch.py --bt 0a12:0001  # start with a real USB Bluetooth dongle bridged in
    uv run run/usb_launch.py --stop          # power the VM off again
    uv run run/usb_launch.py --status

An administrator prompt appears when the VM starts (macOS requirement, see below). The
viewer window opens attached to that VM. Quitting the viewer does NOT stop this VM; stop it
with `--stop`, or from a terminal:

    uv run run/vm_control.py RUN_DIR VM_POWEROFF

## How it works

`run_vm.py` gained `--usb VVVV:PPPP`. Each device becomes a QEMU `usb-host` device on the
VM's xHCI controller. A successful capture still needs the corresponding guest kernel
driver and Android service. USB enumeration alone does not prove application support.

## macOS permission gate (why admin?)

macOS lets a process take a USB device another process has claimed only when it is root or
carries the restricted `com.apple.vm.device-access` entitlement (Apple grants that to
shipping virtualization products; this project is ad-hoc signed and does not have it).
Devices with no macOS driver bound can attach without root, but that is rare in practice.
The prototype launcher requests administrator rights for QEMU. It currently widens the
SPICE and serial sockets and makes the token readable by other accounts. The QMP socket
is not deliberately widened, but the whole permission model still needs hardening.

Running the full VM as root is a significant risk. A safer isolated device-capture helper
and restrictive runtime permissions are release blockers, not completed safeguards.

The guest control link (pointer, clipboard, paste) is loopback-only and token-gated, but
the viewer hands the token to whoever reaches its local port first, and the token is
visible in QEMU's command line to local users. Treat it as trusted-local: any account on
the Mac can, in principle, inject input into the VM.

## Rules and limits (from the Try Omarchy port's findings)

- Do not select hubs, storage containing important data, or the Mac's only input device.
  The current VID/PID-only CLI does not yet enforce these exclusions.
- Unmount a drive on the Mac first (`diskutil unmountDisk`), or macOS and the guest fight.
- While attached, the Mac cannot use the device.
- Replugging mid-run can stall the VM window for seconds (libusb re-enumeration).
- The match pins vendor and product id; two identical devices are ambiguous.

## Bluetooth

The VM's built-in radio is virtual (netsimd): Bluetooth turns on inside Android, but there
is nothing real to pair with. Real Bluetooth comes from a USB dongle bridged into the same
HCI pipe the virtual radio uses:

    uv run run/usb_launch.py --bt VVVV:PPPP

The intended design claims a dedicated USB controller and transports HCI data into the
guest. It does not share the Mac's built-in Bluetooth radio. No dongle has been tested.

- No chipset compatibility is established. Firmware loading and vendor-specific setup
  are not implemented; marketing labels such as "Bluetooth 5.0" do not identify a chipset.
- `uv run run/bt_bridge.py --list` shows attached candidates; `--selftest` checks the framing.
- SCO and ISO traffic are not carried. A2DP uses ACL transport, but audio is untested.
- Using --bt replaces the virtual radio for that boot.

## Camera

- The built-in FaceTime camera cannot be passed through: it is not a USB device macOS can
  release, and Apple Silicon guests have no PCIe passthrough. It never appears to libusb.
- A USB webcam also needs guest UVC support, an Android external camera provider and the
  correct permissions/SELinux policy. Chrome visibility is not established for this image.
- Built-in camera sharing remains requested work. It needs a macOS capture bridge and a
  guest camera provider, with explicit permission and capture only while in use.
