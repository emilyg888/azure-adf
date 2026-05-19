"""Dataset certification gate."""


class CertificationGate:
    """Evaluates whether a dataset can be certified."""

    def evaluate(self, evidence: dict) -> bool:
        raise NotImplementedError("Implement certification evaluation.")
