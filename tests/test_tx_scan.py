"""Compile actual driver scheduling code twice and compare observable decisions.

Run from an x64 Visual Studio developer prompt: python tests/test_tx_scan.py
Only the pure locked scheduling logic runs on the host. USB submission, packets,
and device fields are stubs; this cannot validate Xbox DMA, timing, or recovery.
"""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
source = (ROOT / "CUsbEnet/CUsbEnet.cpp").read_text()
header = (ROOT / "CUsbEnet/CUsbEnet.h").read_text()
# Fail loudly if production limits change; test fixtures below use these limits.
for definition in ("XMIT_TRACKER_COUNT = 64", "XMIT_BUFFER_COUNT = XMIT_TRACKER_COUNT", "MaximumPendingXmitCount = 24",
                   "MaximumTitlePendingXmitCount = MaximumPendingXmitCount - 1"):
    assert definition in header, definition

start = source.index("#if USBENET_TX_SCAN_OPTIMIZATION\nstatic BOOL HasQueued")
end = source.index("VOID __fastcall CUsbEnet::AbortUserControlTransfer", start)
schedule = source[start:end]
start = source.index("#if USBENET_TX_SCAN_OPTIMIZATION\n\t// The original counts")
end = source.index("\n\t++ActiveXmitCount;", start)
decision = source[start:end].replace("this", "Device")
# Counts visits without changing decisions; both versions get the same probe.
probe = "for (DWORD Index = 0; Index < XMIT_BUFFER_COUNT; Index++) {"
schedule = schedule.replace(probe, probe + "\n++Visits;")
decision = decision.replace(probe, probe + "\n++Visits;")

prelude = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>
#include <algorithm>
typedef uint32_t DWORD;
typedef bool BOOL;
#define TRUE true
#define FALSE false
const DWORD XMIT_BUFFER_COUNT = 64;
const DWORD MaximumPendingXmitCount = 24;
const DWORD MaximumTitlePendingXmitCount = 23;
const DWORD XMIT_FLAG_WAITING = 0x10000000;
const DWORD XMIT_FLAG_CRC_PADDING = 0x20000000;
const DWORD XMIT_FLAG_BUSY = 0x40000000;
const DWORD XMIT_FLAG_QUEUED = 0x80000000;
const DWORD USBENET_STATE_RESETTING = 1;
const DWORD USBENET_STATE_STOPPING = 2;
struct Packet { BOOL Debug; };
Packet Title = {FALSE}, Debug = {TRUE};
struct XMIT_TRACKER { Packet* FirstPacket; DWORD Flags; };
typedef XMIT_TRACKER* PXMIT_TRACKER;
struct CUsbEnet {
    XMIT_TRACKER XmitTrackers[64];
    DWORD Flags, ActiveXmitCount, PendingXmitCount;
    std::vector<int> Submitted;
};
static BOOL IsDebugXmitTracker(PXMIT_TRACKER t) {
    return t != NULL && t->FirstPacket != NULL && t->FirstPacket->Debug;
}
static void SubmitXmitTrackerLocked(CUsbEnet* d, PXMIT_TRACKER t) {
    assert(t->FirstPacket != NULL);
    assert(!(t->Flags & (XMIT_FLAG_BUSY | XMIT_FLAG_QUEUED | XMIT_FLAG_WAITING)));
    assert(d->PendingXmitCount < (IsDebugXmitTracker(t) ? 24u : 23u));
    t->Flags |= XMIT_FLAG_BUSY;
    ++d->PendingXmitCount;
    d->Submitted.push_back(int(t - d->XmitTrackers));
}
'''

parts = [prelude]
for namespace, enabled in (("original", 0), ("optimized", 1)):
    parts += [f"\n#define USBENET_TX_SCAN_OPTIMIZATION {enabled}\nnamespace {namespace} {{\n",
              "uint64_t Visits = 0;\n", schedule,
              "BOOL Decide(CUsbEnet* Device, BOOL ImmediateLowLatency) {\n"
              "DWORD PendingXmitCount = Device->PendingXmitCount;\n"
              "PXMIT_TRACKER XmitTrackers = Device->XmitTrackers;\n"
              "DWORD ScheduledXmitCount, WaitingXmitCount; BOOL SubmitTracker;\n",
              decision, "\nreturn SubmitTracker;\n}\n}\n#undef USBENET_TX_SCAN_OPTIMIZATION\n"]

parts.append(r'''
uint64_t Cases = 0;
void recount(CUsbEnet& d) {
    d.ActiveXmitCount = d.PendingXmitCount = 0;
    for (const auto& t : d.XmitTrackers) {
        if (t.FirstPacket) ++d.ActiveXmitCount;
        if (t.Flags & XMIT_FLAG_BUSY) { assert(t.FirstPacket); ++d.PendingXmitCount; }
    }
    assert(d.PendingXmitCount <= 24);
}
// Eight coherent states: free; title/debug open, waiting, queued; BUSY.
void state(XMIT_TRACKER& t, unsigned s) {
    t.FirstPacket = s == 0 ? NULL : ((s >= 4 && s <= 6) ? &Debug : &Title);
    t.Flags = (s == 2 || s == 5) ? XMIT_FLAG_WAITING :
              (s == 3 || s == 6) ? XMIT_FLAG_QUEUED : (s == 7 ? XMIT_FLAG_BUSY : 0);
}
void check(const CUsbEnet& input, unsigned start) {
    for (int immediate = 0; immediate != 2; ++immediate) {
        CUsbEnet a = input, b = input;
        original::Visits = optimized::Visits = 0;
        assert(original::Decide(&a, immediate != 0) == optimized::Decide(&b, immediate != 0));
        assert(optimized::Visits <= original::Visits);
    }
    CUsbEnet a = input, b = input;
    original::Visits = optimized::Visits = 0;
    DWORD na = original::ScheduleReadyXmitTrackers(&a, &a.XmitTrackers[start]);
    DWORD nb = optimized::ScheduleReadyXmitTrackers(&b, &b.XmitTrackers[start]);
    assert(na == nb && na == a.Submitted.size());
    assert(a.Submitted == b.Submitted);
    assert(a.PendingXmitCount == b.PendingXmitCount);
    assert(a.ActiveXmitCount == b.ActiveXmitCount);
    assert(optimized::Visits <= original::Visits);
    if (input.Flags) assert(na == 0);
    for (unsigned i = 0; i < 64; ++i) {
        assert(a.XmitTrackers[i].Flags == b.XmitTrackers[i].Flags);
        assert(a.XmitTrackers[i].FirstPacket == b.XmitTrackers[i].FirstPacket);
    }
    ++Cases;
}
int main() {
    // Independent expectations: global class priority beats ring position,
    // debug-open flush waits for pending==0; title cannot consume slot 24.
    CUsbEnet priority = {};
    state(priority.XmitTrackers[0], 1); state(priority.XmitTrackers[1], 2);
    state(priority.XmitTrackers[2], 4); state(priority.XmitTrackers[3], 5);
    recount(priority);
    optimized::ScheduleReadyXmitTrackers(&priority, &priority.XmitTrackers[63]);
    assert((priority.Submitted == std::vector<int>{3,1,0}));
    CUsbEnet idle = {}; state(idle.XmitTrackers[2], 4); state(idle.XmitTrackers[1], 2);
    recount(idle); optimized::ScheduleReadyXmitTrackers(&idle, &idle.XmitTrackers[63]);
    assert((idle.Submitted == std::vector<int>{2,1}));
    CUsbEnet reserved = {};
    for (unsigned i=4;i<27;++i) state(reserved.XmitTrackers[i],7);
    state(reserved.XmitTrackers[0],2); state(reserved.XmitTrackers[1],5);
    recount(reserved); optimized::ScheduleReadyXmitTrackers(&reserved, &reserved.XmitTrackers[63]);
    assert((reserved.Submitted == std::vector<int>{1}));

    const unsigned positions[] = {62,63,0,1};
    const unsigned starts[] = {0,1,31,62,63};
    const unsigned pending[] = {0,1,22,23,24};
    for (unsigned pattern=0;pattern<4096;++pattern) {
        for (unsigned busy : pending) {
            CUsbEnet d = {}; unsigned p = pattern;
            for (unsigned i=0;i<4;++i) { state(d.XmitTrackers[positions[i]],p%8); p/=8; }
            unsigned already = 0;
            for (auto& t : d.XmitTrackers) if (t.Flags & XMIT_FLAG_BUSY) ++already;
            if (already > busy) continue;
            for (unsigned i=2;already<busy;++i,++already) state(d.XmitTrackers[i],7);
            recount(d);
            for (unsigned flags=0;flags<4;++flags) {
                d.Flags = flags;
                for (unsigned start : starts) check(d,start);
            }
        }
    }
    std::mt19937 rng(0x360179);
    for (unsigned trial=0;trial<20000;++trial) {
        CUsbEnet d = {};
        for (auto& t : d.XmitTrackers) {
            unsigned s = rng()%8;
            if (s==7 && d.PendingXmitCount==24) s=0;
            state(t,s); if (s==7) ++d.PendingXmitCount;
            if (rng()&1) t.Flags |= XMIT_FLAG_CRC_PADDING;
        }
        recount(d); d.Flags = trial%19==0 ? 1+(rng()%3) : 0;
        check(d,rng()%64);
    }
    // Model interleaved completion, allocation, and DPC release under NicLock.
    CUsbEnet evolving = {};
    for (unsigned step=0;step<20000;++step) {
        unsigned index = rng()%64;
        auto& t = evolving.XmitTrackers[index];
        if (t.Flags & XMIT_FLAG_BUSY) state(t,0); // successful or cancelled completion
        else if (t.Flags & XMIT_FLAG_QUEUED) t.Flags = XMIT_FLAG_WAITING;
        else if (!t.FirstPacket) state(t,1+(rng()%6));
        recount(evolving); check(evolving,index);
        optimized::ScheduleReadyXmitTrackers(&evolving,&evolving.XmitTrackers[index]);
        evolving.Submitted.clear();
    }
    for (unsigned busy : {0u,1u,22u}) {
        CUsbEnet d = {}; for (unsigned i=0;i<busy;++i) state(d.XmitTrackers[i],7);
        recount(d); original::Visits=optimized::Visits=0;
        original::ScheduleReadyXmitTrackers(&d,&d.XmitTrackers[63]);
        optimized::ScheduleReadyXmitTrackers(&d,&d.XmitTrackers[63]);
        printf("No unsent trackers, pending=%u: visits %llu -> %llu\n",busy,
               (unsigned long long)original::Visits,(unsigned long long)optimized::Visits);
    }
    printf("PASS: %llu scheduling states; submission order, final flags, slot limits, and new-frame decisions match.\n",
           (unsigned long long)Cases);
}
''')

with tempfile.TemporaryDirectory(prefix="usbenet-txscan-") as temp:
    directory = pathlib.Path(temp)
    cpp = directory / "scheduler.cpp"
    cpp.write_text("".join(parts))
    subprocess.run(["cl", "/nologo", "/EHsc", "/O2", "/std:c++14", str(cpp),
                    "/Fe:" + str(directory / "scheduler.exe"),
                    "/Fo:" + str(directory / "scheduler.obj")], check=True, cwd=directory)
    subprocess.run([str(directory / "scheduler.exe")], check=True, cwd=directory)
