"""Source system reader abstractions."""


class SourceReader:
    """Reads source data according to dataset metadata."""

    def read(self, metadata: dict):
        raise NotImplementedError("Implement source read.")
