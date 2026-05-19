"""Notebook-style entrypoint for Phase 1A Erwin export ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from erwin.model_ingestion.erwin_loader import ingest_erwin_export


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    print(json.dumps(ingest_erwin_export(args.export_path, args.output_path), indent=2))


if __name__ == "__main__":
    main()
