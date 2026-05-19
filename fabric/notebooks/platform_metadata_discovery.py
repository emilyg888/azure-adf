"""Notebook-style entrypoint for Phase 1A platform metadata discovery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from erwin.model_ingestion.platform_discovery import discover_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--file-format", default="csv")
    parser.add_argument("--delimiter", default="tab")
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    result = discover_file(
        dataset_root=args.dataset_root,
        dataset_id=args.dataset_id,
        relative_path=args.path,
        file_format=args.file_format,
        delimiter=args.delimiter,
        output_path=args.output_path,
    )
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()
