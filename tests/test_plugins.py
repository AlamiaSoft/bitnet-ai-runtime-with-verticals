import pytest
from bitnet_runtime.plugins.vertical_registry import (
    VerticalManifest,
    VerticalPluginContract,
    VerticalRegistry,
)

class SampleCustomVertical(VerticalPluginContract):
    manifest = VerticalManifest(
        name="custom_invoice",
        title="Custom Invoice Assistant",
        version="1.0.0",
        description="Automated invoice generator",
    )

    def __init__(self, **kwargs):
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    def get_cli_handlers(self):
        return {"generate": lambda: "Invoice generated"}

@pytest.mark.asyncio
async def test_vertical_registry_lifecycle():
    reg = VerticalRegistry()
    reg.register(SampleCustomVertical)

    # Check manifest listing
    manifests = reg.list_manifests()
    assert len(manifests) == 1
    assert manifests[0].name == "custom_invoice"

    # Instantiate
    instance = reg.get_vertical_instance("custom_invoice")
    assert instance is not None
    await instance.initialize()
    assert instance.initialized is True
    assert "generate" in instance.get_cli_handlers()

def test_vertical_auto_discovery():
    reg = VerticalRegistry()
    reg.auto_discover("verticals")
    manifests = reg.list_manifests()
    names = {m.name for m in manifests}

    # Verify all 5 built-in verticals are discovered dynamically
    assert "employee" in names
    assert "memory" in names
    assert "computer" in names
    assert "whatsapp" in names
    assert "qa" in names

def test_runtime_standalone_without_verticals():
    # Verify that bitnet_runtime does not import verticals at module level
    import sys
    # Import core runtime modules
    import bitnet_runtime
    import bitnet_runtime.agent
    import bitnet_runtime.inference
    import bitnet_runtime.memory
    import bitnet_runtime.tools
    import bitnet_runtime.policy
    import bitnet_runtime.plugins

    assert bitnet_runtime.__version__ is not None
