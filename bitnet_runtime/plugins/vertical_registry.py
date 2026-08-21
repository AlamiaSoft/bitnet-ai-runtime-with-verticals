from __future__ import annotations
import importlib
import inspect
import os
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from ..logging import logger

@dataclass
class VerticalManifest:
    name: str
    title: str
    version: str = "0.1.0"
    description: str = ""
    author: str = "Community"
    enabled: bool = True
    config_schema: Optional[Dict[str, Any]] = None

class VerticalPluginContract(ABC):
    """Formal plugin contract that every vertical must implement."""

    manifest: VerticalManifest

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vertical instance and resources."""
        pass

    @abstractmethod
    def get_cli_handlers(self) -> Dict[str, Callable]:
        """Return mapping of CLI action names to handler functions."""
        return {}

class VerticalRegistry:
    """
    Dynamic registry for discovering, loading, and managing vertical plugins
    with ZERO static compile-time coupling in core runtime.
    """

    def __init__(self):
        self._plugins: Dict[str, Type[VerticalPluginContract]] = {}
        self._instances: Dict[str, VerticalPluginContract] = {}

    def register(self, plugin_cls: Type[VerticalPluginContract]) -> None:
        manifest = getattr(plugin_cls, "manifest", None)
        if manifest is None:
            name = getattr(plugin_cls, "name", plugin_cls.__name__.lower())
            manifest = VerticalManifest(name=name, title=name.capitalize())
        self._plugins[manifest.name] = plugin_cls
        logger.debug(f"Registered vertical plugin: '{manifest.name}'")

    def get_vertical_class(self, name: str) -> Optional[Type[VerticalPluginContract]]:
        return self._plugins.get(name)

    def get_vertical_instance(self, name: str, **kwargs) -> Optional[VerticalPluginContract]:
        if name in self._instances:
            return self._instances[name]
        plugin_cls = self.get_vertical_class(name)
        if not plugin_cls:
            return None
        instance = plugin_cls(**kwargs)
        self._instances[name] = instance
        return instance

    def list_manifests(self) -> List[VerticalManifest]:
        manifests = []
        for name, cls in self._plugins.items():
            if name == "base" or cls.__name__ == "BaseVertical":
                continue
            m = getattr(cls, "manifest", VerticalManifest(name=name, title=name))
            manifests.append(m)
        return manifests

    def auto_discover(self, package_name: str = "verticals") -> None:
        """Dynamically scans and imports vertical packages at runtime."""
        try:
            pkg = importlib.import_module(package_name)
            pkg_path = getattr(pkg, "__path__", None)
            if not pkg_path:
                return

            for _, subname, ispkg in pkgutil.iter_modules(pkg_path):
                try:
                    sub_module = importlib.import_module(f"{package_name}.{subname}")
                    # Look for classes implementing VerticalPluginContract or BaseVertical
                    for attr_name in dir(sub_module):
                        attr = getattr(sub_module, attr_name)
                        if (
                            inspect.isclass(attr)
                            and issubclass(attr, VerticalPluginContract)
                            and attr is not VerticalPluginContract
                        ):
                            self.register(attr)
                except Exception as e:
                    logger.debug(f"Could not load vertical module {package_name}.{subname}: {e}")
        except ImportError:
            logger.debug(f"Verticals package '{package_name}' not found in current environment.")

registry = VerticalRegistry()
