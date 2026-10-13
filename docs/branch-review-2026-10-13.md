# Branch review — 13 October 2026

The conservative build options and optional TxScan scheduling are integrated into
`main`. Larger buffers, receive batching, and aggregation experiments remain on
`claude/project-thread-hy4q3s`. The review does not establish that every experimental
configuration is stable on a console, and no new build was deployed.

## Reviewed revisions and decisions

| Original branch | Reviewed head | Decision |
| --- | --- | --- |
| `main` | `bc12bbe50c584e014d797f7fe46477c55ed04413` | Preserve the current README, upstream implementation, and attribution; integrate conservative options |
| `experiment/conservative-build-performance` | `63ffb57f22395f071a2f4b0544c1ef4c34e3a0ed` | Integrate through its TxScan descendant, then remove the redundant branch |
| `experiment/usb2-tx-scheduler` | `cc34dcdb9a455f92f501e1cab861b4f135586f65` | Integrate the reviewed, optional scheduler and its host tests, then remove the redundant branch |
| `claude/project-thread-0n0gng` | `69f23478e6dd9a7aac63c9adf22edab5cf21119f` | Superseded by the newer throughput branch; close draft PR #1 and remove the redundant branch, retaining its commits in that descendant |
| `claude/project-thread-hy4q3s` | `4ffcef551ad9701abdb010364c3b1e46ca759035` | Retain separately; compile checks pass, but a validated driver configuration for the 29.1 MiB/s report is not recorded |

The removed branches are merged or superseded copies. Their age alone is not
evidence of a defect. No unique experiment is discarded, and the earlier throughput
commits remain reachable through the retained branch.

## Changes accepted into main

- Explicit Baseline, Speed, Diagnostics, and TxScan Release build choices with
  separate output paths and explicit retail/devkit selection.
- Deployment excluded for those opt-in builds.
- Optional TxScan scheduling that reduces redundant tracker searches while
  preserving tracker priority, ring order, pending limits, and the reserved debug slot.
- The existing host scheduling test and build/recovery guides.

With the experiment properties omitted, the original project settings remain.
`USBENET_TX_SCAN_OPTIMIZATION` defaults to zero. Baseline RX remains 48 × 16 KiB,
TX remains 64 × 12 KiB, and pending TX remains 24 with a title limit of 23.
Kernel hooks, addresses, packet formats, chipset registers, and the pinned xkelib
revision are unchanged. Original AX88179 transmit aggregation remains disabled.

## Validation and its limits

The combined source built Baseline, Speed, TxScan, and Diagnostics with Visual
Studio 2022 Community, the installed RXDK integration, and the Xbox 360 SDK.
The builds use the retail definition `DEVKIT_ONLY=0`; none ran console deployment.
The existing two MSB8003 WindowsSDKDir warnings remain. Generated images have
XEX2 headers. TxScan's extracted scheduling code passed 409,240 host states,
checking submission order, flags, pending limits, and new-frame decisions against
the original implementation.

Earlier user reports say Baseline worked, Speed was approximately 19.8 MiB/s,
and TxScan was approximately 19.7–19.9 MiB/s PC → Xbox with steadier behavior;
Xbox → PC was approximately 18 MiB/s. Those are informal observations, without
recorded full-file integrity checks or enough evidence to promise a speed gain.
This review did not repeat those console tests.

The newer throughput branch was exported at its exact head and compiled with
temporary local project overrides for retail targeting, isolated outputs, and
deployment exclusion. Default aggregation-off, Diagnostics, and small-frame-only
aggregation configurations compiled. Those overrides were not committed to that
branch. Build success does not validate USB/DMA timing, callback lifetimes,
hardware limits, data integrity, or console stability. Neither branch has CI
results that establish hardware correctness.

## Why the throughput work remains experimental

Its base changes RX to 24 KiB, TX to 16 KiB, receive delivery to batches, and
chipset-specific aggregate thresholds. Later commits add small-frame coalescing,
small-only aggregation, 26/32 KiB RX options, CPU diagnostics, and a TP-Link UE300
USB ID. These features need checks beyond the host scheduler test.

Commit `db2127ccbb735a4e94f4f6111cc7a0b458afc3f5` records a console freeze during
unlimited Xbox → PC sends with full-size AX88179 aggregation enabled. The later
small-only switch is a proposed restriction, not a demonstrated repair. The
`__sync()` submission barrier also exists in the reviewed baseline, so its presence
does not establish that aggregation corruption has been fixed by this branch.

Receive batching snapshots only the first 16 attached users before filtering,
whereas baseline snapshots up to 16 matching users per frame. With more than 16
attached users this can omit a matching recipient. Typical title/debug use may
have fewer users, but that assumption needs enforcement or correction before
promoting the implementation as generally equivalent.

The maintainer's final 29.1 MiB/s measurement is an FTP upload from PC → Xbox
using a TP-Link UE306. Its exact driver commit, switches, and FTP software versions
remain unrecorded. It cannot yet identify which experimental configuration should
be promoted. Record those details and completed integrity/stability checks in both
directions before considering the remaining throughput work for main.

## History and recovery

The integration retains the conservative branch history. The retained throughput
branch contains the older throughput head as an ancestor. A verified complete
Git bundle of all five original remote branch heads was also saved locally before
cleanup as `CUsbEnet-branches-before-cleanup.bundle`.

To undo the conservative integration, revert its merge commit with mainline parent
1. A source revert does not replace a loaded console plugin: retain the working
XEX and plugin-loading configuration and restore them through the existing local
recovery route if needed. This repository cleanup does not require NAND changes.
