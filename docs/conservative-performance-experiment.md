# Conservative CUsbEnet build experiment

The follow-up [USB 2 transmit scheduling experiment](usb2-tx-scan-experiment.md)
adds an opt-in `TxScan` build based on Speed. The original experiments below
retain their existing runtime behavior.

Status: built locally with VS 2022 RXDK. The user subsequently reported that
Baseline works and Speed transfers at roughly 19.8 versus 19.6 MiB/s. That is
not yet a controlled performance result. The agent has not deployed any build.
Base: proferabg/CUsbEnet main at 6b29507d1808d6e5a1716c85a94aa52ae84df8de;
pinned xkelib a6353be8e81e1e5910f6b28183707caa75458c7c.

## Scope

Default builds are unchanged. Opt-in Release experiments are:

| Experiment | Compiler preference | Performance logging |
| --- | --- | --- |
| Baseline | Size (upstream) | Off (upstream default) |
| Speed | Speed | Off |
| Diagnostics | Size | Existing USBENET_PERF_LOGGING enabled |

Speed changes only the size/speed compiler preference; full optimization was
already enabled. Diagnostics enables the existing five-second summaries, not
ordinary USBENET_DEBUG output. Logging can change timing and throughput: do not
use Diagnostics results as a clean Speed comparison. DbgPrint requires a working
debug capture path; FTP does not collect it. Do not install a debugger/plugin or
pause the kernel simply to obtain these logs on the retail console.

The three original experiments do not change runtime source behavior. AX88179 TX aggregation remains disabled because the
upstream comment reports timing-sensitive XNet corruption. RX stays 48 x 16 KiB,
TX stays 64 x 12 KiB, and maximum pending TX stays 24. Kernel hooks, addresses,
USB queue settings, recovery logic, and dependency revision are unchanged.

## Build only

Requires VS 2022 RXDK legacy Xbox 360 build integration and legally
available Xbox SDK. Initialize pinned dependencies with:

```powershell
git submodule update --init --recursive
```

From the solution directory in a properly configured build shell:

```powershell
msbuild CUsbEnet.sln /t:Build /p:Configuration=Release "/p:Platform=Xbox 360" /p:UsbEnetExperiment=Baseline /p:UsbEnetTargetRetail=true
msbuild CUsbEnet.sln /t:Build /p:Configuration=Release "/p:Platform=Xbox 360" /p:UsbEnetExperiment=Speed /p:UsbEnetTargetRetail=true
msbuild CUsbEnet.sln /t:Build /p:Configuration=Release "/p:Platform=Xbox 360" /p:UsbEnetExperiment=Diagnostics /p:UsbEnetTargetRetail=true
```

Use Build only, never a console-connected debug launch. Experimental builds set
Deploy.ExcludedFromBuild=true because RXDK hooks Deploy after ImageXex even for
Build. Keep that exclusion: the initial attempts reached xbecopy and failed
because no console target was configured. Nothing was deployed.
Output is isolated under
`Build/CUsbEnet/Experiments/<Experiment>/Retail-true/`, including intermediates,
PDB and `CUsbEnet-<Experiment>.xex`. The normal `CUsbEnet.xex` is not overwritten.
Keep hashes and compiler/build logs for each artifact.

The retail flag explicitly defines DEVKIT_ONLY=0 for these experimental builds;
upstream Main.h defaults to 1 and rejects a retail console. Use the same target
flag for all comparisons; false selects the upstream devkit mode. This selection
does not prove compatibility with a particular exploit/plugin combination.
Do not add custom logging or compiler definitions during the comparison.
Invalid experiment names, non-Release experiments, and missing target choice
are rejected during PrepareForBuild.

## Validation performed on 12 October 2026

Downloaded the exact source and pinned submodule. XML parsing and diff whitespace
checks passed. An isolated MSBuild property evaluation verified Baseline/Speed/
Diagnostics flags, unchanged defaults, and rejection of invalid experiment names.
VS 2019 failed due to missing legacy props; VS 2022 Community 17.14.6 has RXDK
integration and the Xbox SDK PowerPC compiler 16.00.11886.00. All three retail
variants compiled, linked, generated isolated XEX files, and completed Build with
exit code 0 after excluding deployment. Compiler logs confirm /Os for Baseline
and Diagnostics, /Ot for Speed, DEVKIT_ONLY=0 for all, and performance logging only
for Diagnostics. A WindowsSDKDir warning remains, but did not prevent these builds.

Experimental build metadata explicitly names the existing stdafx.h PCH and aligns
OutputFile, TargetPath and linker output for RXDK; no PCH content changed.
RXDK did not run xkelib's upstream prebuild library-generation event here, so the
same pinned definitions were built manually before the solution build:

```powershell
Push-Location libraries/xkelib
& "$env:XEDK/bin/win32/lib.exe" /def:xam/xamext21256.0.def /MACHINE:PPCBE /OUT:xamext.lib
& "$env:XEDK/bin/win32/lib.exe" /def:kernel/kernelext21256.0.def /MACHINE:PPCBE /OUT:kernelext.lib
Pop-Location
```

No installed VS/RXDK/SDK files were changed. The agent has not performed console
runtime validation; the user's subsequent observations are recorded above.
Build success does not establish data integrity, stability or improved throughput.
## Recovery prerequisites before any later console test

Kernel plugins cannot guarantee zero crashes, corruption, or risk. Optimization
can expose timing or undefined-behavior issues even when source logic is unchanged.
The agent builds locally and does not deploy to the console.

Before considering a test, preserve the working XEX and exact launch.ini locally
and on separate removable storage. Record hashes and original plugin paths/order.
Confirm a recovery route that works on this exact ABadAvatar 1.3 + Bad Storage 1.2
Unauthenticated + XeUnshackle setup, without relying on this USB network driver:
for example an already verified independent file manager/storage access route.
Do not assume DashLaunch recovery shortcuts apply to this exploit configuration.
If recovery cannot be verified, do not test the experimental plugin.

Never touch NAND, flash firmware, change kernel hooks, or overwrite the working
XEX. If a later test is authorized, use a separate named experimental file and
preserve a way to restore the original loading configuration. Do not hot-swap or
unload a live driver as a recovery strategy. On a freeze, corruption, connection
loss or boot failure, stop testing and use the verified independent route to
restore the original XEX path and launch.ini, then restart into the known working
setup. Power cycling alone does not remove an auto-loaded faulty plugin.

## Benchmark plan

User-reported setup: retail dashboard 17559, UE306/AX88179, internal SSHD,
ABadAvatar 1.3, Bad Storage 1.2 Unauthenticated, XeUnshackle.

| FTP server | PC to Xbox | Xbox to PC |
| --- | ---: | ---: |
| Aurora | 19.5 MiB/s | 18.0 MiB/s |
| XeXMenu 1.1 | 16.6 MiB/s | 11.5 MiB/s |

These are prior observations, not fresh controlled measurements. Parallel FTP
did not help. Compare a freshly built Baseline against Speed with logging off,
then restore Baseline and repeat (A/B/A). Also retain the existing working binary
as the recovery control; it may not match this source/toolchain exactly.

Use the same PC, cable, USB port, adapter, FTP client settings, storage location,
and large non-critical file (preferably at least 1 GiB). Test Aurora and XeXMenu
separately, one transfer at a time, at least three runs per direction/build.
Alternate build order, allow comparable SSHD/cache conditions, record elapsed
seconds and exact bytes, and compute MiB/s as bytes / seconds / 1048576.
Record median and range, failures, reconnects, and hangs. Copy downloaded test
data back to the PC and compare SHA-256 with the original for integrity in both
directions; also verify size. A speed increase with corruption is a failed test.
Stop immediately at instability, hash mismatch, or sustained regression.
Diagnostics is optional and separate, only if debug capture is already available.

## Revert

For an upstream-style build, omit both experiment properties; for a retail
control with isolated output, select Baseline and UsbEnetTargetRetail=true.
To undo the source patch after it is committed, use `git revert <experiment-commit>`
on the experiment branch. The fork main branch remains the untouched upstream
base. Source reversion does not restore a deployed plugin; restore the preserved
working XEX and loading configuration through the verified recovery route.
