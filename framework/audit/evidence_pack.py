"""Evidence pack generation."""


class EvidencePack:
    """Builds release and certification evidence packages."""

    def build(self, audit_run_id: str) -> dict:
        raise NotImplementedError("Implement evidence pack generation.")
