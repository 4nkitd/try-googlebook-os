# Parity checklist: Try Omarchy features vs our Googlebook OS VM

As of 2026-10-17. Compares the Try Omarchy Mac app feature set with our current gbos-vm based setup.

Legend: done / partial / missing. Effort is rough: S = hours, M = days, L = a week+, XL = research project.

## Interaction and window

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Full screen | done (Ctrl-Cmd-F) | Immersive default, hide Mac menu bar/Dock, Command belongs to guest capture | S/M |
| Resizable window, auto guest resolution + HiDPI | missing | Window resize signaling into QEMU/Android resolution change | L |
| Seamless vs captured pointer | partial | Three modes exist; polish Mac cursor and Android cursor; guest acceleration disabled 2026-10-17 | M |
| System shortcuts reach guest (Accessibility) | missing | Optional accessibility bridge | M |

Touch ID for sudo and 1Password: not applicable, Android has no PAM stack.

## Clipboard

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Paste into guest (text) | implemented for absolute pointer mode; end-to-end verification pending | fix captured-mode Cmd-V and test | S |
| Copy guest to Mac (text) | partial (implemented, untested) | test and harden | S |
| Images (PNG) both directions | missing | add image formats | M |
| Nothing transferred until copied | partial | verify semantics | S |

## Audio

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Audio output in guest | partial (flaky on some boots) | fix dropouts, verify | M |
| Mac device pickers, live routing | missing | CoreAudio device list + switch, system default fallback | M |
| Microphone | missing | usb-audio capture path + permission flow | M |

## Camera

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Mac camera in guest | missing | Option A: USB webcam passthrough (recommended; needs USB feature). Option B: emulated camera bridge feeding Android | M with A, XL for B |

## Storage and sharing

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Shared Mac folder | missing | Android guest makes 9p/virtiofs unlikely; consider adb-based sync, network share visible in Files, or virtiofs investigation | L |
| Shared folder safety policy | n/a | borrow Try Omarchy's warnings if built | - |

## Networking and ports

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| NAT | done | - | - |
| Bridged mode + helper | missing | vmnet-bridged helper with permission flow | M/L |
| Stable MAC / regenerate MAC | done (static) / missing | keep; add regenerate | S |
| Loopback port forwarding (TCP/UDP) | missing | QEMU hostfwd + settings UI; adb preset | S/M |
| Reverse access to Mac services | done (10.0.2.2) | document it | S |
| SSH preset analog | n/a | adb connect preset instead | S |

## USB

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| USB device passthrough (one device, no hubs) | missing in UI | usb-host is compiled into our QEMU; gate is macOS permissions (root/admin or Apple's restricted entitlement). Build admin-mode flow + device picker + bus/port pinning + safety notes (unmount drives first, replug caveats) | M |

## VM management and distribution

| Feature | Us | To replicate | Effort |
|---|---|---|---|
| Launcher with settings (skip, resources, reset) | missing | productization milestone | M |
| CPU/memory settings | done (applies next boot) | keep | - |
| Max disk size control | missing | resize flow + docs | S/M |
| Choose VM folder | partial (GOOGLEBOOK_WORK env) | UI | S |
| Reset with confirmation / ephemeral VMs | missing | launcher work | S/M |
| Clean shutdown on quit | done | - | - |
| Guest console log | done (serial.log per run) | - | - |
| Updates | partial (update-image.sh) | in-app check later | S |
| Signed + notarized distribution | missing | Apple Developer account decision | S/M |

## Nice to have

| Feature | Note |
|---|---|
| Battery mirror | cosmetic |
| Locale inheritance | nice-to-have |
| Memory reclamation | virtio balloon / free page reporting, needs investigation |
| 60 fps display cap | QEMU refresh setting, upstream |
| Trusty/TPM crash loop | observed log churn; CPU impact not isolated |

## Applied fixes

- 2026-10-17: guest-side mouse acceleration disabled (`mouse_pointer_acceleration_enabled=0`, `pointer_speed=0`) for the current user. Matches upstream issue #4 (double acceleration from macOS and guest stacking). Persists in userdata; can be toggled back in Googlebook OS settings.
- 2026-10-17: mouse pass 2 shipped: event coalescing off; live pointer-speed slider (Settings, 0.25-3.0). Viewer rebuilt, VM re-verified on the new build.
- 2026-10-17: USB/Bluetooth prototype code exists, but physical passthrough and privileged startup are unverified. Earlier "shipped" wording overstated readiness; see `usb-passthrough.md`.
- 2026-10-17: compact header candidate uses native title-bar accessories. Layout fixture measured 52 to 32 pt; running VM has not been restarted to apply it.
