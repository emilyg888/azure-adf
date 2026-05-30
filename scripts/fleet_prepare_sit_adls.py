"""Prepare Fleet SIT files for ADLS STAGING upload.

The local pipeline writes CSV files as a lightweight stand-in for ADLS Parquet.
This script converts those staged CSV outputs into Parquet using the same
partition layout expected by the Snowflake external stage.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_ROOT = Path(".local")
DEFAULT_OUTPUT_ROOT = Path(".local/fleet_sit_adls")
FULL_RUN_TEMPLATE = "fleet_full_{date_compact}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Fleet SIT Parquet files.")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--source-date", action="append", required=True, help="Source date, e.g. 2026-05-25")
    args = parser.parse_args()

    staging_root = args.output_root / "staging"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)

    written = []
    for source_date in args.source_date:
        run_root = args.input_root / FULL_RUN_TEMPLATE.format(date_compact=source_date.replace("-", ""))
        source_staging = run_root / "staging" / "domain=fleet_management"
        if not source_staging.exists():
            raise FileNotFoundError(f"Missing staged source folder: {source_staging}")

        for csv_path in sorted(source_staging.glob("dataset=*/batch_date=*/part-00000.csv")):
            relative = csv_path.relative_to(source_staging)
            parquet_relative = relative.with_suffix(".parquet")
            output_path = staging_root / "domain=fleet_management" / parquet_relative
            output_path.parent.mkdir(parents=True, exist_ok=True)

            frame = pd.read_csv(csv_path, dtype=str).fillna("")
            frame.to_parquet(output_path, index=False)
            written.append(output_path)

    manifest_path = args.output_root / "manifest.txt"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("\n".join(str(path) for path in written) + "\n", encoding="utf-8")

    print(f"Prepared {len(written)} Parquet files under {staging_root}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
