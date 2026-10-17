# USB passthrough (and camera notes)

The VM can take a USB device from the Mac and give it to Googlebook OS while the VM runs.

## Use

    cd try-googlebook-os
    uv run run/usb_launch.py                 # list devices (vvvv:pppp)
    uv run run/usb_launch.py 05ac:8514       # start the VM as admin with this device attached
    uv run run/usb_launch.py --stop          # power the VM off again
    uv run run/usb_launch.py --status

An administrator prompt appears when the VM starts (macOS requirement, see below). The
viewer window opens attached to that VM. Quitting the viewer does NOT stop this VM; stop it
with `--stop`, or from a terminal:

    uv run run/vm_control.py RUN_DIR VM_POWEROFF

## How it works

`run_vm.py` gained `--usb VVVV:PPPP`. Each device becomes a QEMU `usb-host` device on the
VM's xHCI controller; the guest sees a normal USB device, and Android has native drivers
(mass storage, UVC cameras, audio class, HID).

## macOS permission gate (why admin?)

macOS lets a process take a USB device another process has claimed only when it is root or
carries the restricted `com.apple.vm.device-access` entitlement (Apple grants that to
shipping virtualization products; this project is ad-hoc signed and does not have it).
Devices with no macOS driver bound can attach without root, but that is rare in practice.
So the launcher starts the VM with administrator rights and leaves the run folder reachable
(umask 0, world-readable token) so the viewer and this folder's tools still work as the
logged-in user.

Trade-off: a privileged QEMU is a bigger security surface. Pass devices only while you need
them, on a lab machine.

The guest control link (pointer, clipboard, paste) is loopback-only and token-gated, but
the viewer hands the token to whoever reaches its local port first, and the token is
visible in QEMU's command line to local users. Treat it as trusted-local: any account on
the Mac can, in principle, inject input into the VM.

## Rules and limits (from the Try Omarchy port's findings)

- One or a few devices, never a hub (passing a hub takes everything behind it).
- Unmount a drive on the Mac first (`diskutil unmountDisk`), or macOS and the guest fight.
- While attached, the Mac cannot use the device.
- Replugging mid-run can stall the VM window for seconds (libusb re-enumeration).
- The match pins vendor and product id; two identical devices are ambiguous.

## Camera

- The built-in FaceTime camera cannot be passed through: it is not a USB device macOS can
  release, and Apple Silicon guests have no PCIe passthrough. It never appears to libusb.
- Practical route: plug a USB webcam and pass it through as above. Android supports USB
  webcams (UVC) natively, so Chrome and camera apps see it.
- Longer-term option (not scheduled): a virtual camera bridge that feeds the Mac camera into
  the guest as an emulated UVC device, or through Cuttlefish's camera HAL. That is R&D.
