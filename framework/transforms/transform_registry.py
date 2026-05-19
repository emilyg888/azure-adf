"""Transform registry."""

from __future__ import annotations

from transforms.pyspark.population_by_age_transform import transform_population_by_age


TRANSFORM_REGISTRY = {
    "DS_REF_POPULATION_001": transform_population_by_age,
}


class TransformRegistry:
    """Resolves transform implementations by dataset id."""

    def get(self, transform_name: str):
        try:
            return TRANSFORM_REGISTRY[transform_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported MVP transform: {transform_name}") from exc
