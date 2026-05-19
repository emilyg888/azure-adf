from decimal import Decimal

import pytest

from transforms.pyspark.population_by_age_transform import (
    OUTPUT_COLUMNS,
    clean_percentage,
    transform_population_by_age,
)


def population_rows():
    return [
        {"indic_de_geo_time": "PC_Y0_14,AU", "2019": "18.7p"},
        {"indic_de_geo_time": "PC_Y15_24,AU", "2019": "12.8"},
        {"indic_de_geo_time": "PC_Y25_49,AU", "2019": "34.1"},
        {"indic_de_geo_time": "PC_Y50_64,AU", "2019": "19.0"},
        {"indic_de_geo_time": "PC_Y65_79,AU", "2019": "11.0"},
        {"indic_de_geo_time": "PC_Y80_MAX,AU", "2019": "4.4"},
        {"indic_de_geo_time": "PC_Y0_14,INVALID", "2019": "99.9"},
    ]


def country_rows():
    return [
        {
            "country": "Australia",
            "country_code_2_digit": "AU",
            "country_code_3_digit": "AUS",
            "population": "25690000",
        }
    ]


def test_output_schema():
    output = transform_population_by_age(population_rows(), country_rows())
    assert set(OUTPUT_COLUMNS).issubset(output[0].keys())


def test_country_code_extraction_and_join():
    output = transform_population_by_age(population_rows(), country_rows())
    assert output[0]["country"] == "Australia"
    assert output[0]["country_code_2_digit"] == "AU"
    assert output[0]["country_code_3_digit"] == "AUS"


def test_age_group_extraction_and_pivot_columns():
    output = transform_population_by_age(population_rows(), country_rows())
    assert output[0]["age_group_0_14"] == Decimal("18.7")
    assert output[0]["age_group_80_max"] == Decimal("4.4")


def test_percentage_cleaning():
    assert clean_percentage("18.7p") == Decimal("18.7")


def test_no_invalid_country_codes():
    output = transform_population_by_age(population_rows(), country_rows())
    assert len(output) == 1


def test_missing_lookup_data_fails():
    with pytest.raises(ValueError, match="country lookup input is empty"):
        transform_population_by_age(population_rows(), [])
