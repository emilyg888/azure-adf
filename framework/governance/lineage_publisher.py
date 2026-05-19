"""Lineage publisher."""


class LineagePublisher:
    """Publishes lineage metadata to the configured catalog."""

    def publish(self, event: dict) -> None:
        raise NotImplementedError("Implement lineage publishing.")
