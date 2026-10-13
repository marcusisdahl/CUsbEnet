# CUsbEnet  [![Github All Releases](https://img.shields.io/github/downloads/proferabg/CUsbEnet/total.svg)]()

## Overview

CUsbEnet is a USB Ethernet driver for modified Xbox 360 systems. Microsoft
originally added the driver to various early Xbox 360 recoveries for use with
advanced Xbox 360 development kits. The hardware project was later cancelled and 
the driver was thus removed from the Xbox 360 kernel. This is a port of that 
driver with support for additional chipsets outside the original AX88178 driver
and better XNet registration. CUsbEnet registers supported ASIX and Realtek 
adapters with the Xbox 360 USB stack and integrates them with the console's 
existing XNet and NIC infrastructure.

## Features

The driver supports title networking and checked/devkit XBDM traffic, including
separate title and debug unicast addresses where required. It provides link-state
reporting, receive filtering, USB RX/TX buffering, transmit aggregation for
capable chipsets, and recovery for failed or stalled transfers.

CUsbEnet uses private Xbox 360 kernel interfaces and build-specific structure
layouts. Kernel addresses, ABI assumptions, and hook targets must be verified
before using the driver with a kernel version other than the one for which it
was built. This is experimental kernel-level software and should be tested
carefully on each adapter and console configuration.

## Installation

Copy `CUsbEnet.xex` to the console, then configure it as the first plugin so
the USB Ethernet driver loads before any other plugins.

- **DashLaunch:** Add `CUsbEnet.xex` as the first plugin entry
  in `launch.ini`, before `xbdm.xex`.
- **RGLoader:** Add `CUsbEnet.xex` as the first plugin entry in `rgloader.ini`.

Alternatively, the plugin can be loaded and unloaded after boot but may encounter issues.

## Supported chipsets

| Chipset |
| --- |
| ASIX AX88178 |
| ASIX AX88178A |
| ASIX AX88179 |
| ASIX AX88179A/B |
| ASIX AX88772D |
| ASIX AX88279 |
| Realtek RTL8153 v3-v6 |
| Realtek RTL8153B v8/v9 |

## Build options for throughput testing

These compile-time switches live in `CUsbEnet/Main.h`:

| Switch | Default | Purpose |
| --- | --- | --- |
| `USBENET_DEBUG` | 0 | Ordinary driver output. Keep at 0 when measuring; debug output slows the driver. |
| `USBENET_PERF_LOGGING` | 0 | Prints a five-second throughput summary (drops, USB transfer sizes, TX scheduling). |
| `USBENET_AX88179_TX_AGGREGATION` | 0 | Experimental: several frames per USB transfer on the original AX88179. Only use it after full-data checks pass, for example with NetBench360's "All data" check. |
| `USBENET_COALESCE_TITLE_SMALL_FRAMES` | 0 | Experimental, retail kernels: small title frames (mostly TCP ACKs during downloads to the Xbox) join an open transfer while other transmits are in flight, instead of each taking its own USB transfer. Needs transmit aggregation, so on the original AX88179 combine it with `USBENET_AX88179_TX_AGGREGATION`. |

## License

CUsbEnet is licensed under the GNU General Public License, version 2 only
(`GPL-2.0-only`). The complete license text is provided in [LICENSE](LICENSE).

Hardware initialization and descriptor handling were developed with reference
to GPL-2.0-licensed Linux USB Ethernet drivers, including the Linux `r8152`
driver. GPL notices, SPDX identifiers, attribution, and provenance comments must
be preserved when modifying or redistributing this project.

This project is not affiliated with or endorsed by Microsoft, ASIX Electronics,
or Realtek Semiconductor.
