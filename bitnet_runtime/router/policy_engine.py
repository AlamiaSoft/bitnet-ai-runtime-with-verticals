from __future__ import annotations
from typing import Dict, List, Optional
from ..logging import logger
from .models import (
    ModelCapabilityProfile,
    ModelTier,
    PrivacyRequirement,
    RoutingDecision,
    TaskRequirements,
    TaskType,
)
from .registry import ModelCapabilityRegistry

class RoutingPolicyEngine:
    """
    Evaluates task requirements, applies hard security/privacy constraints,
    scores eligible candidate models, and compiles the primary execution route + fallback chain.
    """

    def __init__(self, registry: Optional[ModelCapabilityRegistry] = None):
        self.registry = registry or ModelCapabilityRegistry()

    def evaluate_route(self, req: TaskRequirements) -> RoutingDecision:
        all_candidates = self.registry.list_all()
        eligible_candidates: List[ModelCapabilityProfile] = []
        filter_reasons: Dict[str, str] = {}

        # 1. Apply Hard Constraints
        for m in all_candidates:
            # Health check
            if not m.is_healthy:
                filter_reasons[m.model_id] = "Unhealthy status"
                continue

            # Privacy constraint
            if req.privacy == PrivacyRequirement.AIRGAPPED_LOCAL_ONLY:
                if m.tier == ModelTier.CLOUD_FRONTIER:
                    filter_reasons[m.model_id] = "Cloud model rejected under strict airgap policy"
                    continue
            elif req.privacy == PrivacyRequirement.LOCAL_NETWORK:
                if m.tier == ModelTier.CLOUD_FRONTIER:
                    filter_reasons[m.model_id] = "Cloud model rejected under local network policy"
                    continue

            # Capability constraint
            if req.task_type not in m.capabilities:
                filter_reasons[m.model_id] = f"Missing capability for task '{req.task_type}'"
                continue

            # Context size fit
            if req.estimated_context_tokens > m.context_window:
                filter_reasons[m.model_id] = f"Context size {req.estimated_context_tokens} exceeds window {m.context_window}"
                continue

            # Budget constraint
            if req.max_budget_usd is not None and req.max_budget_usd == 0.0:
                if m.cost_per_1k_input > 0.0 or m.cost_per_1k_output > 0.0:
                    filter_reasons[m.model_id] = "Paid cloud model rejected on zero-budget constraint"
                    continue

            # Minimum quality score
            if m.quality_score < req.min_quality:
                filter_reasons[m.model_id] = f"Quality score {m.quality_score} below required minimum {req.min_quality}"
                continue

            eligible_candidates.append(m)

        # Fallback if no candidate meets all strict constraints
        if not eligible_candidates:
            # Provide emergency fallback from any healthy local model
            fallback_local = [m for m in all_candidates if m.is_healthy and m.tier in (ModelTier.LOCAL_1BIT, ModelTier.LOCAL_DENSE)]
            if fallback_local:
                primary = fallback_local[0]
                return RoutingDecision(
                    primary_model=primary,
                    fallback_chain=fallback_local[1:],
                    rationale=f"Emergency local fallback: no model met strict criteria ({filter_reasons}).",
                    candidate_scores={m.model_id: 1.0 for m in fallback_local},
                )
            raise RuntimeError(f"No eligible model candidates available for task requirements: {req}. Filter reasons: {filter_reasons}")

        # 2. Score Eligible Candidates
        scores: Dict[str, float] = {}
        for m in eligible_candidates:
            score = 50.0  # Base score

            # Preferred tier bonus
            if req.preferred_tier and m.tier == req.preferred_tier:
                score += 30.0

            # Quality alignment
            score += (m.quality_score - req.min_quality) * 10.0

            # Cost efficiency (zero-cost local models get strong boost)
            if m.cost_per_1k_input == 0.0:
                score += 25.0
            else:
                score -= (m.cost_per_1k_input * 1000.0)

            # Latency alignment
            if m.typical_latency_ms <= 200.0:
                score += 15.0
            elif m.typical_latency_ms <= 500.0:
                score += 8.0
            else:
                score -= (m.typical_latency_ms / 100.0)

            # High risk or complex reasoning bias towards higher quality
            if req.task_type in (TaskType.HIGH_RISK_ACTION, TaskType.CODING, TaskType.REASONING):
                score += m.quality_score * 5.0

            # Fast edge classification/extraction bias towards 1-bit
            if req.task_type in (TaskType.CLASSIFICATION, TaskType.EXTRACTION) and m.tier == ModelTier.LOCAL_1BIT:
                score += 30.0

            scores[m.model_id] = round(score, 2)

        # Sort candidates descending by score
        ranked_candidates = sorted(eligible_candidates, key=lambda m: scores.get(m.model_id, 0.0), reverse=True)
        primary = ranked_candidates[0]
        fallback_chain = ranked_candidates[1:]

        rationale = f"Selected '{primary.name}' ({primary.tier}) with score {scores[primary.model_id]} for task '{req.task_type}'."
        return RoutingDecision(
            primary_model=primary,
            fallback_chain=fallback_chain,
            rationale=rationale,
            candidate_scores=scores,
        )
