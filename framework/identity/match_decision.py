"""Governed identity match decision policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Decision = Literal["MATCH", "REVIEW", "NO_MATCH"]
DecisionStatus = Literal["AUTO_APPROVED", "REVIEW_REQUIRED", "HUMAN_APPROVED", "HUMAN_REJECTED"]
GraphApplyStatus = Literal["READY_TO_APPLY", "NOT_ELIGIBLE"]


@dataclass(frozen=True)
class ThresholdPolicy:
    entity_type: str
    auto_match_min_score: float
    review_min_score: float
    auto_reject_below_score: float
    policy_version: str


@dataclass(frozen=True)
class PriorHumanDecision:
    final_decision: Literal["MATCH", "NO_MATCH"]
    decision_status: Literal["HUMAN_APPROVED", "HUMAN_REJECTED"]
    reviewer_id: str
    override_reason: str


@dataclass(frozen=True)
class MatchDecision:
    final_decision: Decision
    decision_status: DecisionStatus
    decision_method: str
    decision_reason: str
    threshold_policy_version: str
    graph_apply_status: GraphApplyStatus


def decide_match(
    *,
    match_score: float,
    threshold_policy: ThresholdPolicy,
    hard_match: bool = False,
    hard_reject: bool = False,
    prior_human_decision: PriorHumanDecision | None = None,
) -> MatchDecision:
    """Apply the v1 Snowflake-authoritative identity decision hierarchy."""
    if hard_reject:
        return _decision(
            final_decision="NO_MATCH",
            decision_status="AUTO_APPROVED",
            decision_method="hard_reject_rule",
            decision_reason="hard_reject_rule",
            policy=threshold_policy,
        )

    if hard_match:
        return _decision(
            final_decision="MATCH",
            decision_status="AUTO_APPROVED",
            decision_method="hard_match_rule",
            decision_reason="hard_match_rule",
            policy=threshold_policy,
        )

    if prior_human_decision is not None:
        return _decision(
            final_decision=prior_human_decision.final_decision,
            decision_status=prior_human_decision.decision_status,
            decision_method="human_review",
            decision_reason=prior_human_decision.override_reason,
            policy=threshold_policy,
        )

    if match_score >= threshold_policy.auto_match_min_score:
        return _decision(
            final_decision="MATCH",
            decision_status="AUTO_APPROVED",
            decision_method="ml_score_band",
            decision_reason="score_at_or_above_auto_match_threshold",
            policy=threshold_policy,
        )

    if match_score >= threshold_policy.review_min_score:
        return _decision(
            final_decision="REVIEW",
            decision_status="REVIEW_REQUIRED",
            decision_method="ml_score_band",
            decision_reason="score_in_review_band",
            policy=threshold_policy,
        )

    return _decision(
        final_decision="NO_MATCH",
        decision_status="AUTO_APPROVED",
        decision_method="ml_score_band",
        decision_reason="score_below_review_threshold",
        policy=threshold_policy,
    )


def is_graph_eligible(final_decision: str, decision_status: str) -> bool:
    return final_decision == "MATCH" and decision_status in {"AUTO_APPROVED", "HUMAN_APPROVED"}


def _decision(
    *,
    final_decision: Decision,
    decision_status: DecisionStatus,
    decision_method: str,
    decision_reason: str,
    policy: ThresholdPolicy,
) -> MatchDecision:
    graph_apply_status: GraphApplyStatus = (
        "READY_TO_APPLY" if is_graph_eligible(final_decision, decision_status) else "NOT_ELIGIBLE"
    )
    return MatchDecision(
        final_decision=final_decision,
        decision_status=decision_status,
        decision_method=decision_method,
        decision_reason=decision_reason,
        threshold_policy_version=policy.policy_version,
        graph_apply_status=graph_apply_status,
    )

