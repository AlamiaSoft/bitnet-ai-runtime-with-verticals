from __future__ import annotations
import enum
import os
import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from ..logging import logger
from .models import HardwareRequirements, ModelManifest

class CompatibilityStatus(str, enum.Enum):
    COMPATIBLE = "compatible"
    RAM_CONSTRAINED = "ram_constrained"
    INCOMPATIBLE_ARCH = "incompatible_arch"
    REQUIRES_GPU = "requires_gpu"

@dataclass
class HardwareCompatibility:
    status: CompatibilityStatus
    is_runnable: bool
    reason: str
    ram_usage_percent: float
    recommended_threads: int

@dataclass
class HostHardwareProfile:
    platform: str
    architecture: str
    cpu_model: str
    logical_cores: int
    physical_cores: int
    total_ram_mb: int
    available_ram_mb: int
    has_gpu: bool = False
    supported_extensions: List[str] = field(default_factory=list)

class HardwareDiscoveryEngine:
    """
    Inspects host CPU, RAM, and hardware acceleration capabilities,
    and evaluates model compatibility constraints.
    """

    def __init__(self, override_profile: Optional[HostHardwareProfile] = None):
        self._profile = override_profile or self._detect_host_hardware()

    def get_profile(self) -> HostHardwareProfile:
        return self._profile

    def evaluate_compatibility(self, manifest: ModelManifest) -> HardwareCompatibility:
        req = manifest.hardware
        host = self._profile

        # 1. Cloud models require zero local hardware
        if manifest.provider_backend == "cloud":
            return HardwareCompatibility(
                status=CompatibilityStatus.COMPATIBLE,
                is_runnable=True,
                reason="Cloud API endpoint - zero local hardware load",
                ram_usage_percent=0.0,
                recommended_threads=host.logical_cores,
            )

        # 2. Architecture check
        arch_norm = "x86_64" if host.architecture in ("x86_64", "AMD64", "x64") else host.architecture.lower()
        allowed_archs = [a.lower() for a in req.cpu_archs]
        if arch_norm not in allowed_archs and "x86_64" not in allowed_archs:
            return HardwareCompatibility(
                status=CompatibilityStatus.INCOMPATIBLE_ARCH,
                is_runnable=False,
                reason=f"Model requires {req.cpu_archs}, but host is {host.architecture}",
                ram_usage_percent=0.0,
                recommended_threads=host.logical_cores,
            )

        # 3. GPU requirement check
        if req.requires_gpu and not host.has_gpu:
            return HardwareCompatibility(
                status=CompatibilityStatus.REQUIRES_GPU,
                is_runnable=False,
                reason="Model requires dedicated GPU acceleration",
                ram_usage_percent=0.0,
                recommended_threads=host.logical_cores,
            )

        # 4. RAM capacity check
        ram_percent = (req.min_ram_mb / max(host.total_ram_mb, 1)) * 100.0
        if req.min_ram_mb > host.available_ram_mb:
            return HardwareCompatibility(
                status=CompatibilityStatus.RAM_CONSTRAINED,
                is_runnable=True,  # Might run with pagefile/swap, but high latency warning
                reason=f"Requires {req.min_ram_mb}MB RAM (only {host.available_ram_mb}MB currently free)",
                ram_usage_percent=round(ram_percent, 1),
                recommended_threads=min(req.recommended_threads, host.logical_cores),
            )

        return HardwareCompatibility(
            status=CompatibilityStatus.COMPATIBLE,
            is_runnable=True,
            reason=f"Fully compatible (Uses {req.min_ram_mb}MB of {host.total_ram_mb}MB RAM)",
            ram_usage_percent=round(ram_percent, 1),
            recommended_threads=min(req.recommended_threads, host.logical_cores),
        )

    def _detect_host_hardware(self) -> HostHardwareProfile:
        total_ram = 8192
        avail_ram = 4096

        # Platform-specific memory detection
        try:
            if sys.platform == "win32":
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                total_ram = int(stat.ullTotalPhys / (1024 * 1024))
                avail_ram = int(stat.ullAvailPhys / (1024 * 1024))
            elif hasattr(os, "sysconf"):
                if "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
                    page_size = os.sysconf("SC_PAGE_SIZE")
                    total_pages = os.sysconf("SC_PHYS_PAGES")
                    total_ram = int((page_size * total_pages) / (1024 * 1024))
                    avail_ram = int(total_ram * 0.5)
        except Exception as e:
            logger.debug(f"Could not read exact physical RAM stats: {e}")

        cores = os.cpu_count() or 4
        return HostHardwareProfile(
            platform=platform.system(),
            architecture=platform.machine(),
            cpu_model=platform.processor() or "Generic CPU",
            logical_cores=cores,
            physical_cores=max(cores // 2, 1),
            total_ram_mb=total_ram,
            available_ram_mb=avail_ram,
            has_gpu=False,
            supported_extensions=["AVX2", "FMA", "NEON"] if "arm" in platform.machine().lower() else ["AVX2", "AVX512"],
        )
