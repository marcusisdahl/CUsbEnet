# CUsbEnet

**A USB Ethernet driver for homebrew-capable Xbox 360 consoles, with ASIX/Realtek support and experimental throughput tuning in this fork.**

CUsbEnet lets a supported USB Ethernet adapter provide networking through the Xbox 360's existing XNet/NIC interfaces. Dashboards, FTP servers, and other network applications can then use the connection through their normal networking APIs. The driver is loaded as an XEX plugin; applications such as Aurora or FastFTP provide the file-transfer interface.

This is a fork of [proferabg/CUsbEnet](https://github.com/proferabg/CUsbEnet), which ports the early Xbox 360 USB Ethernet driver and extends chipset support and XNet integration. Upstream attribution, GPL notices, and hardware-driver provenance are retained.

**Reported result:** the maintainer reports **29.1 MiB/s with a TP-Link UE306 USB Ethernet adapter**. That is approximately **30.5 MB/s / 244.1 Mbit/s** of transferred data. See [measurement context](#reported-performance) before comparing it with another setup.

## What it does

- Detects supported adapters by USB vendor/product IDs and, where needed, device revision.
- Initializes the adapter's Ethernet link, addressing, receive filters, and transfer format.
- Exchanges Ethernet frames through asynchronous USB transfers and the Xbox's networking callbacks.
- Handles link-state notifications, RX/TX buffering, and recovery paths for failed or stalled transfers.
- Provides title networking and a separate checked/devkit XBDM path where the matching kernel/build supports it.

A compatible adapter may negotiate a gigabit Ethernet link, but the Xbox's USB connection, driver, network stack, application, and storage still determine useful throughput. A USB 3.0 adapter does not make the console's USB path USB 3.0.

## Reported performance

| Item | Report |
|---|---|
| Adapter | **TP-Link UE306**, using the AX88179-based setup reported by the maintainer |
| Final reported rate | **29.1 MiB/s** |
| Decimal equivalents | Approximately **30.5 MB/s**, or **244.1 Mbit/s** |
| Test application / method | Not specified in the report |
| Direction | Not specified in the report |
| Driver revision / configuration | Exact driver commit and build switches not recorded |
| Evidence | Maintainer-reported result, recorded **13 October 2026** |

This is a result from one setup, not a guaranteed rate for every adapter, console, build, or transfer direction. It is not attributed to the default `main` implementation or to a particular experimental switch without a recorded build. RAM network throughput, FTP file copying, and USB-disk copying are different workloads; compare like-for-like tests.

For a reproducible comparison, record the driver commit and compile-time switches, console kernel, adapter hardware/USB IDs, transfer direction, application/version, file size or benchmark duration, stream count, rate cap, and integrity-check result. Use several completed runs and compare medians; a momentary peak or interrupted run is not a final throughput result.

## Main code and experimental branches

The default `main` branch currently contains the upstream-derived baseline **driver code**. The performance changes below are on separate branches; updating this README does not merge them into `main`.

| Branch / work | Purpose |
|---|---|
| [`main`](https://github.com/marcusisdahl/CUsbEnet/tree/main) | Baseline driver implementation and repository overview |
| [`experiment/conservative-build-performance`](https://github.com/marcusisdahl/CUsbEnet/tree/experiment/conservative-build-performance) | Separate Baseline, Speed, and Diagnostics build choices; size/speed compiler preference and optional logging |
| [`experiment/usb2-tx-scheduler`](https://github.com/marcusisdahl/CUsbEnet/tree/experiment/usb2-tx-scheduler) | Opt-in reduction of redundant transmit-tracker scans |
| [Throughput work / PR #1](https://github.com/marcusisdahl/CUsbEnet/pull/1) | Larger RX/TX buffers, batched receive delivery, and experimental AX88179 transmit aggregation |
| [`claude/project-thread-hy4q3s`](https://github.com/marcusisdahl/CUsbEnet/tree/claude/project-thread-hy4q3s) | Further small-frame/ACK coalescing experiments, RX-size switches, CPU timing diagnostics, and TP-Link UE300 ID matching |

Check the [branches](https://github.com/marcusisdahl/CUsbEnet/branches) and [pull requests](https://github.com/marcusisdahl/CUsbEnet/pulls) for their current status. Select the intended branch before building and keep the resulting XEX associated with its commit and settings.

In the baseline code, RX uses **48 × 16 KiB** buffers, TX uses **64 × 12 KiB** buffers, and the pending transmit limit is **24**, with one slot reserved from title traffic. The newer throughput branch changes buffer/receive-delivery behavior; those changes are not descriptions of `main`.

### Original AX88179 transmit aggregation

The baseline deliberately keeps multi-frame TX aggregation **off** on the original AX88179. Its source documents timing-sensitive XNet/Netshare corruption from earlier aggregation experiments.

Performance branches expose opt-in switches for further investigation. Their presence is not proof that aggregation is stable. Branch history also records a console freeze during a full-size aggregated transmit experiment. Keep these experimental defaults off for an initial control, preserve a working build, and validate complete data and both directions before relying on an experimental configuration. A single pre-test check or higher speed does not establish correctness.

## Adapter support

Support depends on the adapter's **chipset, USB IDs, hardware revision, and driver branch**, rather than its brand name alone.

| Backend included in the source | Notes |
|---|---|
| ASIX AX88178 | Legacy ASIX backend |
| ASIX AX88178A | AX88179/178A family backend |
| ASIX AX88179 | Original AX88179 path; maintainer's reported UE306 setup |
| ASIX AX88179A/B | Revision-specific family path |
| ASIX AX88772D | Revision-specific ASIX path |
| ASIX AX88279 | Revision-specific ASIX path |
| Realtek RTL8153 v3–v6 | Subject to the backend's hardware-version checks |
| Realtek RTL8153B v8/v9 | Subject to the backend's hardware-version checks |

[TP-Link's UE306 V1 specification](https://www.tp-link.com/us/home-networking/usb-converter/ue306/v1/) identifies an **AX88179** chipset. Verify the actual device revision; similarly named products and later revisions can differ.

The additional TP-Link **UE300 ID `2357:0601`** is mapped to the RTL8153 backend on `claude/project-thread-hy4q3s`. That additional ID mapping is not currently in the baseline `main` code. Generic support for a chipset does not imply that every rebranded USB ID is recognized.

## Kernel and build compatibility

CUsbEnet uses private kernel interfaces, fixed addresses, and kernel-dependent structure layouts. The current retail address path is written for **dashboard/kernel 17559**; other kernel versions require verification and porting.

**The build target must match the kernel.** A homebrew exploit or RGH modification does not by itself turn a retail kernel into a devkit kernel.

- **Retail kernel:** build with `DEVKIT_ONLY=0`.
- **Matching devkit/checked kernel:** use the devkit layout and `DEVKIT_ONLY=1`, with its addresses and dependencies verified for that kernel.
- `CUsbEnet/Main.h` defaults `DEVKIT_ONLY` to **1** when no compiler definition overrides it. The plain default build should not be assumed suitable for a retail console.

Use a matched Release build for normal comparisons. Debug output, profiling, compiler choices, and experimental switches can change timing and throughput.

## Load the driver

1. Preserve your current working driver and plugin configuration, and keep your existing local recovery method available.
2. Copy the matched `CUsbEnet.xex` build to the console.
3. Load it through the plugin method appropriate for your setup:
   - **DashLaunch:** configure CUsbEnet as the first plugin in `launch.ini`, before `xbdm.xex` when used.
   - **RGLoader:** configure it as the first plugin in `rgloader.ini`.
   - **Other retail homebrew setups:** use the plugin loader supported by that exploit/homebrew chain; DashLaunch instructions are not automatically applicable.
4. Load one CUsbEnet instance, attach a supported adapter, and use your normal network application. Confirm that traffic is using the USB adapter when measuring it.

This is a driver plugin, so its loading procedure differs from launching a standalone FTP server. Loading/unloading after boot is possible in some setups but can encounter lifecycle issues. Kernel-driver experiments can hang or crash a console; retain the working build and stop testing if transfers corrupt data or stability changes. Driver installation/testing does not require NAND changes.

## How frames move

On transmit, XNet hands an Ethernet frame to the driver. CUsbEnet copies it into an aligned DMA transfer buffer, adds the chipset's USB framing, and submits the request to the USB stack. Chipset support and build settings determine whether a transfer contains one frame or an aggregate.

On receive, the driver parses the adapter's USB data, identifies valid Ethernet frames and destinations, applies receive filtering, and delivers frames through the registered networking callbacks. Link changes and transfer failures feed the existing notification and recovery paths. The experimental receive-batching work aims to reduce repeated lock/callback overhead; it is separate from changing an application's FTP implementation.

## Build from source

Requirements: a compatible installed Xbox 360 SDK/toolchain, Xbox 360 Visual Studio platform integration (the project uses toolset `2010-01`), and the `xkelib` Git submodule. The SDK is not included.

```text
git clone --recurse-submodules https://github.com/marcusisdahl/CUsbEnet.git
cd CUsbEnet
```

For an existing checkout:

```text
git submodule update --init --recursive
```

1. Select the branch you intend to build.
2. Open `CUsbEnet.sln` and select **Release | Xbox 360**.
3. For a retail kernel, add **`DEVKIT_ONLY=0`** to the Release C/C++ preprocessor definitions so it overrides `Main.h`'s devkit default. Verify the compiler command line contains the intended definition.
4. Check deployment settings before building. The baseline project contains deployment settings, and some SDK/RXDK integrations can copy to a configured console as part of a build. Exclude deployment from the build when preparing a file for manual testing.
5. Build the solution and inspect the output/errors before transferring the XEX manually.

The Release image output is `Build\CUsbEnet\CUsbEnet.xex`. The project references import libraries from the `libraries/xkelib` submodule and an xkelib configuration named `Release21256.0`; dependency and target-kernel compatibility still need to match your environment.

The conservative experiment branches additionally expose project properties such as `UsbEnetExperiment` and `UsbEnetTargetRetail`. These properties are branch-specific and are not substitutes for checking the plain `main` project's actual compiler definitions.

### Diagnostic and experimental switches

These are compile-time settings; availability depends on the selected branch.

| Switch | Default | Purpose / availability |
|---|---|---|
| `USBENET_DEBUG` | `0` | Ordinary driver output; enabled logging can alter timing |
| `USBENET_PERF_LOGGING` | `0` | Periodic performance counters; requires an actual debug-output capture route |
| `USBENET_CONNECTION_LOGGING` | `0` | Extra connection diagnostics |
| `USBENET_TX_SCAN_OPTIMIZATION` | `0` | Transmit-scan experiment on `experiment/usb2-tx-scheduler` |
| `USBENET_AX88179_TX_AGGREGATION` | `0` | Original-AX88179 aggregation experiment on the throughput branches |
| `USBENET_COALESCE_TITLE_SMALL_FRAMES` | `0` | Small retail-title frame/ACK coalescing experiment on the later throughput branch |
| `USBENET_TX_AGGREGATE_SMALL_ONLY` | `0` | Restricts experimental aggregation to small frames on the later throughput branch |
| `USBENET_AX88179_RX_26K` | `0` | Experimental 26 KiB AX88179 RX transfers on the later throughput branch |
| `USBENET_AX88179_RX_32K_UNTESTED` | `0` | Explicitly unvalidated 32 KiB AX88179 RX option on the later throughput branch |

The RX-size overrides are mutually exclusive. Aggregation/coalescing switches have chipset and interaction constraints; inspect the selected branch's source before configuring them. This table documents available research controls, not a recommended set of switches for reproducing the 29.1 MiB/s report.

## License and credits

CUsbEnet is licensed under the GNU General Public License, version 2 only (**GPL-2.0-only**). See [LICENSE](LICENSE).

Hardware initialization and descriptor handling were developed with reference to GPL-2.0-licensed Linux USB Ethernet drivers, including `r8152`. Preserve GPL notices, SPDX identifiers, upstream attribution, and provenance comments when modifying or redistributing the source.

Upstream project: [proferabg/CUsbEnet](https://github.com/proferabg/CUsbEnet). This fork is not affiliated with or endorsed by Microsoft, TP-Link, ASIX Electronics, or Realtek Semiconductor.
