"""PII masking helpers."""


class PiiMasker:
    """Applies configured PII masking rules."""

    def mask(self, data, rules: list[dict]):
        raise NotImplementedError("Implement PII masking.")
