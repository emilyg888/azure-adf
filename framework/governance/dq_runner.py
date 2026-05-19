"""Data quality runner."""


class DataQualityRunner:
    """Executes data quality checks."""

    def run(self, data, rules: list[dict]) -> list[dict]:
        raise NotImplementedError("Implement data quality execution.")
