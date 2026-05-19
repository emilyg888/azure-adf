"""Population by age transformation logic."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Iterable


AGE_GROUP_COLUMNS = {
    "Y0_14": "age_group_0_14",
    "Y15_24": "age_group_15_24",
    "Y25_49": "age_group_25_49",
    "Y50_64": "age_group_50_64",
    "Y65_79": "age_group_65_79",
    "Y80_MAX": "age_group_80_max",
}

OUTPUT_COLUMNS = [
    "country",
    "country_code_2_digit",
    "country_code_3_digit",
    "population",
    "age_group_0_14",
    "age_group_15_24",
    "age_group_25_49",
    "age_group_50_64",
    "age_group_65_79",
    "age_group_80_max",
]


def validate_required_columns(rows: Iterable[dict], required_columns: set[str], label: str) -> None:
    sample = next(iter(rows), None)
    if sample is None:
        raise ValueError(f"{label} input is empty")
    missing = required_columns.difference(sample.keys())
    if missing:
        raise ValueError(f"{label} missing required columns: {sorted(missing)}")


def clean_percentage(value: str) -> Decimal | None:
    cleaned = re.sub(r"[A-Za-z]", "", str(value)).strip()
    if cleaned in {"", ":"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid percentage value: {value}") from exc


def parse_population_row(row: dict) -> tuple[str, str, Decimal | None] | None:
    composite = row["indic_de_geo_time"]
    if "," not in composite:
        return None
    raw_age_group, country_code = [part.strip() for part in composite.split(",", 1)]
    if len(country_code) != 2 or not country_code.isalpha():
        return None
    age_group = raw_age_group.removeprefix("PC_")
    return country_code.upper(), age_group, clean_percentage(row["2019"])


def transform_population_by_age(df_population, df_country) -> list[dict]:
    """Transform raw population-by-age input into curated country age-band output."""
    population_rows = list(df_population)
    country_rows = list(df_country)
    validate_required_columns(population_rows, {"indic_de_geo_time", "2019"}, "population")
    validate_required_columns(
        country_rows,
        {"country", "country_code_2_digit", "country_code_3_digit", "population"},
        "country lookup",
    )

    countries = {row["country_code_2_digit"].upper(): row for row in country_rows}
    pivoted: dict[str, dict] = {}
    for row in population_rows:
        parsed = parse_population_row(row)
        if parsed is None:
            continue
        country_code, age_group, percentage = parsed
        if country_code not in countries or age_group not in AGE_GROUP_COLUMNS:
            continue
        output = pivoted.setdefault(
            country_code,
            {
                "country": countries[country_code]["country"],
                "country_code_2_digit": countries[country_code]["country_code_2_digit"],
                "country_code_3_digit": countries[country_code]["country_code_3_digit"],
                "population": countries[country_code]["population"],
                "age_group_0_14": None,
                "age_group_15_24": None,
                "age_group_25_49": None,
                "age_group_50_64": None,
                "age_group_65_79": None,
                "age_group_80_max": None,
            },
        )
        output[AGE_GROUP_COLUMNS[age_group]] = percentage
    return [{column: row[column] for column in OUTPUT_COLUMNS} for row in pivoted.values()]


def transform(dataframe):
    """Backward-compatible transform alias for the Phase 0 scaffold."""
    return dataframe
