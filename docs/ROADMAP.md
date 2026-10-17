# Try Googlebook OS: roadmap

Program to match the Try Omarchy experience (features and ergonomics) on top of gbos-vm.
Source list: `docs/parity-with-try-omarchy.md`. Updated 2026-10-17.

## Done

- [x] Googlebook OS (ARM64) running locally, GPU-accelerated, boot to desktop verified.
- [x] Guest mouse acceleration disabled (fixes the double-acceleration stacking, upstream issue #4).
- [x] Mouse feel pass 2: mouse-event coalescing off; immediate pointer-speed slider in Settings.
- [ ] Validate USB passthrough end to end. CLI plumbing exists; privileged launch and physical devices are unverified.

The public `v0.1.0-alpha.1` blocks physical USB/Bluetooth capture and root QEMU execution.
Research source is included, but these are not supported release features.

## Performance (active focus)

- [x] Baseline and first A/B (see `docs/PERFORMANCE.md`): boot about 40 s guest; sampled QEMU
      CPU about 22-37% of one core. The samples do not separate host and guest overhead.
      vCPU 6 vs 8 shows no clear difference; default stays 6.
- [ ] Stop the Trusty crash loop (vendor init service) through the image overlay.
- [ ] Free-page reporting / virtio-balloon experiment for host memory.
- [ ] 60 fps cap investigation.
- [ ] Repeatable input-latency probe for interactive tuning.

## M1: input polish (in progress)

- [x] Compact title-bar candidate with Pointer, Full Screen, Settings and Restart. Native layout
      test measured 32 pt versus the former 52 pt. Candidate compiled and screenshot checked.
- [x] Apply compact candidate after approved reboot. Guest control confirmed boot completion in 41.2 seconds wall time.
- [ ] Verify fullscreen transitions and header interactions on the live guest.
- [ ] Live test of the pointer-speed slider; tune default if needed.
- [ ] Raw-HID mouse mode to bypass macOS pointer acceleration entirely (needs Input Monitoring
      permission). Only if the slider is not enough.
- [ ] Polish the two absolute pointer modes (Mac cursor / Android cursor).
- [ ] Immersive: full screen by default option; hide the Mac menu bar and Dock; pass
      Command-key chords to the guest (Accessibility).
- [ ] Window focus: Ctrl-Cmd-F while immersive; keep current shortcuts.

## M2: USB and camera (in progress)

- [x] QEMU `usb-host` command generation and list/stop/status helper code.
- [ ] Privileged USB startup and device identity/permission safety review.
- [ ] Plug-and-test with a real device (webcam or USB drive). No physical-device test has passed yet.
- [ ] Bluetooth bridge prototype: framing self-test, environment discovery and `--bt` forwarding pass;
      device capture, pairing and audio remain unverified. Not release-ready.
- [ ] Viewer Settings UI: device picker, "restart with USB…" flow, no terminal needed.
- [ ] Camera: validate USB capture, the guest UVC driver and Android's external camera provider.
- [ ] Built-in camera sharing requires a separate macOS capture and Android camera bridge;
      it cannot use the USB dongle path. Research remains in scope.

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

- [x] Publish [public source and an ARM64 setup-launcher DMG](https://github.com/4nkitd/try-googlebook-os/releases/tag/v0.1.0-alpha.1),
      source archive and checksums. No Google OS image or UTM binaries are redistributed.
- [x] Publish the `4nkitd/tap/try-googlebook-os` Homebrew cask.
- [x] Replace the ribbed app icon with the open-book/launch-arrow design and retain vector source.
- [ ] Launcher UI: skip option, resources, networking, USB, reset, logs.
- [x] Alpha signing decision: ad-hoc signed with an explicit Gatekeeper warning.
- [ ] Developer ID signing and notarization for wider distribution.
- [ ] Onboarding docs and screenshots.

## Not planned

- Touch ID for sudo / 1Password (Android has no PAM), battery mirror (cosmetic), nested
  virtualization.
