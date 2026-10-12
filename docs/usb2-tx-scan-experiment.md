# USB 2 transmit scheduling experiment

TxScan builds on the Speed experiment and reduces redundant tracker scans in the
common transmit path. It does not claim a measured Xbox throughput improvement.
Compare it with the already tested Speed XEX before adopting it.

## USB 2 budget

High-speed USB 2 has a 480 Mbit/s signaling rate. The ideal bulk-transfer schedule
can carry 13 packets of 512 bytes per 125 microseconds: 53.248 MB/s, or about
50.8 MiB/s, before USB Ethernet framing, Ethernet/TCP traffic, host scheduling,
driver work, and application/storage costs. That is a theoretical bus budget,
not an Xbox FTP target. Both transfer directions share the USB bus.
[Microchip's high-speed USB reference](https://developerhelp.microchip.com/xwiki/bin/view/applications/usb/speeds-specs/high-speed/)
documents the rate and bulk limits.

The reported 19.8 MiB/s is about 166 Mbit/s of file data. It leaves theoretical
room, but does not establish which component limits this console. RGH or a
homebrew exploit permits loading the plugin; it does not raise USB bandwidth.
Retail-kernel RGH/homebrew consoles still require the retail build. A development
kernel has different internal layouts and is a separate target.

## Review findings

The review covered the common NIC/USB path, adapter selection, chipset data
paths, recovery, kernel integration, utilities, headers, and build configuration.
The deepest inspection and change validation focused on the original AX88179
and common transmit scheduler. This is not a full safety audit of every legacy
chipset initialization sequence or the external SDK/xkelib implementation.

| Area | Finding and action |
| --- | --- |
| `CUsbEnet.cpp`: transmit completion | Each priority-class search can walk all 64 trackers. No ready work can cost 192 or 256 visits. TxScan checks the existing active/pending counters and searches the priority classes in one circular pass. |
| `CUsbEnet.cpp`: new transmit tracker | The code counts queued/waiting trackers even when an immediate small frame or an existing pending transfer already determines the answer. TxScan short-circuits those cases and stops at the first queued/waiting tracker. |
| `CUsbEnet.cpp`: receive delivery | Normal Ethernet frames already point into the receive buffer for the callback. Blindly adding a “zero-copy” flag would not remove that callback or XNet/storage work. Buffer lifetime and callback locking need to be preserved. |
| `Ax88179x_178A_772D.cpp` | Original AX88179 RX aggregation already operates within 16 KiB buffers. TX aggregation remains disabled because the source documents XNet/Netshare corruption. The newer AX179A-family format is different. |
| `Ax88178.*`, `Rtl8153.*` | These have different descriptor formats and aggregation handling. Their settings are not substitutes for the UE306's original AX88179 settings. The shared scheduler retains their open-aggregate behavior. |
| `CUsbEnet.h`, `Usbd.h`, NIC headers | Existing limits remain RX 48 x 16 KiB, TX 64 x 12 KiB, up to 24 pending transfers with one slot reserved from title traffic. No structure layout or queue limit changes. |
| `Main.*`, `Hooks.*`, `UsbEnet.*`, detour utilities | Kernel addresses, hook installation, device matching, retail/devkit distinctions, synchronization, and shutdown handling remain unchanged. |
| `UsbEnetChipset.*`, transport wrappers, other utilities | Interfaces and recovery paths remain unchanged. Recovery counters and DMA ordering barriers are not logging-only overhead and were retained. |
| Solution/project, precompiled header, XEX configuration, xkelib reference | TxScan is an explicit Release experiment. The same pinned dependency and installed PowerPC toolchain are used. Deployment remains excluded. |

## What TxScan changes

- `USBENET_TX_SCAN_OPTIMIZATION` defaults to zero in `Main.h`.
- `UsbEnetExperiment=TxScan` enables it and uses the same Speed preference as
  `UsbEnetExperiment=Speed`.
- Under the existing NIC lock, active trackers equal pending trackers only when
  every occupied tracker is already busy. In that case the completion search
  has no eligible work and returns immediately.
- Otherwise one circular scan remembers the first eligible tracker per class.
  Priority remains debug waiting, debug open when pending is zero, title waiting,
  then title open. Busy and queued trackers remain excluded; the reserved debug
  slot remains intact. Circular order within each class is unchanged.
- New-frame submission uses the same boolean decision without counting all
  queued/waiting trackers when the count is unnecessary.

The changes add no queue, allocation, lock, persistent field, USB request, packet
format, or chipset register change. Logging stays off. Both transmitter traffic
and acknowledgements can use this path, so both FTP directions should be tested.

## Build and validation

From a configured Visual Studio/RXDK environment:

```text
MSBuild CUsbEnet.sln /t:Build /p:Configuration=Release /p:Platform="Xbox 360" /p:UsbEnetExperiment=TxScan /p:UsbEnetTargetRetail=true
```

The existing [build guide](conservative-performance-experiment.md) covers the
installed SDK, import-library preparation, output paths, and rollback.

On the user's computer, Visual Studio 2022 Community with the installed Xbox SDK
and RXDK integration successfully built TxScan and the Speed control. Both had
zero errors and the existing two MSB8003 WindowsSDKDir warnings. Compiler logs
confirmed `/Ot` and `DEVKIT_ONLY=0`; only TxScan enabled the optimization macro.
Neither build enabled performance logging or ran `xbecopy`.

`python tests/test_tx_scan.py`, run from an x64 Visual Studio developer prompt,
extracts the actual scheduling and submission-decision code and compiles both
macro settings with host stubs. It passed 409,240 states, comparing submission
sequence, final flags, pending counts, and new-frame decisions. Coverage includes
ring wrap, pending 0/1/22/23/24, free/busy/queued/waiting/open trackers, debug and
title priorities, reset/stop flags, randomized states, and evolving completion /
allocation / DPC-release sequences. Independent expected-order cases check debug
priority and the reserved slot. Assertions remain enabled in the host executable.

In the tested no-unsent-work cases, tracker visits fell from 256 to zero at
pending zero and from 192 to zero at pending one or 22. These are operation
counts, not measured speedups. Host stubs do not validate Xbox interrupt timing,
USB/DMA behavior, real descriptor reuse, or hardware stability.

## Test on the console

1. Preserve the known-working baseline XEX, Speed XEX, and `launch.ini` on the PC
   and console. Have your existing local plugin recovery method available; do
   not rely solely on USB networking to restore it. Do not change NAND.
2. Change only the driver build for this comparison. Load one CUsbEnet plugin,
   using the same installation method that worked for Baseline and Speed.
3. Compare **Speed -> TxScan -> Speed**, rebooting between builds. Use Aurora,
   the same large disposable file, PC, wired route, transfer settings and disk
   locations. Keep at least three timed transfers per build and direction.
4. Test **Xbox -> PC first**, because it exercises the transmit path most
   directly. Also repeat PC -> Xbox. Record completed bytes / elapsed seconds,
   not only the FTP client's momentary speed display; compare medians and spread.
5. Check SHA-256 after downloading the uploaded test file back to the PC.
   Retransfers, disconnects, stalls, dashboard changes and shutdown/restart
   behavior matter even when the final hash matches.
6. If any new issue appears, stop transfers and restore the known-working XEX
   through the existing local recovery route. Reboot and repeat a baseline test.

The reported Baseline 19.6 and Speed 19.8 MiB/s differ by about 1%; repeated runs
are needed to distinguish an improvement from run-to-run variation. Earlier
Aurora results were 19.5 MiB/s PC -> Xbox and 18.0 MiB/s Xbox -> PC. Earlier
XeXMenu 1.1 results were 16.6 and 11.5 MiB/s respectively. Keep those application
results separate. TxScan has no console measurements yet.

No kernel plugin experiment can guarantee freedom from crashes or corrupted
transfers. These checks reduce uncertainty but do not establish console safety.

## Next useful work after this comparison

1. **Separate disk and network costs.** A homebrew RAM-backed TCP send/receive
   benchmark with fixed buffers, byte validation and no file writes would show
   how much of the FTP result belongs to Aurora/SSHD. If RAM-backed throughput is
   similar, focus on the driver/XNet/USB path; if much higher, focus on FTP and
   storage. This benchmark is a proposed next experiment, not included here.
2. **Measure USB utilization.** Existing diagnostics report frames per USB
   completion, bytes per transfer and pending high-water marks. Capturing those
   counters, plus carefully sampled callback time, would identify underfilled
   RX aggregates or expensive delivery. The existing diagnostic build requires
   an actual DbgPrint capture route; simply enabling it does not produce a file.
3. **Tune original-AX88179 RX coalescing only with measurements.** Smaller or
   larger aggregation windows trade latency against completions per second.
   Keep the 16 KiB buffer cap and test one register setting at a time only after
   documenting the original chip's register semantics and collecting baseline
   data. Current presets for newer chips are not sufficient evidence.
4. **Investigate TX batching separately.** Reducing bulk transfers can help on
   chips/formats that support it correctly. Original AX88179 aggregation has a
   documented corruption failure, so a future investigation needs a validated
   framing design and sustained integrity tests before any console trial.
   Changing one capability boolean is not a valid optimization.

More queued requests, more buffers, jumbo frames, a devkit build, or a gigabit
link label do not themselves demonstrate higher useful USB 2 throughput.
