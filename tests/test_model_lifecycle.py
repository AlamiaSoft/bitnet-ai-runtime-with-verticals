import pytest
from pathlib import Path
from bitnet_runtime.model_garden import (
    CompatibilityStatus,
    HardwareDiscoveryEngine,
    HostHardwareProfile,
    ModelGarden,
    ModelLifecycleManager,
    ModelStatus,
)

def test_hardware_compatibility_detection():
    mock_host = HostHardwareProfile(
        platform="Windows",
        architecture="AMD64",
        cpu_model="Mock CPU",
        logical_cores=8,
        physical_cores=4,
        total_ram_mb=8192,
        available_ram_mb=3000,
        has_gpu=False,
    )
    engine = HardwareDiscoveryEngine(override_profile=mock_host)
    garden = ModelGarden()

    # 1. BitNet 2B requires 1.2GB RAM -> Compatible
    bitnet = garden.get("bitnet_b1_58_2b")
    assert bitnet is not None
    compat_bitnet = engine.evaluate_compatibility(bitnet)
    assert compat_bitnet.status == CompatibilityStatus.COMPATIBLE
    assert compat_bitnet.is_runnable is True

    # 2. Model requiring 5000MB RAM -> RAM Constrained
    heavy_manifest = garden.get("phi3.5_mini_3.8b")
    assert heavy_manifest is not None
    # Temporarily set high RAM requirement
    heavy_manifest.hardware.min_ram_mb = 5000
    compat_heavy = engine.evaluate_compatibility(heavy_manifest)
    assert compat_heavy.status == CompatibilityStatus.RAM_CONSTRAINED

@pytest.mark.asyncio
async def test_model_lifecycle_install_uninstall(tmp_path):
    garden = ModelGarden()
    manager = ModelLifecycleManager(garden=garden, storage_dir=tmp_path)

    model_id = "bitnet_b1_58_2b"

    # 1. Initially available
    assert manager.get_status(model_id) == ModelStatus.AVAILABLE

    # 2. Trigger installation
    success = await manager.install_model(model_id)
    assert success is True
    assert manager.get_status(model_id) == ModelStatus.INSTALLED
    assert manager.get_model_file_path(model_id).exists()

    # 3. Check storage stats
    stats = manager.get_storage_stats()
    assert stats.installed_models_count >= 1

    # 4. Uninstall
    uninstalled = manager.uninstall_model(model_id)
    assert uninstalled is True
    assert manager.get_status(model_id) == ModelStatus.AVAILABLE
    assert not manager.get_model_file_path(model_id).exists()
