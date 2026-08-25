"""
Tests for hardware detection, binary tier selection, and runtime preference.
Covers CPU-agnostic native binary selection and preference-aware resolver behaviour.
"""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from bitnet_runtime.execution.hardware import HardwareProfile, detect_hardware
from bitnet_runtime.execution.native_binary import (
    NativeBinaryTier,
    select_best_binary,
    BINARY_TIERS_X86,
)
from bitnet_runtime.execution.runtime_preference import (
    RuntimePreference,
    RuntimePreferenceStore,
)
from bitnet_runtime.execution.runtime_resolver import ExecutionRuntimeResolver
from bitnet_runtime.router.models import PrivacyRequirement


# ---------------------------------------------------------------------------
# HardwareProfile helpers
# ---------------------------------------------------------------------------

def _make_hw(simd_flags=None, cpu_arch="x86_64", cpu_cores=4,
             total_ram_mb=8192, available_ram_mb=6000, free_disk_mb=50000):
    return HardwareProfile(
        cpu_arch=cpu_arch,
        cpu_cores=cpu_cores,
        total_ram_mb=total_ram_mb,
        available_ram_mb=available_ram_mb,
        simd_flags=simd_flags or [],
        has_gpu=False,
        gpu_vram_mb=0,
        free_disk_mb=free_disk_mb,
    )


# ---------------------------------------------------------------------------
# detect_hardware
# ---------------------------------------------------------------------------

def test_detect_hardware_returns_profile():
    hw = detect_hardware()
    assert isinstance(hw, HardwareProfile)
    assert hw.cpu_arch in ("x86_64", "arm64", "x86", "amd64")
    assert hw.cpu_cores >= 1
    assert hw.total_ram_mb > 0
    assert hw.available_ram_mb > 0


def test_hardware_profile_has_flag():
    hw = _make_hw(simd_flags=["avx2", "sse4_2"])
    assert hw.has_flag("avx2")
    assert hw.has_flag("AVX2")   # case-insensitive
    assert not hw.has_flag("avx512f")


def test_hardware_profile_ram_sufficient():
    hw = _make_hw(available_ram_mb=2000)
    # 1200 MB model with 20% headroom = 1440 MB required
    assert hw.ram_sufficient_for_mb(1200)
    # 3800 MB model with 20% headroom = 4560 MB required
    assert not hw.ram_sufficient_for_mb(3800)


# ---------------------------------------------------------------------------
# select_best_binary - AVX2 path (file exists)
# ---------------------------------------------------------------------------

def test_select_best_binary_avx2(tmp_path):
    """Machine with AVX2 + avx2 binary on disk -> excellent suitability."""
    (tmp_path / "llama-server-avx2.exe").touch()
    hw = _make_hw(simd_flags=["avx2", "sse4_2"])
    result = select_best_binary(hw, tmp_path)
    assert result.tier is not None
    assert result.tier.name == "avx2"
    assert result.suitability == "excellent"
    assert result.suitability_score >= 0.9
    assert not result.warn_performance


def test_select_best_binary_avx512_preferred(tmp_path):
    """AVX-512 binary selected over AVX2 when both exist and CPU supports it."""
    (tmp_path / "llama-server-avx512.exe").touch()
    (tmp_path / "llama-server-avx2.exe").touch()
    hw = _make_hw(simd_flags=["avx512f", "avx2"])
    result = select_best_binary(hw, tmp_path)
    assert result.tier.name == "avx512"
    assert result.suitability_score == 1.0


def test_select_best_binary_avx2_fallback_when_no_avx512_binary(tmp_path):
    """AVX2 selected when CPU has AVX-512 but only AVX2 binary exists."""
    (tmp_path / "llama-server-avx2.exe").touch()
    hw = _make_hw(simd_flags=["avx512f", "avx2"])
    result = select_best_binary(hw, tmp_path)
    assert result.tier.name == "avx2"
    assert result.suitability == "excellent"


# ---------------------------------------------------------------------------
# select_best_binary - generic x64 (no SIMD) -> poor suitability
# ---------------------------------------------------------------------------

def test_select_best_binary_generic_is_poor(tmp_path):
    """Generic x64 binary with no SIMD flags -> poor suitability + warn_performance=True."""
    (tmp_path / "llama-server.exe").touch()
    hw = _make_hw(simd_flags=[])  # No SIMD at all
    result = select_best_binary(hw, tmp_path)
    assert result.tier is not None
    assert result.tier.name == "generic_x64"
    assert result.suitability == "poor"
    assert result.suitability_score < 0.5
    assert result.warn_performance is True


# ---------------------------------------------------------------------------
# select_best_binary - no binary on disk -> incompatible
# ---------------------------------------------------------------------------

def test_select_best_binary_no_binary(tmp_path):
    """No binary on disk -> incompatible assessment."""
    hw = _make_hw(simd_flags=["avx2"])
    result = select_best_binary(hw, tmp_path)
    assert result.tier is None
    assert result.suitability == "incompatible"
    assert result.suitability_score == 0.0
    assert not result.warn_performance


# ---------------------------------------------------------------------------
# select_best_binary - AVX2 CPU but no AVX2 binary, only generic
# ---------------------------------------------------------------------------

def test_select_best_binary_avx2_cpu_generic_only(tmp_path):
    """AVX2 CPU but only generic binary on disk -> poor suitability (not incompatible)."""
    (tmp_path / "llama-server.exe").touch()
    hw = _make_hw(simd_flags=["avx2"])
    result = select_best_binary(hw, tmp_path)
    # avx2 binary doesn't exist, generic does; generic returns poor
    assert result.tier.name == "generic_x64"
    assert result.suitability == "poor"
    assert result.warn_performance is True


# ---------------------------------------------------------------------------
# RuntimePreferenceStore - load / save round-trip
# ---------------------------------------------------------------------------

def test_preference_store_default():
    store = RuntimePreferenceStore()
    assert store.preference == RuntimePreference.AUTO


def test_preference_store_save_load(tmp_path):
    path = tmp_path / "prefs.json"
    store = RuntimePreferenceStore(preference=RuntimePreference.NATIVE, dismissed_recommendation=True)
    store.save(path)
    loaded = RuntimePreferenceStore.load(path)
    assert loaded.preference == RuntimePreference.NATIVE
    assert loaded.dismissed_recommendation is True


def test_preference_store_load_missing_file(tmp_path):
    path = tmp_path / "nonexistent.json"
    store = RuntimePreferenceStore.load(path)
    assert store.preference == RuntimePreference.AUTO


def test_preference_store_load_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("not json!", encoding="utf-8")
    store = RuntimePreferenceStore.load(path)
    assert store.preference == RuntimePreference.AUTO


# ---------------------------------------------------------------------------
# ExecutionRuntimeResolver - NATIVE preference, native offline -> no silent fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolver_native_preference_native_offline(tmp_path):
    """
    When preference=NATIVE and native runtime is offline,
    the resolver must return an offline placement and NOT silently use Docker or remote.
    """
    from bitnet_runtime.model_garden.models import ModelFamily, ModelManifest, ModelTier
    from bitnet_runtime.router.models import PrivacyRequirement

    manifest = ModelManifest(
        model_id="bitnet_b1_58_2b",
        name="BitNet 2B",
        family=ModelFamily.BITNET,
        tier=ModelTier.LOCAL_1BIT,
        provider="bitnet",
        context_window=4096,
        ram_required_mb=1200,
    )

    # Put an avx2 binary on disk so suitability = excellent
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "llama-server-avx2.exe").touch()

    # Create resolver pointing at bin_dir
    resolver = ExecutionRuntimeResolver(
        native_bitnet_endpoints=["http://127.0.0.1:19999"],  # port that won't respond
        container_bitnet_endpoints=["http://127.0.0.1:19998"],
        bin_dir=bin_dir,
    )

    # Override preference to NATIVE
    pref_store = RuntimePreferenceStore(preference=RuntimePreference.NATIVE)

    with patch("bitnet_runtime.execution.runtime_resolver.get_preference_store", return_value=pref_store), \
         patch("bitnet_runtime.execution.hardware.detect_hardware", return_value=_make_hw(simd_flags=["avx2"])):
        placement = await resolver.resolve_execution(manifest, privacy=PrivacyRequirement.CLOUD_ALLOWED)

    # Must stay native, must NOT switch to container or remote
    assert placement.runtime_type.value == "native_cpu"
    assert "unavailable" in placement.reason or "preference" in placement.reason
    assert "Docker" in placement.why or "Auto" in placement.why


# ---------------------------------------------------------------------------
# ExecutionRuntimeResolver - DOCKER preference skips native probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolver_docker_preference_skips_native(tmp_path):
    """When preference=DOCKER, resolver must skip native probe entirely."""
    from bitnet_runtime.model_garden.models import ModelFamily, ModelManifest, ModelTier

    manifest = ModelManifest(
        model_id="bitnet_b1_58_2b",
        name="BitNet 2B",
        family=ModelFamily.BITNET,
        tier=ModelTier.LOCAL_1BIT,
        provider="bitnet",
        context_window=4096,
        ram_required_mb=1200,
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "llama-server-avx2.exe").touch()

    resolver = ExecutionRuntimeResolver(
        native_bitnet_endpoints=["http://127.0.0.1:19999"],
        container_bitnet_endpoints=["http://127.0.0.1:19997"],
        bin_dir=bin_dir,
    )

    pref_store = RuntimePreferenceStore(preference=RuntimePreference.DOCKER)

    with patch("bitnet_runtime.execution.runtime_resolver.get_preference_store", return_value=pref_store), \
         patch("bitnet_runtime.execution.hardware.detect_hardware", return_value=_make_hw(simd_flags=["avx2"])):
        placement = await resolver.resolve_execution(manifest)

    # Must be container-type (even if offline) and NOT native
    assert placement.runtime_type.value in ("container",)
    assert "docker" in placement.reason.lower() or "container" in placement.reason.lower()


# ---------------------------------------------------------------------------
# ExecutionRuntimeResolver - AUTO with poor suitability prefers Docker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolver_auto_poor_suitability_uses_docker(tmp_path, monkeypatch):
    """
    AUTO preference + poor native suitability (generic x64 only) ->
    resolver should skip native and use Docker container.
    """
    from bitnet_runtime.model_garden.models import ModelFamily, ModelManifest, ModelTier

    manifest = ModelManifest(
        model_id="bitnet_b1_58_2b",
        name="BitNet 2B",
        family=ModelFamily.BITNET,
        tier=ModelTier.LOCAL_1BIT,
        provider="bitnet",
        context_window=4096,
        ram_required_mb=1200,
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "llama-server.exe").touch()  # Only generic - poor suitability

    pref_store = RuntimePreferenceStore(preference=RuntimePreference.AUTO)

    # Patch container endpoint to respond OK
    async def mock_probe_first_working(self, endpoints, timeout=2.0):
        if any("19996" in ep for ep in endpoints):
            return "http://127.0.0.1:19996"
        return None

    resolver = ExecutionRuntimeResolver(
        native_bitnet_endpoints=["http://127.0.0.1:19999"],
        container_bitnet_endpoints=["http://127.0.0.1:19996"],
        bin_dir=bin_dir,
    )

    with patch("bitnet_runtime.execution.runtime_resolver.get_preference_store", return_value=pref_store), \
         patch("bitnet_runtime.execution.hardware.detect_hardware", return_value=_make_hw(simd_flags=[])), \
         patch.object(resolver, "_probe_first_working", side_effect=mock_probe_first_working.__get__(resolver)):
        placement = await resolver.resolve_execution(manifest)

    # Should have skipped native (poor suitability) and gone to container
    assert placement.runtime_type.value == "container"
