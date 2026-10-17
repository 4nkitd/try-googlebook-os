# v0.1.0-alpha.1

First public experimental release for Apple Silicon Macs.

- Compiled native setup launcher with app icon, packaged as an ARM64 DMG.
- Compact 32-point VM header with Pointer, Full Screen, Settings and Restart controls.
- Captured-pointer speed slider and long control-socket-path fix.
- Homebrew cask in `4nkitd/tap`.

## Install

```sh
brew tap 4nkitd/tap
brew install --cask try-googlebook-os
```

Open **Try Googlebook OS**. First launch prepares the VM locally in Terminal. Budget about
9 GB of downloads and 60 GB of free space, plus Xcode/Homebrew/Android developer tools.
Later launches open the generated VM. The DMG does not contain a preinstalled Google OS image.

The launcher is ad-hoc signed, not notarized. macOS may require approval in Privacy & Security.

## Limits

USB, real Bluetooth and camera startup are disabled in this alpha while the capture design
and physical hardware support are validated. Clipboard, audio, input feel and long-session
reliability remain experimental. This is not a secure daily-driver Googlebook.

No Google recovery-derived images, user data or UTM binaries are redistributed.
Source and checksums are attached alongside the DMG.
