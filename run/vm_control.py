#!/usr/bin/env python3
"""Send one fixed verb to a running VM's guest control service over its serial socket.

Usage: vm_control.py RUN_DIR VERB [text]

The guest's PL011 serial input stalls if more than its 16-byte FIFO arrives at once, so
bytes are written in small chunks. macOS limits AF_UNIX paths to about 100 characters, so
when RUN_DIR is long the socket is opened under a temporary chdir with a short name.
"""

import base64, os, socket, sys, time
from pathlib import Path

VERBS = (
    "VM_POWEROFF",
    "VM_STATUS",
    "VM_POINTER",
    "VM_POINTER_ACCEL_OFF",
    "VM_AUDIO_DIAG",
    "VM_PLAY_TEST",
    "VM_POINTER_LOCATION 0",
    "VM_POINTER_LOCATION 1",
    "VM_PASTE",
    "VM_PASTE1",
)


def _send(sock_path, data):
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(sock_path)
        for i in range(0, len(data), 8):
            s.sendall(data[i : i + 8])
            time.sleep(0.03)


def send(run_dir, verb, text=None):
    line = (
        verb if text is None else verb + " " + base64.b64encode(text.encode()).decode()
    )
    data = (line + "\n").encode()
    run = Path(run_dir).resolve()
    full = run / "serial.sock"
    if len(str(full)) <= 100:
        _send(str(full), data)
        return
    cwd = os.getcwd()
    try:
        os.chdir(run)
        _send("serial.sock", data)
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    assert sys.argv[2] in VERBS or sys.argv[2].startswith("VM_DENSITY ")
    send(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
