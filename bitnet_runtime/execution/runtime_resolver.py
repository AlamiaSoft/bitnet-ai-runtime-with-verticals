from __future__ import annotations
import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from ..logging import logger
from ..router.models import ExecutionPlacement, ExecutionTarget, PrivacyRequirement, RuntimeType
from ..model_garden.models import ModelFamily, ModelManifest, ModelTier
from .hardware import HardwareProfile, detect_hardware
from .native_binary import NativeBinaryAssessment, select_best_binary
from .runtime_preference import RuntimePreference, RuntimePreferenceStore, get_preference_store


# Default binary directory for the portable sidecar
_DEFAULT_BIN_DIR = Path(__file__).parent.parent.parent / ".sidecar" / "alamia-bitnet-runtime" / "bin"


class ExecutionRuntimeResolver:
    """
    Stage 2 Execution Provider and Runtime Resolver.

    Resolves what execution runtime should run a given model on this machine,
    considering:
      - Hardware capabilities (CPU arch, SIMD flags, available RAM)
      - Native binary suitability (not just compatibility)
      - User runtime preference (auto | native | docker)
      - Privacy policy requirements

    Runtime priority under AUTO preference:
      1. NATIVE_CPU  - if suitability is excellent/good AND runtime is online
      2. LOCAL_CONTAINER - Docker sidecar (if running)
      3. REMOTE_FALLBACK - Remote VPS/cloud tunnel (if privacy policy allows)

    When the user selects NATIVE or DOCKER explicitly:
      - Honor the preference.
      - If that runtime becomes unavailable, report clearly and return offline placement.
      - Do NOT silently fallback to another runtime.
    """

    def __init__(
        self,
        native_bitnet_endpoints: Optional[List[str]] = None,
        container_bitnet_endpoints: Optional[List[str]] = None,
        remote_bitnet_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bin_dir: Optional[Path] = None,
    ):
        self.native_bitnet_endpoints = native_bitnet_endpoints or [
            "http://127.0.0.1:8080",
            "http://localhost:8080",
        ]
        self.container_bitnet_endpoints = container_bitnet_endpoints or [
            "http://bitnet-runtime:11434",
            "http://bitnet-server:11434",
            "http://bitnet-server:8080",
            "http://172.17.0.1:8080",
            "http://172.18.0.1:8080",
            "http://172.30.0.1:8080",
            "http://host.docker.internal:8080",
        ]
        self.remote_bitnet_url = (
            remote_bitnet_url
            or os.getenv("BITNET_SERVER_URL", "https://ai.alamiaconnect.com/v1")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("BITNET_API_KEY", "51129693340")
        self._cached_placement: Dict[str, ExecutionPlacement] = {}
        self._probe_ttl_seconds: float = 20.0
        self._bin_dir: Path = bin_dir or _DEFAULT_BIN_DIR

        # Cached hardware assessment (populated on first resolve)
        self.hardware_profile: Optional[HardwareProfile] = None
        self.binary_assessment: Optional[NativeBinaryAssessment] = None

    def _assess_hardware(self) -> tuple[HardwareProfile, NativeBinaryAssessment]:
        """Run (or return cached) hardware detection and binary selection."""
        if self.hardware_profile is None or self.binary_assessment is None:
            hw = detect_hardware()
            assessment = select_best_binary(hw, self._bin_dir)
            self.hardware_profile = hw
            self.binary_assessment = assessment
        return self.hardware_profile, self.binary_assessment

    async def resolve_execution(
        self,
        manifest: ModelManifest,
        privacy: PrivacyRequirement = PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
        force_refresh: bool = False,
    ) -> ExecutionPlacement:
        """Capability-driven, preference-aware runtime selection."""
        if force_refresh:
            self.hardware_profile = None
            self.binary_assessment = None

        model_id = manifest.model_id
        is_bitnet = (
            manifest.family == ModelFamily.BITNET
            or manifest.tier == ModelTier.LOCAL_1BIT
            or "bitnet" in model_id
        )

        if is_bitnet:
            return await self._resolve_bitnet(manifest, privacy)

        # Dense GGUF models: in-process llama.cpp
        return ExecutionPlacement(
            runtime_type=RuntimeType.NATIVE_CPU,
            target=ExecutionTarget.LOCAL_CPU_INPROCESS,
            reason="in_process_gguf_execution",
            endpoint_url="in-process://llama_cpp",
            endpoint_label="Native In-Process GGUF (CPU)",
            fallback_chain=["bitnet_native_fallback", "remote_fallback"],
            why=f"Model '{manifest.name}' -> In-process GGUF engine -> Zero Docker, 100% on-device CPU/RAM execution",
        )

    async def _resolve_bitnet(
        self, manifest: ModelManifest, privacy: PrivacyRequirement
    ) -> ExecutionPlacement:
        """Preference-aware BitNet runtime resolution."""
        hw, assessment = self._assess_hardware()
        pref_store = get_preference_store()
        preference = pref_store.preference

        native_suitable = assessment.suitability in ("excellent", "good")

        if preference == RuntimePreference.NATIVE:
            return await self._resolve_native_strict(manifest, hw, assessment, native_suitable)

        if preference == RuntimePreference.DOCKER:
            return await self._resolve_docker_strict(manifest)

        # AUTO: capability-first, suitability-aware
        return await self._resolve_auto(manifest, hw, assessment, native_suitable, privacy)

    async def _resolve_native_strict(
        self,
        manifest: ModelManifest,
        hw: HardwareProfile,
        assessment: NativeBinaryAssessment,
        native_suitable: bool,
    ) -> ExecutionPlacement:
        """NATIVE preference: attempt native only. Do NOT silently fallback."""
        if native_suitable:
            working = await self._probe_first_working(self.native_bitnet_endpoints, timeout=1.5)
            if working:
                return ExecutionPlacement(
                    runtime_type=RuntimeType.NATIVE_CPU,
                    target=ExecutionTarget.LOCAL_CPU_NATIVE,
                    reason="native_portable_bitnet_online",
                    endpoint_url=working,
                    endpoint_label=f"Native BitNet CPU ({assessment.tier.name if assessment.tier else 'native'})",
                    fallback_chain=[],
                    why=(
                        f"Model '{manifest.name}' -> Native BitNet runtime on {working} "
                        f"[{assessment.tier.description if assessment.tier else ''}] "
                        f"-> User preference: native"
                    ),
                )

        # Native unavailable or unsuitable - report clearly, do NOT silently fallback
        suitability_note = (
            f"Native binary suitability: {assessment.suitability} ({assessment.reason})"
            if assessment.suitability != "incompatible"
            else assessment.reason
        )
        return ExecutionPlacement(
            runtime_type=RuntimeType.NATIVE_CPU,
            target=ExecutionTarget.LOCAL_CPU_NATIVE,
            reason="native_runtime_unavailable_preference_honored",
            endpoint_url="http://127.0.0.1:8080",
            endpoint_label="BitNet Native (Offline)",
            fallback_chain=[],
            why=(
                f"Model '{manifest.name}' -> Native runtime unavailable or unsuitable. "
                f"{suitability_note}. "
                f"Action required: switch to Docker or enable Auto in runtime settings."
            ),
        )

    async def _resolve_docker_strict(self, manifest: ModelManifest) -> ExecutionPlacement:
        """DOCKER preference: attempt container only. Do NOT silently fallback."""
        working = await self._probe_first_working(self.container_bitnet_endpoints, timeout=2.0)
        if working:
            port = working.split(":")[-1].split("/")[0]
            return ExecutionPlacement(
                runtime_type=RuntimeType.CONTAINER,
                target=ExecutionTarget.LOCAL_CPU_CONTAINER,
                reason="local_container_sidecar_online",
                endpoint_url=working,
                endpoint_label=f"BitNet Container ({port})",
                fallback_chain=[],
                why=f"Model '{manifest.name}' -> Docker sidecar on {working} -> User preference: docker",
            )

        return ExecutionPlacement(
            runtime_type=RuntimeType.CONTAINER,
            target=ExecutionTarget.LOCAL_CPU_CONTAINER,
            reason="docker_runtime_unavailable_preference_honored",
            endpoint_url="",
            endpoint_label="BitNet Docker (Offline)",
            fallback_chain=[],
            why=(
                f"Model '{manifest.name}' -> Docker runtime unavailable. "
                f"Action required: start Docker and the BitNet container, or switch to Native/Auto."
            ),
        )

    async def _resolve_auto(
        self,
        manifest: ModelManifest,
        hw: HardwareProfile,
        assessment: NativeBinaryAssessment,
        native_suitable: bool,
        privacy: PrivacyRequirement,
    ) -> ExecutionPlacement:
        """AUTO preference: capability-first, suitability-aware selection."""
        # Priority 1: Native - only if suitability is good/excellent
        if native_suitable:
            working = await self._probe_first_working(self.native_bitnet_endpoints, timeout=1.5)
            if working:
                tier_name = assessment.tier.name if assessment.tier else "native"
                return ExecutionPlacement(
                    runtime_type=RuntimeType.NATIVE_CPU,
                    target=ExecutionTarget.LOCAL_CPU_NATIVE,
                    reason="native_portable_bitnet_online",
                    endpoint_url=working,
                    endpoint_label=f"Native BitNet CPU ({tier_name})",
                    fallback_chain=["container", "remote_fallback"],
                    why=(
                        f"Model '{manifest.name}' -> Native BitNet runtime on {working} "
                        f"[{assessment.tier.description if assessment.tier else ''}] "
                        f"-> Suitability: {assessment.suitability}"
                    ),
                )
        else:
            # Log why native was skipped
            logger.info(
                "AUTO: Skipping native runtime for '%s'. %s",
                manifest.model_id, assessment.reason
            )

        # Priority 2: Container (Docker sidecar)
        working_container = await self._probe_first_working(self.container_bitnet_endpoints, timeout=2.0)
        if working_container:
            port = working_container.split(":")[-1].split("/")[0]
            return ExecutionPlacement(
                runtime_type=RuntimeType.CONTAINER,
                target=ExecutionTarget.LOCAL_CPU_CONTAINER,
                reason="local_container_sidecar_online",
                endpoint_url=working_container,
                endpoint_label=f"BitNet Container ({port})",
                fallback_chain=["remote_fallback"],
                why=f"Model '{manifest.name}' -> Local Docker sidecar on {working_container}",
            )

        # Priority 3: Remote fallback (if privacy policy allows)
        if privacy != PrivacyRequirement.AIRGAPPED_LOCAL_ONLY:
            remote_ok = await self._probe_endpoint(self.remote_bitnet_url)
            if remote_ok:
                domain = self.remote_bitnet_url.replace("https://", "").replace("http://", "").split("/")[0]
                return ExecutionPlacement(
                    runtime_type=RuntimeType.REMOTE_FALLBACK,
                    target=ExecutionTarget.REMOTE_VPS_FALLBACK,
                    reason="local_runtime_offline_using_remote_fallback",
                    endpoint_url=self.remote_bitnet_url,
                    endpoint_label=f"BitNet Remote VPS ({domain})",
                    fallback_chain=[],
                    why=f"Model '{manifest.name}' -> Local runtimes offline -> Remote VPS fallback ({domain})",
                )

        # Offline / airgap
        return ExecutionPlacement(
            runtime_type=RuntimeType.NATIVE_CPU,
            target=ExecutionTarget.LOCAL_CPU_NATIVE,
            reason="all_runtimes_unreachable_airgap_enforced",
            endpoint_url="http://127.0.0.1:8080",
            endpoint_label="BitNet Native (Offline)",
            fallback_chain=[],
            why=(
                f"Model '{manifest.name}' -> All runtimes unreachable. "
                f"Native suitability: {assessment.suitability}. "
                f"{'Airgap policy prevents remote.' if privacy == PrivacyRequirement.AIRGAPPED_LOCAL_ONLY else 'Remote unreachable.'}"
            ),
        )

    async def _probe_first_working(self, endpoints: List[str], timeout: float = 2.0) -> Optional[str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=timeout, headers=headers, verify=False) as client:
            for base in endpoints:
                for path in ["/health", "/v1/models", "/models"]:
                    try:
                        res = await client.get(f"{base}{path}")
                        if res.status_code == 200:
                            return base
                    except Exception:
                        continue
        return None

    async def _probe_endpoint(self, url: str) -> bool:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        clean_base = url.replace("/v1", "").rstrip("/")
        async with httpx.AsyncClient(timeout=3.0, headers=headers, verify=False) as client:
            for path in ["/health", "/v1/models", "/models"]:
                try:
                    res = await client.get(f"{clean_base}{path}")
                    if res.status_code == 200:
                        return True
                except Exception:
                    continue
        return False


# Global singleton runtime resolver
global_runtime_resolver = ExecutionRuntimeResolver()
