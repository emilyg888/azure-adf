"""Target writer abstraction."""


class TargetWriter:
    """Base target writer interface."""

    def write(self, data, metadata: dict) -> None:
        raise NotImplementedError("Implement target write.")
