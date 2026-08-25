from __future__ import annotations
import os
import sys
import platform
from dataclasses import dataclass, field
from typing import List, Tuple

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass
class HardwareProfile:
    cpu_arch: str
    cpu_cores: int
    total_ram_mb: int
    available_ram_mb: int
    simd_flags: List[str] = field(default_factory=list)
    has_gpu: bool = False
    gpu_vram_mb: int = 0
    free_disk_mb: int = 0

    def has_flag(self, flag: str) -> bool:
        return flag.lower() in [f.lower() for f in self.simd_flags]

    def ram_sufficient_for_mb(self, required_mb: int) -> bool:
        return self.available_ram_mb >= int(required_mb * 1.2)


def _detect_simd_windows() -> List[str]:
    flags: List[str] = []
    try:
        import ctypes
        krnl = ctypes.windll.kernel32
        feature_map = {10: "sse2", 13: "sse3", 36: "ssse3", 37: "sse4_1", 38: "sse4_2", 39: "avx", 40: "avx2", 41: "avx512f"}
        for fid, name in feature_map.items():
            try:
                if krnl.IsProcessorFeaturePresent(fid):
                    flags.append(name)
            except Exception:
                pass
    except Exception:
        pass
    return flags


def _detect_simd_linux() -> List[str]:
    flags: List[str] = []
    try:
        content = open("/proc/cpuinfo", encoding="utf-8").read()
        for flag in ["sse2","sse3","ssse3","sse4_1","sse4_2","avx","avx2","avx512f","neon"]:
            if flag in content:
                flags.append(flag)
    except Exception:
        pass
    return flags


def _detect_simd_macos() -> List[str]:
    flags: List[str] = []
    try:
        import subprocess
        checks = {"avx512f":"hw.optional.avx512f","avx2":"hw.optional.avx2_0","avx":"hw.optional.avx1_0","sse4_2":"hw.optional.sse4_2","sse4_1":"hw.optional.sse4_1","neon":"hw.optional.AdvSIMD"}
        for flag, key in checks.items():
            r = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=1)
            if r.returncode == 0 and r.stdout.strip() == "1":
                flags.append(flag)
    except Exception:
        pass
    return flags


def _detect_ram() -> Tuple[int, int]:
    if _HAS_PSUTIL:
        m = psutil.virtual_memory()
        return int(m.total/1024/1024), int(m.available/1024/1024)
    if os.path.exists("/proc/meminfo"):
        try:
            total = avail = 0
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal:"): total = int(line.split()[1])//1024
                elif line.startswith("MemAvailable:"): avail = int(line.split()[1])//1024
            if total: return total, avail
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
            ms = MS(); ms.dwLength = ctypes.sizeof(ms)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return int(ms.ullTotalPhys/1024/1024), int(ms.ullAvailPhys/1024/1024)
        except Exception:
            pass
    return 4096, 2048


def _detect_free_disk_mb() -> int:
    if _HAS_PSUTIL:
        try: return int(psutil.disk_usage(".").free/1024/1024)
        except Exception: pass
    return 10240


def detect_hardware() -> HardwareProfile:
    """Detects host hardware capabilities for runtime selection."""
    machine = platform.machine().lower()
    if machine in ("amd64","x86_64"): cpu_arch = "x86_64"
    elif machine in ("aarch64","arm64"): cpu_arch = "arm64"
    elif machine in ("i386","i686","x86"): cpu_arch = "x86"
    else: cpu_arch = machine or "x86_64"

    cpu_cores = os.cpu_count() or 1
    total_ram_mb, available_ram_mb = _detect_ram()
    free_disk_mb = _detect_free_disk_mb()

    if os.name == "nt": simd_flags = _detect_simd_windows()
    elif sys.platform == "darwin": simd_flags = _detect_simd_macos()
    else: simd_flags = _detect_simd_linux()

    if cpu_arch == "arm64" and "neon" not in simd_flags:
        simd_flags.append("neon")

    has_gpu = False; gpu_vram_mb = 0
    try:
        import subprocess
        r = subprocess.run(["nvidia-smi","--query-gpu=memory.total","--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            gpu_vram_mb = int(r.stdout.strip().split("\n")[0].strip())
            has_gpu = gpu_vram_mb > 0
    except Exception:
        pass

    return HardwareProfile(cpu_arch=cpu_arch, cpu_cores=cpu_cores, total_ram_mb=total_ram_mb, available_ram_mb=available_ram_mb, simd_flags=simd_flags, has_gpu=has_gpu, gpu_vram_mb=gpu_vram_mb, free_disk_mb=free_disk_mb)
