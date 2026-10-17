# Try Googlebook OS: roadmap

Program to match the Try Omarchy experience (features and ergonomics) on top of gbos-vm.
Source list: `docs/parity-with-try-omarchy.md`. Updated 2026-10-17.

## Done

- [x] Googlebook OS (ARM64) running locally, GPU-accelerated, boot to desktop verified.
- [x] Guest mouse acceleration disabled (fixes the double-acceleration stacking, upstream issue #4).
- [x] Mouse feel pass 2: mouse-event coalescing off; immediate pointer-speed slider in Settings.
- [x] USB passthrough plumbing: `run_vm.py --usb`, `run/usb_launch.py` with the admin flow.

## M1: input polish (in progress)

- [ ] Live test of the pointer-speed slider; tune default if needed.
- [ ] Raw-HID mouse mode to bypass macOS pointer acceleration entirely (needs Input Monitoring
      permission). Only if the slider is not enough.
- [ ] Polish the two absolute pointer modes (Mac cursor / Android cursor).
- [ ] Immersive: full screen by default option; hide the Mac menu bar and Dock; pass
      Command-key chords to the guest (Accessibility).
- [ ] Window focus: Ctrl-Cmd-F while immersive; keep current shortcuts.

## M2: USB and camera (in progress)

- [x] QEMU `usb-host` flag, privileged start, list/stop/status helper.
- [ ] Plug-and-test with a real device (webcam or USB drive).
- [ ] Viewer Settings UI: device picker, "restart with USB…" flow, no terminal needed.
- [ ] Camera: USB webcam through the passthrough flow. Built-in camera cannot be passed;
      a virtual camera bridge stays R&D (see `docs/usb-passthrough.md`).

## M3: clipboard

- [ ] Test and harden copy-out (guest to Mac; implemented but untested upstream).
- [ ] PNG images both ways (currently text only).
- [ ] Verify the "nothing transferred until copied" semantics.

## M4: audio

- [ ] Fix flaky boot audio (silent on some boots).
- [ ] CoreAudio device pickers for output; live routing; system-default fallback.
- [ ] Microphone capture path.

## M5: networking

- [ ] Loopback port forwarding (TCP/UDP) + an adb preset; document reverse access via 10.0.2.2.
- [ ] Bridged mode (vmnet helper and permission flow).
- [ ] Regenerate MAC button.

## M6: window and display

- [ ] Resizable window with live guest resolution signaling (investigate `wm size`/`wm density`
      while running).
- [ ] 60 fps cap (QEMU refresh setting; upstream-level).

## M7: storage and VM management

- [ ] Shared folder: evaluate options for an Android guest (adb-based sync, network share in
      Files, virtiofs feasibility).
- [ ] Choose VM folder in the UI; reset with confirmation; ephemeral launch; disk growth tools.
- [ ] In-app update check; keep `update-image.sh` as the image updater.

## M8: productization

- [ ] Launcher UI: skip option, resources, networking, USB, reset, logs.
- [ ] Signing/notarization decision for distribution beyond this Mac (needs Apple Developer account).
- [ ] Onboarding docs and screenshots.

## Not planned

- Touch ID for sudo / 1Password (Android has no PAM), battery mirror (cosmetic), nested
  virtualization.
