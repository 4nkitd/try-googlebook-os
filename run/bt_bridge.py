#!/usr/bin/env python3
"""Bridge a real USB Bluetooth dongle into the Googlebook VM.

The guest's Bluetooth service (Cuttlefish's) speaks H4-framed HCI over /dev/hvc0, a virtio
console that run_vm.py wires to a TCP port. Normally netsimd (a virtual radio) sits behind
that port; with --bluetooth-device VVVV:PPPP this script sits there instead and carries the
same H4 stream to a real dongle over USB, so the guest pairs with real devices (headphones,
keyboards, phones).

    usb_launch.py --bt VVVV:PPPP      the supported way in (one administrator prompt)
    bt_bridge.py --list               show attached dongles that look like HCI controllers

Requirements: administrator rights (macOS only lets root take a claimed USB device; see
docs/usb-passthrough.md), and a dongle that needs no firmware download. CSR8510-class parts
work; Realtek/Intel/Broadcom parts that load patch files do not, yet.

While bridged the Mac loses the dongle (same as any USB passthrough). Wire format on the TCP
side is H4 (0x01 command, 0x02 ACL, 0x03 SCO, 0x04 event, 0x05 ISO); on USB it is HCI over
USB: commands by control transfer, events by interrupt IN, ACL by bulk in/out. SCO and
isochronous traffic are not carried.
"""

import argparse, os, socket, struct, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = (
    Path(os.environ.get("GOOGLEBOOK_WORK", HERE.parent / "work")).expanduser().resolve()
)

H4_CMD, H4_ACL, H4_SCO, H4_EVT, H4_ISO = 0x01, 0x02, 0x03, 0x04, 0x05


def ensure_pyusb():
    try:
        import usb.core  # noqa: F401
        import usb.util  # noqa: F401

        return
    except ImportError:
        venv_py = WORK / "bt-env" / "bin" / "python"
        # A venv interpreter can symlink to the same executable as its base interpreter.
        if (
            venv_py.exists()
            and Path(sys.prefix).resolve() != venv_py.parent.parent.resolve()
        ):
            os.execv(
                str(venv_py),
                [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]],
            )
        sys.exit(
            "pyusb is missing. Create the bridge environment once:\n"
            f"  uv venv {WORK / 'bt-env'}\n"
            f"  uv pip install --python {WORK / 'bt-env/bin/python'} pyusb"
        )


def backend():
    import usb.backend.libusb1 as libusb1

    candidates = [
        os.environ.get("GBOS_LIBUSB"),
        str(
            WORK
            / "UTM-beta/UTM.app/Contents/Frameworks/usb-1.0.0.framework/Versions/A/usb-1.0.0"
        ),
    ]
    for path in candidates:
        if path and Path(path).exists():
            return libusb1.get_backend(find_library=lambda _name, p=path: p)
    return libusb1.get_backend()


def frame_size(buf):
    """Bytes of the first complete H4 frame in buf, None while it is still short."""
    if not buf:
        return None
    kind = buf[0]
    if kind == H4_CMD:
        return None if len(buf) < 4 else 4 + buf[3]
    if kind == H4_ACL:
        return None if len(buf) < 5 else 5 + struct.unpack_from("<H", buf, 3)[0]
    if kind == H4_SCO:
        return None if len(buf) < 4 else 4 + buf[3]
    if kind == H4_EVT:
        return None if len(buf) < 3 else 3 + buf[2]
    if kind == H4_ISO:
        return None if len(buf) < 5 else 5 + struct.unpack_from("<H", buf, 3)[0]
    return 1


def selftest():
    frames = [
        (H4_CMD, bytes([0x03, 0x0C, 0x00])),
        (H4_EVT, bytes([0x0E, 0x04, 0x01, 0x03, 0x0C, 0x00])),
        (H4_ACL, bytes([0x01, 0x00, 0x05, 0x00]) + b"hello"),
        (H4_SCO, bytes([0x01, 0x00, 0x02]) + b"xy"),
    ]
    stream = b"".join(bytes([k]) + p for k, p in frames)
    out, buf = [], b""
    for i in range(len(stream)):
        buf += stream[i : i + 1]
        while True:
            size = frame_size(buf)
            if size is None or len(buf) < size:
                break
            out.append((buf[0], buf[1:size]))
            buf = buf[size:]
    assert out == frames, (out, frames)
    assert buf == b"", buf
    print("selftest: PASS (H4 framing, byte-wise reassembly)")


def list_devices():
    import usb.core
    import usb.util

    be = backend()
    found = 0
    for dev in usb.core.find(find_all=True, backend=be):
        classes = [dev.bDeviceClass]
        try:
            for cfg in dev:
                for intf in cfg:
                    classes.append(intf.bInterfaceClass)
        except usb.core.USBError:
            pass
        if 0xE0 not in classes:
            continue
        name = ""
        try:
            name = usb.util.get_string(dev, dev.iProduct) or ""
        except Exception:
            pass
        print(f"{dev.idVendor:04x}:{dev.idProduct:04x}  {name}".rstrip())
        found += 1
    if not found:
        print("no Bluetooth dongles found (device class 0xE0)")


class Bridge:
    def __init__(self, dev, evt, acl_in, acl_out, conn):
        import usb.core

        self.usb_error = usb.core.USBError
        self.dev, self.evt, self.acl_in, self.acl_out, self.conn = (
            dev,
            evt,
            acl_in,
            acl_out,
            conn,
        )
        self.done = False
        self.lock = threading.Lock()

    def stop(self):
        self.done = True
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def to_guest(self, kind, payload):
        with self.lock:
            try:
                self.conn.sendall(bytes([kind]) + payload)
            except OSError:
                self.stop()

    def evt_loop(self):
        while not self.done:
            try:
                data = self.evt.read(256, timeout=500)
            except self.usb_error as e:
                if "timeout" in str(e).lower():
                    continue
                print("bridge: event endpoint failed:", e, file=sys.stderr)
                break
            if data:
                self.to_guest(H4_EVT, bytes(data))

    def acl_loop(self):
        while not self.done:
            try:
                data = self.acl_in.read(4096, timeout=500)
            except self.usb_error as e:
                if "timeout" in str(e).lower():
                    continue
                print("bridge: ACL endpoint failed:", e, file=sys.stderr)
                break
            if data:
                self.to_guest(H4_ACL, bytes(data))

    def guest_loop(self):
        buf = b""
        while not self.done:
            try:
                chunk = self.conn.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while True:
                size = frame_size(buf)
                if size is None or len(buf) < size:
                    break
                kind, payload = buf[0], buf[1:size]
                buf = buf[size:]
                if kind == H4_CMD:
                    try:
                        self.dev.ctrl_transfer(0x20, 0x00, 0, 0, payload, timeout=2000)
                    except self.usb_error as e:
                        print("bridge: command failed:", e, file=sys.stderr)
                elif kind == H4_ACL and self.acl_out is not None:
                    try:
                        self.acl_out.write(payload, timeout=2000)
                    except self.usb_error as e:
                        print("bridge: ACL write failed:", e, file=sys.stderr)
                # SCO, ISO and unknown types are not carried.
        self.stop()


def serve(spec, port):
    import usb.core
    import usb.util

    vid, pid = (int(p, 16) for p in spec.split(":"))
    dev = usb.core.find(idVendor=vid, idProduct=pid, backend=backend())
    if dev is None:
        sys.exit(
            f"device {vid:04x}:{pid:04x} not found; is the dongle plugged in? "
            "(bt_bridge.py --list shows candidates)"
        )
    name = ""
    try:
        name = usb.util.get_string(dev, dev.iProduct) or ""
    except Exception:
        pass
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    evt = acl_in = acl_out = None
    for intf in cfg:
        try:
            dev.detach_kernel_driver(intf.bInterfaceNumber)
        except (usb.core.USBError, NotImplementedError):
            pass
        try:
            usb.util.claim_interface(dev, intf.bInterfaceNumber)
        except usb.core.USBError:
            pass
        for ep in intf:
            direction = usb.util.endpoint_direction(ep.bEndpointAddress)
            etype = usb.util.endpoint_type(ep.bmAttributes)
            if (
                etype == usb.util.ENDPOINT_TYPE_INTR
                and direction == usb.util.ENDPOINT_IN
                and evt is None
            ):
                evt = ep
            elif (
                etype == usb.util.ENDPOINT_TYPE_BULK
                and direction == usb.util.ENDPOINT_OUT
                and acl_out is None
            ):
                acl_out = ep
            elif (
                etype == usb.util.ENDPOINT_TYPE_BULK
                and direction == usb.util.ENDPOINT_IN
                and acl_in is None
            ):
                acl_in = ep
    if evt is None:
        sys.exit(
            "no interrupt-IN endpoint found; this dongle does not look like an HCI controller"
        )

    # Best-effort chip bring-up (fine for CSR8510-class parts that need no firmware).
    for request_type, value, data in (
        (0xC0, 0, None),  # read version
        (0x20, 0, bytes([0x03, 0x0C, 0x00])),  # HCI_Reset
    ):
        try:
            if data is None:
                dev.ctrl_transfer(request_type, 0, value, 0, 4, timeout=1000)
            else:
                dev.ctrl_transfer(request_type, 0, value, 0, data, timeout=1000)
        except usb.core.USBError:
            pass

    lsock = socket.socket()
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind(("127.0.0.1", port))
    lsock.listen(1)
    lsock.settimeout(180)
    print(
        f"bluetooth bridge: {vid:04x}:{pid:04x} ({name}) listening on 127.0.0.1:{port}",
        flush=True,
    )
    try:
        conn, _ = lsock.accept()
    except socket.timeout:
        sys.exit("no guest connected within 180 s; is the VM starting?")
    finally:
        lsock.close()
    print("bluetooth bridge: guest connected", flush=True)

    bridge = Bridge(dev, evt, acl_in, acl_out, conn)
    threads = [threading.Thread(target=bridge.evt_loop, daemon=True)]
    if acl_in is not None:
        threads.append(threading.Thread(target=bridge.acl_loop, daemon=True))
    for t in threads:
        t.start()
    try:
        bridge.guest_loop()
    finally:
        bridge.stop()
        for t in threads:
            t.join(timeout=1)
        try:
            usb.util.dispose_resources(dev)
        except Exception:
            pass
    print("bluetooth bridge: closed", flush=True)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("spec", nargs="?", metavar="VVVV:PPPP")
    ap.add_argument("--list", action="store_true", help="show attached dongles")
    ap.add_argument("--selftest", action="store_true", help="check the H4 framing code")
    ap.add_argument(
        "--port", type=int, default=0, help="loopback port for QEMU's chardev"
    )
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    ensure_pyusb()
    if args.list:
        list_devices()
        return
    if not args.spec or not args.port:
        sys.exit("usage: bt_bridge.py VVVV:PPPP --port N   (or --list / --selftest)")
    parts = args.spec.split(":")
    if len(parts) != 2 or not all(
        p and len(p) <= 4 and all(c in "0123456789abcdefABCDEF" for c in p)
        for p in parts
    ):
        sys.exit(f"bad device spec {args.spec!r}; expected hex VENDOR:PRODUCT")
    serve(args.spec, args.port)


if __name__ == "__main__":
    main()
