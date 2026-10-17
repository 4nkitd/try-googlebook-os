# Performance notes

Baseline taken 2026-10-17 on a MacBook Pro M4 Pro (12 cores: 8 performance + 4 efficiency),
24 GB RAM, macOS 27.0.1, with Googlebook OS (mica-user build 16471258) on the UTM 5.0.6
QEMU stack.

## Measurements

| Metric | 6 vCPU / 4 GB (default) | 8 vCPU / 4 GB |
| --- | --- | --- |
| Wall clock to `VM_BOOT_COMPLETED` | 40-45 s (guest 39.8-40.8 s) | 41 s (guest 39.9 s) |
| Idle QEMU CPU (60 s windows) | 16.9 cpu-s, about 28% of one core | 13.0 cpu-s, about 22% of one core |
| Idle viewer CPU | about 2% | about 2% |
| Idle render-server CPU | about 0% | about 0% |
| QEMU RSS after boot | 3.4 GB | 3.5 GB |

Notes:

- Idle CPU is noisy: Android background services burst, and repeated 30 s windows ranged
  25% to 37% for the same configuration. Treat 6 versus 8 vCPUs as "no clear difference at
  idle, boot unchanged". The default stays at 6 (lower power ceiling); 8 vCPUs and more
  memory remain available in Settings for heavy sessions.
- A `sample` profile contains many waiting-thread stacks. This does not establish how much
  CPU is spent in the host VMM versus the guest. CPU-weighted profiling and controlled
  before/after tests are still needed before assigning the overhead to either side.
- Interrupts: the guest uses the GICv3 device plus ITS under HVF on UTM's QEMU 10.0.12.
  Plain upstream QEMU 10 releases lack `hw/intc/arm_gicv3_hvf.c` (the Try Omarchy port moved
  to QEMU 11.1.1 for in-hypervisor GICv3); UTM's fork handles GICv3 with HVF on this stack.
- Display stays capped at 60 fps (QEMU does not expose a refresh setting); unchanged from
  upstream.
- Guest noise: `trusty_security_vm_launcher` aborts repeatedly for absent hardware. The log
  churn is observed; its CPU cost has not been isolated or measured.

## Open items, ranked

1. Trusty crash loop: disable the respawning init service in the vendor overlay (image
   change, ships through `update-image.sh`). Removes steady CPU churn and serial-log growth.
2. Memory return to macOS: try virtio-balloon with free-page reporting (verify the guest
   kernel has the driver) so the host gets unused guest RAM back.
3. 60 fps cap: investigate whether a virtio-gpu refresh setting or a guest SurfaceFlinger
   property can raise it.
4. Interactive latency: no objective probe yet; add one (input-to-frame estimate) before
   tuning further.
5. Boot: about 40 s is roughly 5 s kernel plus Android bring-up; repeat boots equal first
   boots, so there is little to reclaim there yet.

## How to reproduce

- Boot: launch the app, wait for `VM_BOOT_COMPLETED` in `work/logs/<run>/serial.log`.
- Idle CPU: `ps -p <qemu-pid> -o cputime=` sampled over 60 s (cumulative CPU seconds).
- Profile: `sample <qemu-pid> 8 -file sample.txt`, then read the "Sort by top of stack"
  section.
