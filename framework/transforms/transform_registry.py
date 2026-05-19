"""Transform registry."""


class TransformRegistry:
    """Resolves transform implementations by name."""

    def get(self, transform_name: str):
        raise NotImplementedError("Implement transform resolution.")
