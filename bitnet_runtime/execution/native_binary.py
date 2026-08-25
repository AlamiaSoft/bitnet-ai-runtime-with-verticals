from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .hardware import HardwareProfile


@dataclass
class NativeBinaryTier:
    """One tier of native runtime binary with CPU requirements."""
    name: str
    binary_filename: str
    required_flags: List[str]
    performance_rank: int
    description: str = ""


BINARY_TIERS_X86 = [
    NativeBinaryTier(
        name="avx512",
        binary_filename="llama-server-avx512.exe",
        required_flags=["avx512f"],
        performance_rank=3,
        description="AVX-512 optimized (best performance on modern Intel/AMD)",
    ),
    NativeBinaryTier(
        name="avx2",
        binary_filename="llama-server-avx2.exe",
        required_flags=["avx2"],
        performance_rank=2,
        description="AVX2 optimized (good performance on CPUs from 2013+)",
    ),
    NativeBinaryTier(
        name="generic_x64",
        binary_filename="llama-server.exe",
        required_flags=[],
        performance_rank=1,
        description="Generic x64 (compatible but slow - no SIMD acceleration)",
    ),
]

BINARY_TIERS_ARM = [
    NativeBinaryTier(
        name="arm64",
        binary_filename="llama-server-arm64.exe",
        required_flags=["neon"],
        performance_rank=2,
        description="ARM64 with NEON acceleration",
    ),
]


@dataclass
class NativeBinaryAssessment:
    """
    Result of evaluating native binary suitability for this host.

    Key invariant: binary compatibility != suitability.
    A generic x64 build may technically run but deliver poor performance.
    warn_performance=True signals the caller should prefer Docker/remote instead.
    """
    tier: Optional[NativeBinaryTier]
    binary_path: Optional[Path]
    suitability: str           # "excellent" | "good" | "poor" | "incompatible"
    suitability_score: float   # 0.0-1.0
    reason: str
    warn_performance: bool = False
    available_tiers: List[str] = field(default_factory=list)


def select_best_binary(hw: HardwareProfile, bin_dir: Path) -> NativeBinaryAssessment:
    """
    Selects the best native binary tier for this host, considering both:
    - CPU instruction-set compatibility
    - Actual suitability / performance expectation

    Does NOT equate "binary runs" with "best runtime". Generic x64 is flagged
    as poor suitability even if it technically runs.
    """
    tiers = BINARY_TIERS_ARM if hw.cpu_arch == "arm64" else BINARY_TIERS_X86

    def _find_binary(filename: str) -> Optional[Path]:
        p = bin_dir / filename
        if p.exists():
            return p
        no_ext = bin_dir / filename.replace(".exe", "")
        if no_ext.exists():
            return no_ext
        return None

    available_tiers: List[str] = [
        t.name for t in tiers if _find_binary(t.binary_filename)
    ]

    for tier in sorted(tiers, key=lambda t: t.performance_rank, reverse=True):
        if not all(hw.has_flag(f) for f in tier.required_flags):
            continue
        bpath = _find_binary(tier.binary_filename)
        if bpath is None:
            continue

        # Generic x64: compatible but poor performance - warn caller
        if tier.name == "generic_x64":
            return NativeBinaryAssessment(
                tier=tier,
                binary_path=bpath,
                suitability="poor",
                suitability_score=0.3,
                reason=(
                    f"Only generic x64 binary available. CPU has no SIMD flags "
                    f"({hw.simd_flags or 'none'}). Performance will be significantly "
                    f"degraded. Docker or remote inference recommended."
                ),
                warn_performance=True,
                available_tiers=available_tiers,
            )

        score = 1.0 if tier.performance_rank >= 3 else 0.9
        return NativeBinaryAssessment(
            tier=tier,
            binary_path=bpath,
            suitability="excellent",
            suitability_score=score,
            reason=f"{tier.description}. SIMD: {hw.simd_flags}.",
            warn_performance=False,
            available_tiers=available_tiers,
        )

    return NativeBinaryAssessment(
        tier=None,
        binary_path=None,
        suitability="incompatible",
        suitability_score=0.0,
        reason=(
            f"No compatible native binary found in {bin_dir}. "
            f"CPU: {hw.cpu_arch}, SIMD: {hw.simd_flags}. "
            f"Tiers on disk: {available_tiers or 'none'}."
        ),
        warn_performance=False,
        available_tiers=available_tiers,
    )
