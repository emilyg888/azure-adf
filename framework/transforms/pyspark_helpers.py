"""Shared PySpark helper functions."""


def require_columns(dataframe, columns: list[str]) -> None:
    """Validate that a dataframe contains all required columns."""
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
