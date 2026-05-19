# Population by Age Mapping

Dataset: `DS_REF_POPULATION_001`

Contract version: `0.1`

## Source

| Source | Column | Description |
|---|---|---|
| `raw_population` | `indic_de_geo_time` | Composite age group and country code field |
| `raw_population` | `2019` | Population percentage value for 2019 |
| `dim_country` | `country_code_2_digit` | Lookup key for country enrichment |

## Target

| Target column | Type | Transformation |
|---|---|---|
| `country` | string | Joined from country lookup |
| `country_code_2_digit` | string | Extracted from `indic_de_geo_time` and joined to lookup |
| `country_code_3_digit` | string | Joined from country lookup |
| `population` | integer | Joined from country lookup |
| `age_group_0_14` | decimal | `PC_Y0_14` row pivoted into target column |
| `age_group_15_24` | decimal | `PC_Y15_24` row pivoted into target column |
| `age_group_25_49` | decimal | `PC_Y25_49` row pivoted into target column |
| `age_group_50_64` | decimal | `PC_Y50_64` row pivoted into target column |
| `age_group_65_79` | decimal | `PC_Y65_79` row pivoted into target column |
| `age_group_80_max` | decimal | `PC_Y80_MAX` row pivoted into target column |

## Assumptions

- Country codes are valid when they are two alphabetic characters.
- Rows without a matching country lookup are excluded.
- Alphabetic suffixes in percentage values are removed before decimal conversion.
- The LLM agent generated or refactored artefacts at build time only; runtime execution uses approved deterministic code.

## Open Questions

- Confirm whether unmatched countries should be rejected, quarantined, or retained with null lookup fields in later phases.
- Confirm whether percentage values with non-alphabetic symbols should fail or be cleansed under a governed DQ rule.
