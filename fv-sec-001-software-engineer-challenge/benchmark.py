"""Run the aggregator CLI and report wall time plus Windows peak working set."""

import ctypes
from ctypes import wintypes
import platform
import sys
from time import perf_counter

import aggregator


def peak_working_set_bytes() -> int | None:
    """Read the current process's OS-reported peak resident memory on Windows."""
    if sys.platform != "win32":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize


def main() -> int:
    print(f"Python: {platform.python_version()} ({platform.architecture()[0]})", flush=True)
    print(f"Platform: {platform.platform()}", flush=True)
    print(f"Command: python benchmark.py {' '.join(sys.argv[1:])}", flush=True)
    start = perf_counter()
    result = aggregator.main()
    print(f"CLI wall time: {perf_counter() - start:.3f} seconds")
    peak = peak_working_set_bytes()
    if peak is None:
        print("Peak working set: not measured (this helper supports Windows only)")
    else:
        print(f"Peak working set: {peak:,} bytes ({peak / 1024 ** 2:.2f} MiB)")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
