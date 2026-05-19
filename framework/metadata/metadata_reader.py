"""Metadata access helpers."""


class MetadataReader:
    """Reads framework metadata from the configured metadata store."""

    def read_dataset(self, dataset_name: str) -> dict:
        raise NotImplementedError("Implement metadata lookup.")
