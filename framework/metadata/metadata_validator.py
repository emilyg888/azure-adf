"""Metadata validation helpers."""


class MetadataValidator:
    """Validates metadata records before orchestration."""

    def validate(self, metadata: dict) -> list[str]:
        raise NotImplementedError("Implement metadata validation.")
