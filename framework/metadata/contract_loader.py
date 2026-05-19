"""Data contract loading helpers."""


class ContractLoader:
    """Loads dataset contracts from versioned contract files."""

    def load(self, path: str) -> dict:
        raise NotImplementedError("Implement contract loading.")
