"""Data contract loading helpers."""

from __future__ import annotations

import json
from pathlib import Path


class ContractLoader:
    """Loads JSON runtime contracts from versioned contract files."""

    def load(self, path: str | Path) -> dict:
        contract_path = Path(path)
        if contract_path.suffix != ".json":
            raise ValueError("Local MVP runtime contract loading supports JSON contracts.")
        return json.loads(contract_path.read_text(encoding="utf-8"))
