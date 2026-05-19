"""Metadata-driven transformation rule engine."""


class RuleEngine:
    """Applies configured transformation rules."""

    def apply(self, data, rules: list[dict]):
        raise NotImplementedError("Implement rule application.")
