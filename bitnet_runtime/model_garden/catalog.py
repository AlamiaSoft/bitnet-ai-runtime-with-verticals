from __future__ import annotations
from typing import Dict, List, Optional
from ..logging import logger
from .models import (
    HardwareRequirements,
    ModelFamily,
    ModelManifest,
    ModelModality,
    ModelTier,
    TaskType,
)

class ModelGarden:
    """
    Curated model catalog and capability registry for 1-4B SLMs,
    dedicated embedding models, specialized models, and frontier adapters.
    """

    def __init__(self):
        self._manifests: Dict[str, ModelManifest] = {}
        self._init_curated_catalog()

    def register_manifest(self, manifest: ModelManifest) -> None:
        self._manifests[manifest.model_id] = manifest
        logger.debug(f"Model Garden registered: '{manifest.model_id}' ({manifest.family}, {manifest.modality})")

    def get(self, model_id: str) -> Optional[ModelManifest]:
        return self._manifests.get(model_id)

    def list_all(self) -> List[ModelManifest]:
        return list(self._manifests.values())

    def list_by_modality(self, modality: ModelModality) -> List[ModelManifest]:
        return [m for m in self._manifests.values() if m.modality == modality]

    def list_generative_slms(self, max_ram_mb: Optional[int] = None) -> List[ModelManifest]:
        res = [m for m in self._manifests.values() if m.modality == ModelModality.GENERATIVE_TEXT and m.tier != ModelTier.CLOUD_FRONTIER]
        if max_ram_mb:
            res = [m for m in res if m.hardware.min_ram_mb <= max_ram_mb]
        return res

    def list_embedding_models(self) -> List[ModelManifest]:
        return self.list_by_modality(ModelModality.EMBEDDING)

    def _init_curated_catalog(self) -> None:
        # ==========================================
        # 1. Generative SLMs (CPU-friendly 1-4B)
        # ==========================================

        # BitNet b1.58 2B-4T (Microsoft)
        self.register_manifest(
            ModelManifest(
                model_id="bitnet_b1_58_2b",
                name="Microsoft BitNet b1.58 2B-4T",
                family=ModelFamily.BITNET,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_1BIT,
                parameter_size="2.4B",
                context_window=4096,
                hardware=HardwareRequirements(
                    min_ram_mb=1200,
                    quantization="1bit_ternary",
                    recommended_threads=4,
                    requires_gpu=False,
                ),
                provider_backend="bitnet",
                task_ratings={
                    TaskType.DIALOGUE: 4.6,
                    TaskType.CLASSIFICATION: 4.6,
                    TaskType.EXTRACTION: 4.2,
                    TaskType.SUMMARIZATION: 4.0,
                    TaskType.RAG_QA: 3.6,
                    TaskType.REASONING: 3.2,
                    TaskType.CREATIVE: 3.0,
                    TaskType.CODING: 2.0,
                },
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=110.0,
                license="MIT",
                description="Ultra-efficient 1-bit ternary SLM optimized for continuous CPU inference.",
                download_url="https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-GGUF/resolve/main/ggml-model-i2_s.gguf",
            )
        )

        # Qwen 2.5 1.5B Instruct (Alibaba)
        self.register_manifest(
            ModelManifest(
                model_id="qwen2.5_1.5b_instruct",
                name="Qwen 2.5 1.5B Instruct",
                family=ModelFamily.QWEN,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="1.5B",
                context_window=32768,
                hardware=HardwareRequirements(
                    min_ram_mb=1100,
                    quantization="q4_k_m",
                    recommended_threads=4,
                    requires_gpu=False,
                ),
                provider_backend="llamacpp",
                task_ratings={
                    TaskType.DIALOGUE: 4.8,
                    TaskType.EXTRACTION: 4.8,
                    TaskType.CLASSIFICATION: 4.7,
                    TaskType.CODING: 3.8,
                    TaskType.RAG_QA: 4.0,
                    TaskType.SUMMARIZATION: 4.2,
                    TaskType.REASONING: 3.6,
                    TaskType.CREATIVE: 3.5,
                },
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=180.0,
                license="Apache-2.0",
                description="Lightweight multilingual powerhouse with exceptional structured extraction and JSON output capabilities.",
                download_url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            )
        )

        # Phi-3.5 Mini 3.8B Instruct (Microsoft)
        self.register_manifest(
            ModelManifest(
                model_id="phi3.5_mini_3.8b",
                name="Microsoft Phi-3.5 Mini 3.8B",
                family=ModelFamily.PHI,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="3.8B",
                context_window=128000,
                hardware=HardwareRequirements(
                    min_ram_mb=2500,
                    quantization="q4_k_m",
                    recommended_threads=6,
                    requires_gpu=False,
                ),
                provider_backend="llamacpp",
                task_ratings={
                    TaskType.DIALOGUE: 4.7,
                    TaskType.REASONING: 4.6,
                    TaskType.CODING: 4.3,
                    TaskType.RAG_QA: 4.5,
                    TaskType.SUMMARIZATION: 4.4,
                    TaskType.EXTRACTION: 4.2,
                    TaskType.CLASSIFICATION: 4.3,
                    TaskType.HIGH_RISK_ACTION: 4.0,
                },
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=380.0,
                license="MIT",
                description="State-of-the-art small reasoning model excelling at multi-step logic and synthesis.",
                download_url="https://huggingface.co/microsoft/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
            )
        )

        # Gemma 2 2B IT (Google)
        self.register_manifest(
            ModelManifest(
                model_id="gemma2_2b_it",
                name="Google Gemma 2 2B Instruct",
                family=ModelFamily.GEMMA,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="2.6B",
                context_window=8192,
                hardware=HardwareRequirements(
                    min_ram_mb=1700,
                    quantization="q4_k_m",
                    recommended_threads=4,
                    requires_gpu=False,
                ),
                provider_backend="llamacpp",
                task_ratings={
                    TaskType.DIALOGUE: 4.6,
                    TaskType.CREATIVE: 4.5,
                    TaskType.SUMMARIZATION: 4.3,
                    TaskType.CLASSIFICATION: 4.3,
                    TaskType.REASONING: 3.9,
                    TaskType.RAG_QA: 4.0,
                    TaskType.EXTRACTION: 3.8,
                },
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=220.0,
                license="Gemma License",
                description="Highly capable conversational and creative instruction-tuned compact model.",
                download_url="https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
            )
        )

        # LLaMA 3.2 3B Instruct (Meta)
        self.register_manifest(
            ModelManifest(
                model_id="llama3.2_3b_instruct",
                name="Meta LLaMA 3.2 3B Instruct",
                family=ModelFamily.LLAMA,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="3.2B",
                context_window=128000,
                hardware=HardwareRequirements(
                    min_ram_mb=2100,
                    quantization="q4_k_m",
                    recommended_threads=4,
                    requires_gpu=False,
                ),
                provider_backend="llamacpp",
                task_ratings={
                    TaskType.DIALOGUE: 4.6,
                    TaskType.REASONING: 4.3,
                    TaskType.CODING: 4.1,
                    TaskType.RAG_QA: 4.3,
                    TaskType.EXTRACTION: 4.4,
                    TaskType.CLASSIFICATION: 4.5,
                    TaskType.SUMMARIZATION: 4.3,
                },
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=310.0,
                license="Llama 3.2 Community",
                description="Edge-focused multimodal-ready instruction model with 128k context.",
                download_url="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            )
        )

        # ==========================================
        # 2. Dedicated Embedding Models
        # ==========================================

        # BGE-Small-EN v1.5 (BAAI)
        self.register_manifest(
            ModelManifest(
                model_id="bge_small_en_v1.5",
                name="BGE Small English v1.5",
                family=ModelFamily.BGE,
                modality=ModelModality.EMBEDDING,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="33M",
                context_window=512,
                hardware=HardwareRequirements(
                    min_ram_mb=130,
                    quantization="fp32",
                    recommended_threads=2,
                    requires_gpu=False,
                ),
                provider_backend="local_embedding",
                task_ratings={TaskType.RAG_QA: 4.8},
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=15.0,
                license="MIT",
                description="Compact 384-dimensional dense embedding model for semantic vector search.",
                metadata={"vector_dim": 384},
                download_url="https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/model.safetensors",
            )
        )

        # All-MiniLM-L6-v2 (SentenceTransformers)
        self.register_manifest(
            ModelManifest(
                model_id="all_minilm_l6_v2",
                name="Sentence-Transformers all-MiniLM-L6-v2",
                family=ModelFamily.MINILM,
                modality=ModelModality.EMBEDDING,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="22M",
                context_window=256,
                hardware=HardwareRequirements(
                    min_ram_mb=90,
                    quantization="fp32",
                    recommended_threads=2,
                    requires_gpu=False,
                ),
                provider_backend="local_embedding",
                task_ratings={TaskType.RAG_QA: 4.6},
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=12.0,
                license="Apache-2.0",
                description="Industry standard lightweight embedding model for high-throughput search.",
                metadata={"vector_dim": 384},
                download_url="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/model.safetensors",
            )
        )

        # BitNet Feature Hash (Ternary / Projection)
        self.register_manifest(
            ModelManifest(
                model_id="bitnet_feature_hash_128",
                name="BitNet Ternary Feature Hash Embedder",
                family=ModelFamily.BITNET,
                modality=ModelModality.EMBEDDING,
                tier=ModelTier.LOCAL_1BIT,
                parameter_size="100K",
                context_window=8192,
                hardware=HardwareRequirements(
                    min_ram_mb=5,
                    quantization="1bit_hash",
                    recommended_threads=1,
                    requires_gpu=False,
                ),
                provider_backend="bitnet",
                task_ratings={TaskType.RAG_QA: 3.8},
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=1.5,
                license="MIT",
                description="Ultra-fast deterministic n-gram cosine projection running with zero dependencies and <5MB RAM.",
                metadata={"vector_dim": 128},
            )
        )

        # ==========================================
        # 3. Specialized Models
        # ==========================================

        # BGE Reranker Base
        self.register_manifest(
            ModelManifest(
                model_id="bge_reranker_base",
                name="BAAI BGE Reranker Base",
                family=ModelFamily.BGE,
                modality=ModelModality.RERANKER,
                tier=ModelTier.LOCAL_DENSE,
                parameter_size="110M",
                context_window=512,
                hardware=HardwareRequirements(min_ram_mb=500, quantization="fp16"),
                provider_backend="local_reranker",
                task_ratings={TaskType.RAG_QA: 4.9},
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=45.0,
                license="MIT",
                description="Cross-encoder neural reranker for precision-critical RAG pipelines.",
            )
        )

        # ==========================================
        # 4. Cloud Frontier Models
        # ==========================================

        # GPT-4o
        self.register_manifest(
            ModelManifest(
                model_id="gpt4o_frontier",
                name="OpenAI GPT-4o",
                family=ModelFamily.OPENAI,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.CLOUD_FRONTIER,
                parameter_size="Omni",
                context_window=128000,
                hardware=HardwareRequirements(min_ram_mb=0, requires_gpu=False),
                provider_backend="cloud",
                task_ratings={
                    TaskType.DIALOGUE: 4.9,
                    TaskType.REASONING: 4.9,
                    TaskType.CODING: 4.9,
                    TaskType.HIGH_RISK_ACTION: 4.9,
                    TaskType.EXTRACTION: 4.9,
                    TaskType.CLASSIFICATION: 4.9,
                    TaskType.SUMMARIZATION: 4.9,
                    TaskType.RAG_QA: 4.9,
                },
                cost_per_1k_input=0.0025,
                cost_per_1k_output=0.010,
                typical_latency_ms=750.0,
                license="Commercial API",
                description="Frontier multimodal reasoning engine for complex synthesis and mission-critical planning.",
            )
        )

        # ==========================================
        # 5. Fast Test Mock Manifest (Development Only)
        # ==========================================
        self.register_manifest(
            ModelManifest(
                model_id="mock_local_engine",
                name="Mock Development Engine",
                family=ModelFamily.CUSTOM,
                modality=ModelModality.GENERATIVE_TEXT,
                tier=ModelTier.LOCAL_1BIT,
                parameter_size="Mock",
                context_window=4096,
                hardware=HardwareRequirements(min_ram_mb=10),
                provider_backend="mock",
                task_ratings={t: 3.5 for t in TaskType},
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=10.0,
                license="MIT",
                is_development_only=True,
                description="Zero-dependency mock runner for continuous integration and unit testing.",
            )
        )
