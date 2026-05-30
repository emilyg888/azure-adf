from framework.identity.match_decision import PriorHumanDecision, ThresholdPolicy, decide_match, is_graph_eligible


CUSTOMER_POLICY_V1 = ThresholdPolicy(
    entity_type="CUSTOMER",
    auto_match_min_score=0.95,
    review_min_score=0.70,
    auto_reject_below_score=0.70,
    policy_version="v1",
)


CUSTOMER_POLICY_STRICT = ThresholdPolicy(
    entity_type="CUSTOMER",
    auto_match_min_score=0.98,
    review_min_score=0.85,
    auto_reject_below_score=0.85,
    policy_version="v2",
)


def test_score_bands_store_threshold_policy_version():
    auto_match = decide_match(match_score=0.97, threshold_policy=CUSTOMER_POLICY_V1)
    review = decide_match(match_score=0.90, threshold_policy=CUSTOMER_POLICY_STRICT)
    no_match = decide_match(match_score=0.40, threshold_policy=CUSTOMER_POLICY_V1)

    assert auto_match.final_decision == "MATCH"
    assert auto_match.decision_status == "AUTO_APPROVED"
    assert auto_match.graph_apply_status == "READY_TO_APPLY"
    assert auto_match.threshold_policy_version == "v1"

    assert review.final_decision == "REVIEW"
    assert review.decision_status == "REVIEW_REQUIRED"
    assert review.graph_apply_status == "NOT_ELIGIBLE"
    assert review.threshold_policy_version == "v2"

    assert no_match.final_decision == "NO_MATCH"
    assert no_match.graph_apply_status == "NOT_ELIGIBLE"


def test_same_score_can_change_decision_under_policy_version():
    v1_decision = decide_match(match_score=0.96, threshold_policy=CUSTOMER_POLICY_V1)
    strict_decision = decide_match(match_score=0.96, threshold_policy=CUSTOMER_POLICY_STRICT)

    assert v1_decision.final_decision == "MATCH"
    assert v1_decision.threshold_policy_version == "v1"
    assert strict_decision.final_decision == "REVIEW"
    assert strict_decision.threshold_policy_version == "v2"


def test_decision_authority_order():
    hard_reject = decide_match(match_score=0.99, threshold_policy=CUSTOMER_POLICY_V1, hard_reject=True)
    hard_match = decide_match(match_score=0.10, threshold_policy=CUSTOMER_POLICY_V1, hard_match=True)
    human_approved = decide_match(
        match_score=0.75,
        threshold_policy=CUSTOMER_POLICY_V1,
        prior_human_decision=PriorHumanDecision(
            final_decision="MATCH",
            decision_status="HUMAN_APPROVED",
            reviewer_id="steward_a",
            override_reason="verified_contract_evidence",
        ),
    )

    assert hard_reject.final_decision == "NO_MATCH"
    assert hard_reject.decision_method == "hard_reject_rule"
    assert hard_reject.graph_apply_status == "NOT_ELIGIBLE"

    assert hard_match.final_decision == "MATCH"
    assert hard_match.decision_method == "hard_match_rule"
    assert hard_match.graph_apply_status == "READY_TO_APPLY"

    assert human_approved.final_decision == "MATCH"
    assert human_approved.decision_status == "HUMAN_APPROVED"
    assert human_approved.graph_apply_status == "READY_TO_APPLY"


def test_graph_eligibility_gate_blocks_unapproved_matches():
    assert is_graph_eligible("MATCH", "AUTO_APPROVED")
    assert is_graph_eligible("MATCH", "HUMAN_APPROVED")
    assert not is_graph_eligible("MATCH", "REVIEW_REQUIRED")
    assert not is_graph_eligible("REVIEW", "REVIEW_REQUIRED")
    assert not is_graph_eligible("NO_MATCH", "AUTO_APPROVED")

