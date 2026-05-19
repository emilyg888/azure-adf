from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_user_testing_suite_exists_and_covers_mvp_phases():
    suite = ROOT / "tests/user_testing/mvp_user_testing_suite.md"
    text = suite.read_text(encoding="utf-8")
    for phase in ["Phase 0", "Phase 1", "Phase 1A", "Phase 2", "Phase 4 partial"]:
        assert phase in text
    for test_case in ["UT-001", "UT-002", "UT-004", "UT-006", "UT-008", "UT-009"]:
        assert test_case in text
