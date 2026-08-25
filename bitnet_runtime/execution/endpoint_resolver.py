from __future__ import annotations
import asyncio
import os
import time
from typing import Any, Dict, List, Optional
import httpx

from ..logging import logger
from ..router.models import ExecutionPlacement, ExecutionTarget, PrivacyRequirement
from ..model_garden.models import ModelFamily, ModelManifest, ModelTier

class EndpointResolver:
    """
    Stage 2 Execution Router and Endpoint Resolver.
    Determines WHERE and HOW a selected model executes based on:
    1. Local container / sidecar availability (BitNet 2B)
    2. Local in-process GGUF file presence (llama.cpp)
    3. Remote VPS / Cloud fallback availability (Cloudflare Tunnel / Cloud API)
    4. Strict Privacy and Policy constraints
    """

    def __init__(
        self,
        local_bitnet_endpoints: Optional[List[str]] = None,
        remote_bitnet_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.local_bitnet_endpoints = local_bitnet_endpoints or [
            "http://bitnet-runtime:11434",
            "http://bitnet-server:11434",
            "http://127.0.0.1:8080",
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
        self._cached_active_endpoint: Optional[str] = None
        self._last_probe_time: float = 0.0
        self._probe_ttl_seconds: float = 30.0

    async def resolve_execution(
        self,
        manifest: ModelManifest,
        privacy: PrivacyRequirement = PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
        force_refresh: bool = False,
    ) -> ExecutionPlacement:
        """
        Determines the physical execution target for a given model.
        """
        model_id = manifest.model_id
        is_bitnet = (manifest.family == ModelFamily.BITNET or manifest.tier == ModelTier.LOCAL_1BIT or "bitnet" in model_id)

        # 1. BitNet Execution Resolution
        if is_bitnet:
            # A. Check Local CPU Container / Portable Sidecar
            working_local_ep = await self._probe_local_bitnet(force_refresh=force_refresh)
            if working_local_ep:
                port = working_local_ep.split(":")[-1].split("/")[0]
                return ExecutionPlacement(
                    target=ExecutionTarget.LOCAL_CPU_CONTAINER,
                    reason="local_sidecar_endpoint_online",
                    endpoint_url=working_local_ep,
                    endpoint_label=f"BitNet Sidecar (Local Container {port})",
                    fallback_chain=["remote_vps_fallback" if privacy != PrivacyRequirement.AIRGAPPED_LOCAL_ONLY else "none"],
                    why=f"Model '{manifest.name}' -> Local CPU container active on {working_local_ep} -> Zero cloud dependency",
                )

            # B. If local is offline, check if remote fallback is permissible by privacy policy
            if privacy != PrivacyRequirement.AIRGAPPED_LOCAL_ONLY:
                remote_working = await self._probe_endpoint(self.remote_bitnet_url)
                if remote_working:
                    domain = self.remote_bitnet_url.replace("https://", "").replace("http://", "").split("/")[0]
                    return ExecutionPlacement(
                        target=ExecutionTarget.REMOTE_VPS_FALLBACK,
                        reason="local_container_offline_using_remote_vps",
                        endpoint_url=self.remote_bitnet_url,
                        endpoint_label=f"BitNet Sidecar (Remote VPS {domain})",
                        fallback_chain=[],
                        why=f"Model '{manifest.name}' -> Local sidecar offline -> Remote VPS fallback engaged ({domain})",
                    )

            # If air-gapped or remote also unavailable
            return ExecutionPlacement(
                target=ExecutionTarget.LOCAL_CPU_CONTAINER,
                reason="local_sidecar_offline_unreachable",
                endpoint_url="http://bitnet-runtime:11434",
                endpoint_label="BitNet Sidecar (Offline)",
                fallback_chain=[],
                why=f"Model '{manifest.name}' -> Local CPU sidecar is unreachable and privacy prevents remote failover",
            )

        # 2. Local Dense GGUF In-Process (llama.cpp)
        return ExecutionPlacement(
            target=ExecutionTarget.LOCAL_CPU_INPROCESS,
            reason="in_process_gguf_execution",
            endpoint_url="in-process://llama_cpp",
            endpoint_label="Local In-Process GGUF (CPU)",
            fallback_chain=["bitnet_sidecar_fallback"],
            why=f"Model '{manifest.name}' -> In-process GGUF CPU engine -> Air-gapped on-device execution",
        )

    async def _probe_local_bitnet(self, force_refresh: bool = False) -> Optional[str]:
        now = time.time()
        if (
            not force_refresh
            and self._cached_active_endpoint
            and (now - self._last_probe_time) < self._probe_ttl_seconds
        ):
            return self._cached_active_endpoint

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=2.0, headers=headers, verify=False) as client:
            for base in self.local_bitnet_endpoints:
                for path in ["/health", "/v1/models", "/models"]:
                    ep = f"{base}{path}"
                    try:
                        res = await client.get(ep)
                        if res.status_code == 200:
                            working_base = base
                            self._cached_active_endpoint = working_base
                            self._last_probe_time = now
                            return working_base
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

# Global singleton resolver
global_endpoint_resolver = EndpointResolver()
